import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime

class QuantRAGMemory:
    def __init__(self, db_path="./quant_memory_db"):
        """
        初始化持久化的本地向量数据库
        """
        self.client = chromadb.PersistentClient(path=db_path)
        
        # 使用默认的轻量级句子嵌入模型 (all-MiniLM-L6-v2)
        # 第一次运行会自动下载几兆的模型权重
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # 获取或创建集合（Collection 相当于关系型数据库的 Table）
        self.collection = self.client.get_or_create_collection(
            name="historical_market_events",
            embedding_function=self.embedding_fn
        )
        print(f"✅ 量化记忆库已加载，当前记忆容量: {self.collection.count()} 条事件")

    def remember_event(self, event_id: str, news_title: str, asset: str, 
                       return_24h: float, max_drawdown: float, context: str):
        """
        【存入记忆】：将突发新闻及其随后的真实市场表现存入数据库
        """
        # Document (文档): 是大模型用来计算相似度的主体
        # Metadata (元数据): 是不参与向量计算，但作为结果强绑定的统计数据
        self.collection.add(
            ids=[event_id],
            documents=[news_title],
            metadatas=[{
                "asset": asset,
                "return_24h": return_24h,       # 24小时真实涨跌幅
                "max_drawdown": max_drawdown,   # 期间最大回撤
                "market_context": context,      # 当时的宏观/技术面状态
                "recorded_at": datetime.now().strftime("%Y-%m-%d")
            }]
        )
        print(f"📥 成功写入记忆: [{event_id}] {news_title}")

    def recall_similar_events(self, current_news: str, n_results: int = 3) -> str:
        """
        【检索记忆】：根据当前的新闻，召回历史上最相似的事件并格式化为 Prompt
        """
        if self.collection.count() == 0:
            return "历史档案库为空，无参考数据。"

        # 执行向量相似度检索
        results = self.collection.query(
            query_texts=[current_news],
            n_results=min(n_results, self.collection.count())
        )

        # 将检索到的底层数据格式化为自然语言，供风控官(LLM)阅读
        report = f"🔍 针对当前事件「{current_news}」，系统检索到以下历史相似案例：\n\n"
        
        for i in range(len(results['ids'][0])):
            doc = results['documents'][0][i]
            meta = results['metadatas'][0][i]
            distance = results['distances'][0][i] # 距离越小，相似度越高
            
            # 格式化输出
            report += f"案例 {i+1} (相似度距离: {distance:.2f}):\n"
            report += f"  - 历史事件: {doc}\n"
            report += f"  - 当时背景: {meta['market_context']}\n"
            report += f"  - 【24H 真实走势】: 涨跌幅 {meta['return_24h']}%, 最大回撤 {meta['max_drawdown']}%\n"
            report += "-" * 40 + "\n"
            
        return report

# ==========================================
# 🧪 测试与模拟运行
# ==========================================
if __name__ == "__main__":
    memory = QuantRAGMemory()

    # 1. 模拟行情引擎在收盘后，自动将"历史经验"写入数据库
    print("\n--- 正在注入历史经验 ---")
    memory.remember_event(
        event_id="evt_001",
        news_title="SEC officially delays decision on Spot Bitcoin ETF",
        asset="BTC",
        return_24h=-4.5,
        max_drawdown=-8.2,
        context="BTC price at $42,000, high market anticipation, VIX elevated."
    )
    
    memory.remember_event(
        event_id="evt_002",
        news_title="Federal Reserve announces unexpected 50bps rate cut",
        asset="BTC",
        return_24h=6.8,
        max_drawdown=-1.5,
        context="Macro easing, DXY dropping, BTC at $58,000."
    )

    memory.remember_event(
        event_id="evt_003",
        news_title="Major Crypto Exchange halts withdrawals due to anomaly",
        asset="BTC",
        return_24h=-12.4,
        max_drawdown=-18.0,
        context="Market panic, extreme liquidations."
    )

    # 2. 模拟当前的实盘监控阶段，风控官拿着新新闻去查阅历史
    print("\n--- 实时风控检索测试 ---")
    current_alert = "SEC pushes back timeline for Ethereum Spot ETF approval"
    print(f"🚨 当前收到突发新闻: {current_alert}\n")
    
    # 检索历史记忆
    risk_report = memory.recall_similar_events(current_alert, n_results=2)
    print(risk_report)
    