import asyncio
from langchain_core.messages import HumanMessage
import uuid

# 导入我们重构后的大脑组件
from skill_registry import skill_router
from agent_brain import agent_executor

async def run_test_case(test_id: str, news_title: str, current_price: str):
    print(f"\n{'='*50}")
    print(f"🧪 [测试案例 {test_id}]: {news_title}")
    print(f"{'='*50}")
    
    # --- 1. 验证动态路由 (打印出来看看选中了什么工具) ---
    active_skills = skill_router.route_skills(news_title)
    skill_names = [skill.name for skill in active_skills]
    print(f"✅ 意图识别完成! 动态加载技能: {skill_names}")
    print("-" * 50)
    
    # --- 2. 模拟完整的分析流程 ---
    config = {
        "configurable": {"thread_id": f"test_session_{test_id}"},
        "recursion_limit": 25 
    }
    
    inputs = {
        "messages": [HumanMessage(content=f"突发资讯: {news_title}")],
        "market_context": current_price,
        "iterations": 0
    }
    
    try:
        # 运行 Agent 流程
        async for event in agent_executor.astream(inputs, config=config, stream_mode="updates"):
            for node_name, values in event.items():
                if node_name == "alpha_analyst":
                    msg = values["messages"][-1]
                    if msg.tool_calls:
                        # 打印模型实际调用的工具
                        calls = [call['name'] for call in msg.tool_calls]
                        print(f"  └─ 🧠 分析师申请调用: {calls}")
                    elif msg.content:
                        print(f"  └─ 🧠 分析师阶段总结: {msg.content[:80]}...")
                elif node_name == "tools":
                    print(f"  └─ ⚙️  执行外部技能获取数据...")
                elif node_name == "risk_manager":
                    msg = values["messages"][-1]
                    status = "✅ PASS" if "PASS" in msg.content else "❌ REJECT"
                    print(f"  └─ 🛡️ 风控官审查结果: {status}")

        # 获取最终结果
        final_state = await agent_executor.aget_state(config)
        messages = final_state.values.get("messages", [])
        if len(messages) >= 2:
            print("\n🎯 【最终决策闭环】:")
            print(f"分析师: {messages[-2].content.split('[理由]')[0].strip()}...") # 只截取前面的建议部分
            
    except Exception as e:
        print(f"\n⚠️ 测试出错: {e}")

async def main():
    # 测试 1: 普通新闻 (只应该触发 Search)
    await run_test_case(
        test_id="1",
        news_title="Solana network upgrade completed successfully",
        current_price="BTC/USDT: 64500"
    )
    
    # 测试 2: 链上新闻 (应该触发 Search + OnChain)
    await run_test_case(
        test_id="2",
        news_title="Massive Whale transfer detected: 15,000 BTC moved to Binance wallet",
        current_price="BTC/USDT: 64200"
    )
    
    # 测试 3: 宏观新闻 (应该触发 Search + Macro)
    await run_test_case(
        test_id="3",
        news_title="US CPI data slightly higher than expected, Fed rate cut unlikely",
        current_price="BTC/USDT: 63800"
    )

if __name__ == "__main__":
    # 清屏显示
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("🚀 启动动态技能路由深度测试...\n")
    asyncio.run(main())