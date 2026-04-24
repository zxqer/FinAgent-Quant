import asyncio
import grpc
import sys
import os
import uuid
from langchain_core.messages import HumanMessage

# 确保能找到生成的 gRPC protobuf 文件 (假设放在 core 目录下)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, "core"))

try:
    import fin_agent_pb2
    import fin_agent_pb2_grpc
except ImportError:
    print("⚠️ 警告: 未找到 fin_agent_pb2，请确保 C++ gRPC 接口已正确编译。")
    sys.exit(1)

from agent_brain import agent_executor

# 记录已处理的新闻，防止 C++ 端重复推送导致重复下单
processed_news = set()

async def process_task(current_price: str, news_title: str):
    """独立的异步任务：处理单条新闻的完整 AI 推理与交易闭环"""
    if news_title in processed_news: 
        return
    processed_news.add(news_title)
    
    task_id = str(uuid.uuid4())[:8]
    print(f"\n🚀 [Task-{task_id}] 捕获突发新闻: {news_title} (锁定盘口: {current_price})")
    
    config = {
        "configurable": {"thread_id": f"live_session_{task_id}"},
        "recursion_limit": 25
    }
    
    inputs = {
        "messages": [HumanMessage(content=f"突发资讯: {news_title}")],
        "market_context": current_price,
        "iterations": 0
    }
    
    try:
        # 启动 Agent 思考流
        async for event in agent_executor.astream(inputs, config=config, stream_mode="updates"):
            for node_name, values in event.items():
                if node_name == "alpha_analyst":
                    msg = values["messages"][-1]
                    if msg.tool_calls:
                        print(f"  └─ 🧠 [Task-{task_id}] 分析师正在调用数据工具...")
                elif node_name == "risk_manager":
                    msg = values["messages"][-1]
                    status = "✅ PASS" if "PASS" in msg.content else "❌ REJECT"
                    print(f"  └─ 🛡️ [Task-{task_id}] 风控终审: {status}")
                elif node_name == "execution_desk":
                    print(f"  └─ 🏦 [Task-{task_id}] 交易台已执行物理操作！")

        # 打印最终闭环结果
        final_state = await agent_executor.aget_state(config)
        messages = final_state.values.get("messages", [])
        if len(messages) >= 1:
            print(f"\n🎯 [Task-{task_id} 闭环完成] 最新系统报告：\n{messages[-1].content}\n")
            print("-" * 60)
            
    except Exception as e:
        print(f"\n⚠️ [Task-{task_id}] 分析流异常阻断: {e}")

async def run_server():
    """建立 gRPC 长连接，持续监听 C++ 数据流"""
    server_addr = os.getenv('GRPC_SERVER_ADDR', 'localhost:50051')
    
    # 无限重连机制，防止 C++ 端重启导致 Python 端崩溃
    while True:
        try:
            async with grpc.aio.insecure_channel(server_addr) as channel:
                stub = fin_agent_pb2_grpc.FinAgentServiceStub(channel)
                print(f"📡 成功连接至 C++ 行情引擎 [{server_addr}] | 系统待命中...")
                
                current_price = "BTC/USDT: N/A"
                data_stream = stub.StreamFinancialData(fin_agent_pb2.Empty())
                
                async for envelope in data_stream:
                    p_type = envelope.WhichOneof('payload')
                    if p_type == 'market':
                        # 毫秒级静默更新盘口数据
                        m = envelope.market
                        current_price = f"{m.symbol}: {m.price:.2f}"
                        # print(f"\r📉 实时盘口: {current_price}", end="", flush=True)
                    elif p_type == 'news':
                        # 收到新闻，立即切分异步任务，主线程继续接管行情
                        asyncio.create_task(process_task(current_price, envelope.news.title))
                        
        except grpc.aio.AioRpcError:
            print(f"⚠️ 无法连接 C++ 引擎，3秒后重试...")
            await asyncio.sleep(3)

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print("==================================================")
    print("📈 FinAgent-Quant Live Execution Node Starting...")
    print("==================================================")
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n👋 监控终端安全下线")