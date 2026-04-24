import os
import chromadb
from datetime import datetime
from typing import Annotated, TypedDict, Union
from chromadb.utils import embedding_functions
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from dotenv import load_dotenv

# 引入基础工具和物理交易执行器
from skill_registry import skill_router, execute_trade

load_dotenv()

# --- 1. 量化 RAG 记忆组件 ---
class QuantRAGMemory:
    def __init__(self, db_path="./quant_memory_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="historical_market_events",
            embedding_function=self.embedding_fn
        )

    def recall(self, current_news: str) -> str:
        if self.collection.count() == 0: return "历史档案库暂无参考数据。"
        results = self.collection.query(query_texts=[current_news], n_results=2)
        report = "【历史档案检索结果】:\n"
        for i in range(len(results['ids'][0])):
            meta = results['metadatas'][0][i]
            report += f"  - 相似案例: {results['documents'][0][i]}\n"
            report += f"  - 历史表现: 24H涨跌幅 {meta['return_24h']}%, 最大回撤 {meta['max_drawdown']}%\n"
        return report

rag_memory = QuantRAGMemory()

# --- 2. 状态定义 ---
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], lambda x, y: x + y]
    market_context: str
    risk_status: str  
    iterations: int

# --- 3. 基础模型初始化 ---
base_llm = ChatOpenAI(
    model='deepseek-chat', 
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
    temperature=0.2 
)

# --- 4. 节点定义 ---

async def alpha_analyst(state: AgentState):
    """分析师：负责情报收集和策略制定 (无下单权限)"""
    news_content = state['messages'][0].content
    active_tools = skill_router.route_skills(news_content)
    llm_with_skills = base_llm.bind_tools(active_tools)
    
    last_risk = f"\n⚠️ 风控反馈: {state['messages'][-1].content}" if state.get("risk_status") == "REJECT" else ""
    current_time = datetime.now().strftime("%Y年%m月%d日")
    
    # ⚠️ 核心修复：移除了所有的"开火权"暗示
    prompt = (
        f"你是一名资深的跨市场量化分析师。\n"
        f"【系统当前时间】：{current_time}\n"
        f"当前行情背景: {state['market_context']}。{last_risk}\n"
        "【严格执行指令】：\n"
        "1. 使用提供的工具收集最新数据。最多只允许调用 1-2 次工具。\n"
        "2. 数据收集完毕后，立即生成包含明确 [建议] (BUY/SELL/HOLD) 和 [操作点位] 的研报。\n"
        "3. 你的研报将提交给风控官审批，风控通过后，独立的交易台会自动执行你的指令。"
    )
    
    response = await llm_with_skills.ainvoke([HumanMessage(content=prompt)] + state['messages'])
    return {"messages": [response], "iterations": state.get("iterations", 0) + 1}

async def risk_manager(state: AgentState):
    """风控官：利用 RAG 检索进行终审"""
    news_content = state['messages'][0].content 
    historical_context = rag_memory.recall(news_content)
    analyst_suggestion = state['messages'][-1].content
    
    prompt = f"""
    你是一名风控官。
    {historical_context}
    
    当前分析师建议：{analyst_suggestion}
    请根据历史案例的真实表现审核此建议。
    如果建议激进或止损位过窄，请予以驳回。
    
    必须包含以下之一：[STATUS]: PASS 或 [STATUS]: REJECT
    """
    response = await base_llm.ainvoke([HumanMessage(content=prompt)])
    status = "PASS" if "[STATUS]: PASS" in response.content else "REJECT"
    return {"messages": [response], "risk_status": status}

async def execution_desk(state: AgentState):
    """交易台：只有风控通过后，才由本节点物理执行交易"""
    # 提取分析师的最终研报内容
    analyst_msg = state['messages'][-2].content.upper()
    
    # 简单的关键字解析 (实际生产中这里会接一个专门解析结构化数据的函数)
    side = None
    if "BUY" in analyst_msg:
        side = "buy"
    elif "SELL" in analyst_msg:
        side = "sell"
        
    if not side or "HOLD" in analyst_msg:
        return {"messages": [AIMessage(content="【🏦 交易台执行报告】：策略为观望 (HOLD) 或无明确方向，未触发真实交易。")]}
        
    # ⚡ 直接在 Python 代码层调用执行引擎
    print(f"\n✅ 风控绿灯！正在移交 Execution Desk...")
    result_json = execute_trade.invoke({"symbol": "BTC/USDT", "side": side, "amount_usd": 1000})
    
    receipt = f"【🏦 交易台执行报告】：已连接交易所完成物理执行。\n返回结果：{result_json}"
    return {"messages": [AIMessage(content=receipt)]}

# --- 5. 工具节点包装器 ---
all_available_tools = list(skill_router.available_skills.values())
tool_node = ToolNode(all_available_tools)

# --- 6. 路由与构建图逻辑 ---
workflow = StateGraph(AgentState)

# 注册所有节点
workflow.add_node("alpha_analyst", alpha_analyst)
workflow.add_node("risk_manager", risk_manager)
workflow.add_node("execution_desk", execution_desk) # 🌟 新增
workflow.add_node("tools", tool_node)

workflow.set_entry_point("alpha_analyst")

def route_analyst(state: AgentState):
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "tools"
    return "risk_manager"

def route_risk(state: AgentState):
    # 🌟 核心路由修复：PASS 之后去交易台，不再直接结束
    if state["risk_status"] == "PASS":
        return "execution_desk"
    if state["iterations"] >= 3:
        return END
    return "alpha_analyst"

# 连接连线
workflow.add_conditional_edges("alpha_analyst", route_analyst)
workflow.add_edge("tools", "alpha_analyst")
workflow.add_conditional_edges("risk_manager", route_risk)
workflow.add_edge("execution_desk", END) # 交易台执行完后整个流程结束

agent_executor = workflow.compile(checkpointer=MemorySaver())

print("✅ Agent 大脑加载完成 (已启用物理隔离的三级审核架构)")