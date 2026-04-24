import json
import os
import ccxt
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.tools import tool

# ⚠️ 确保在实例化任何工具前加载环境变量
load_dotenv()

# -----------------------------------------------------
# 1. 定义独立的技能 (Skills)
# -----------------------------------------------------

try:
    from langchain_tavily import TavilySearch
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults as TavilySearch

def get_search_skill():
    return TavilySearch(max_results=2)

@tool
def get_onchain_metrics(asset: str) -> str:
    """
    当新闻涉及大户异动、巨鲸转账时调用此工具。
    输入资产名称（如 BTC, ETH），返回其实时链上指标。
    """
    metrics = {"BTC": {"whale_activity": "high", "exchange_inflow": "+15%"}, "ETH": {"gas_fees": "spiking"}}
    return json.dumps(metrics.get(asset.upper(), {"status": "unknown"}), ensure_ascii=False)

@tool
def check_macro_calendar(date_str: str) -> str:
    """
    当新闻涉及美联储、CPI、非农等宏观数据发布时调用。
    输入日期（如 today），返回当天的重要宏观事件。
    """
    return "今天晚上 20:30 有核心 PCE 数据发布，市场预期波动率将激增。"

@tool
def get_stock_data(ticker: str) -> str:
    """
    获取具体公司（如 AAPL, NVDA）的股票信息。
    输入股票代码，返回其实时价格。
    """
    try:
        stock = yf.Ticker(ticker)
        return json.dumps({"current_price": stock.info.get('regularMarketPrice', 'N/A')})
    except Exception as e:
        return f"获取失败: {str(e)}"

# --- 2. 🌟 物理隔离的交易台引擎 (保留但不暴露给大模型) ---
@tool
def execute_trade(symbol: str, side: str, amount_usd: float) -> str:
    """
    物理交易执行器：此工具仅由系统底层的 Execution Desk 节点直接调用，不可暴露给 LLM。
    """
    try:
        exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_TESTNET_API_KEY'),
            'secret': os.getenv('BINANCE_TESTNET_SECRET'),
            'enableRateLimit': True,
        })
        exchange.set_sandbox_mode(True) # 强制进入 Testnet

        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        amount = round(amount_usd / current_price, 5)
        
        if amount_usd < 10:
            return f"❌ 交易失败: 下单金额 ${amount_usd} 太小，至少需要 10 USDT。"

        print(f"\n⚡ [Execution Desk] 正在物理执行 {side.upper()} 订单: {amount} {symbol} (价值: ${amount_usd})...")
        order = exchange.create_market_order(symbol=symbol, side=side.lower(), amount=amount)
        
        return json.dumps({
            "status": "SUCCESS",
            "order_id": order['id'],
            "executed_price": order['average'] or current_price,
            "executed_amount": order['filled'],
            "cost_usdt": order['cost']
        }, ensure_ascii=False)
        
    except ccxt.InsufficientFunds:
        return "❌ 交易执行失败: 模拟盘可用 USDT 余额不足！"
    except Exception as e:
        return f"❌ 交易执行异常: {str(e)}"

# --- 3. 更新动态路由器 (隔离武器库) ---
class SkillRouter:
    def __init__(self):
        self.available_skills = {
            "search": get_search_skill(),
            "onchain": get_onchain_metrics,
            "macro": check_macro_calendar,
            "stock": get_stock_data
            # ⚠️ 核心修复：execute_trade 不在这里注册！
        }
        
    def route_skills(self, news_content: str) -> list:
        selected_tools = [self.available_skills["search"]] 
        lower_news = news_content.lower()
        
        if any(word in lower_news for word in ["whale", "transfer", "on-chain"]):
            selected_tools.append(self.available_skills["onchain"])
            
        if any(word in lower_news for word in ["fed", "cpi", "macro"]):
            selected_tools.append(self.available_skills["macro"])
            
        if any(word in lower_news for word in ["stock", "aapl", "nvda"]):
            selected_tools.append(self.available_skills["stock"])
            
        return selected_tools

skill_router = SkillRouter()