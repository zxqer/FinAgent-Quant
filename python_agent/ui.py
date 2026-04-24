import streamlit as st
import asyncio
import grpc
import sys
import os
from langchain_core.messages import HumanMessage

# 路径修复
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, "core"))

import fin_agent_pb2
import fin_agent_pb2_grpc
from agent_brain import agent_executor

# --- 1. Streamlit 页面配置 ---
st.set_page_config(page_title="FinAgent 实时决策大屏", layout="wide")
st.title("🤖 FinAgent-Quant 实时多智能体决策系统")

# 初始化 Session State (用于跨刷新存储数据)
if "price" not in st.session_state:
    st.session_state.price = 0.0
if "logs" not in st.session_state:
    st.session_state.logs = []

# --- 2. 侧边栏：实时行情看板 ---
st.sidebar.header("💹 实时行情 (C++ Data Source)")
price_placeholder = st.sidebar.empty()

# --- 3. 主界面：Agent 思维监控 ---
st.header("🧠 Agent 实时思维链")
log_container = st.container()

async def run_grpc_client():
    """异步 gRPC 监听任务"""
    server_address = 'localhost:50051'
    async with grpc.aio.insecure_channel(server_address) as channel:
        stub = fin_agent_pb2_grpc.FinAgentServiceStub(channel)
        data_stream = stub.StreamFinancialData(fin_agent_pb2.Empty())
        
        async for envelope in data_stream:
            payload_type = envelope.WhichOneof('payload')
            
            if payload_type == 'market':
                # 更新行情
                st.session_state.price = envelope.market.price
                price_placeholder.metric(
                    label=f"Ticker: {envelope.market.symbol}", 
                    value=f"${st.session_state.price:,.2f}",
                    delta=f"Vol: {envelope.market.volume:.2f}"
                )
                
            elif payload_type == 'news':
                # 触发 Agent 推理
                news = envelope.news
                with log_container:
                    with st.chat_message("assistant", avatar="🔍"):
                        st.write(f"**收到新消息：** {news.title}")
                        
                        # 启动 LangGraph 推理
                        config = {"configurable": {"thread_id": "UI_THREAD"}}
                        inputs = {
                            "messages": [HumanMessage(content=f"新闻: {news.title}. 内容: {news.content}")],
                            "market_context": f"BTC: {st.session_state.price}"
                        }
                        
                        # 流式展示 Agent 节点
                        async for event in agent_executor.astream(inputs, config=config):
                            for node, values in event.items():
                                if node == "agent":
                                    msg = values["messages"][-1]
                                    if msg.content:
                                        st.info(f"**分析师决策：** {msg.content}")
                                elif node == "tools":
                                    st.warning("🌐 正在启动联网搜索补充背景资料...")

# --- 4. 启动逻辑 ---
if __name__ == "__main__":
    # Streamlit 运行异步函数的标准姿势
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        asyncio.run(run_grpc_client())
    except Exception as e:
        st.error(f"❌ 运行异常: {e}")