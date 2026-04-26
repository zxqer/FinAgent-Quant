# 📈 FinAgent-Quant
> An Industrial-Grade AI Quantitative Trading Architecture
> 工业级 AI 量化交易架构：基于多智能体博弈与动态技能路由

![Version](https://img.shields.io/badge/version-3.0-blue.svg)
![Architecture](https://img.shields.io/badge/architecture-Microservices-orange)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![C++](https://img.shields.io/badge/C%2B%2B-17-darkblue)
![Docker](https://img.shields.io/badge/docker-ready-2496ED)

**[EN]** **FinAgent-Quant** is a state-of-the-art, event-driven quantitative trading terminal. It transcends traditional single-prompt trading bots by implementing a **Multi-Agent Debate Framework**, **Model Context Protocol (MCP) inspired Dynamic Routing**, and **Quant RAG Memory**. Designed for safety and scalability, it physically isolates strategy generation from trade execution, effectively preventing "Rogue AI" accidents.

**[ZH]** **FinAgent-Quant** 是一个前沿的事件驱动型量化交易终端。它超越了传统的单次对话式交易机器人，引入了**多智能体内部博弈框架**、**受 MCP 协议启发的动态技能路由**以及**量化 RAG 记忆库**。系统以资金安全和高并发为核心设计，在物理层面上隔离了“策略生成”与“交易执行”，彻底杜绝 AI 失控带来的“胖手指”风险。

---

## 🏗 Core Architecture / 核心架构

FinAgent-Quant is built on a decoupled microservices architecture, bridging high-frequency C++ data streams with deep Python-based AI reasoning.
系统基于解耦的微服务架构构建，桥接了 C++ 的高频数据流与 Python 的深度 AI 推理。

```text
[ C++ gRPC Engine ] ──(Tick/News Stream)──> [ Python System Bus ]
                                                    │
                                         ┌──────────▼──────────┐
                                         │ Semantic Skill Router│ (MCP Inspired)
                                         └──────────┬──────────┘
                                                    │ (Dynamic Tool Injection)
                                         ┌──────────▼──────────┐
                                         │  Alpha Analyst Node  │ ◄── (Self-Correction Loop)
                                         └──────────┬──────────┘               │
                                                    │ (Proposes Strategy)      │ (REJECT + Feedback)
          ┌─────────────────────────┐    ┌──────────▼──────────┐               │
          │ ChromaDB Quant Memory   │◄───┤  Risk Manager Node  ├───────────────┘
          │ (Historical RAG)        │    └──────────┬──────────┘
          └─────────────────────────┘               │ (PASS)
                                         ┌──────────▼──────────┐
                                         │   Execution Desk    │ (Physically Isolated)
                                         └──────────┬──────────┘
                                                    │ (CCXT / REST API)
                                           [ Binance Testnet ]
```

### 🧠 1. Multi-Agent Debate & Self-Correction (多智能体博弈与自我修正)
The cognitive layer is powered by `LangGraph`, splitting the AI into two orthogonal roles:
* **Alpha Analyst**: An aggressive agent that fetches data, interprets news, and proposes actionable trading strategies.
* **Risk Manager**: A conservative auditor that reviews the Analyst's proposals against historical data and strict risk parameters.
* **Self-Correction**: If the Risk Manager rejects a proposal (e.g., stop-loss is too tight), the Analyst absorbs the feedback and autonomously refines the strategy until it passes compliance.

认知层由 `LangGraph` 驱动，将 AI 拆分为两个相互制衡的角色：
* **分析师 (Alpha)**：积极进取，负责动态调用工具获取数据，并提出包含明确止盈止损的交易策略。
* **风控官 (Risk)**：保守批判，负责审查分析师的研报，评估其敞口和风险收益比。
* **内部纠错**：若风控官驳回策略（如止损过窄），分析师能主动吸收反馈，重新计算点位并再次提交，实现真正的逻辑闭环。

### 🔌 2. MCP-Inspired Dynamic Routing (动态技能路由)
To prevent LLM context explosion and tool hallucination, the system implements a `SkillRouter`. When a market event occurs, a lightweight semantic layer evaluates the intent (e.g., "Crypto Whale" vs. "US CPI") and injects **only the relevant tools** (On-chain metrics, Macro calendar, Stock data) into the Analyst's context window.
为了防止大模型上下文爆炸和工具滥用，系统实现了一个意图识别路由器。当事件发生时，轻量级语义层会评估事件属性，并**按需动态注入**相关技能（如：遇到巨鲸新闻只加载链上工具，遇到 CPI 只加载宏观日历）。

### 📚 3. Quant RAG Memory (量化因果记忆库)
Integrated with **ChromaDB**, the system doesn't just store text—it stores causal market reactions. The Risk Manager retrieves historical events similar to the current context to evaluate if the Analyst's predicted price movement aligns with statistical reality.
深度集成 **ChromaDB**，系统不仅存储文本，更存储“事件与市场反应”的因果快照。风控官在审批前，会检索历史上相似宏观事件发生后的真实涨跌幅与最大回撤，用数据对抗主观臆断。

### 🛡️ 4. Physically Isolated Execution (物理隔离的执行台)
The AI Agents **do not** have access to exchange APIs. They only output JSON-formatted strategies. A dedicated `Execution Desk` node parses the approved strategy and executes the `CCXT` logic. This ensures zero risk of the LLM autonomously generating unauthorized API calls.
AI 智能体**没有任何**直接调用交易所 API 的权限，它们只能输出标准化研报。由完全独立的 `Execution Desk` 节点负责解析风控通过的最终结论，并物理调用 `CCXT` 引擎进行下单，坚决捍卫资金安全底线。

---

## 🛠 Tech Stack / 技术栈

| Component / 模块 | Technology / 技术 |
| :--- | :--- |
| **Data Engine (感知层)** | C++17, gRPC, Protocol Buffers |
| **AI Orchestration (编排层)** | Python 3.12, LangGraph, LangChain |
| **Memory (记忆层)** | ChromaDB, Sentence-Transformers |
| **Data Providers (数据源)** | Tavily API (News), yfinance (Stocks) |
| **Execution (执行层)** | CCXT (Binance Testnet ready) |
| **Deployment (部署)** | Docker, Docker-Compose |

---

## 🚀 Getting Started / 快速启动

### 1. Environment Configuration (环境配置)
Clone the repository and configure your `.env` file in the `python_agent` directory:
```env
DEEPSEEK_API_KEY=your_deepseek_key
DEEPSEEK_BASE_URL=[https://api.deepseek.com/v1](https://api.deepseek.com/v1)
TAVILY_API_KEY=your_tavily_key
BINANCE_TESTNET_API_KEY=your_binance_testnet_key
BINANCE_TESTNET_SECRET=your_binance_testnet_secret
```

### 2. Run via Docker Compose (一键云端部署)
The system is fully containerized. Start the C++ Data Provider and Python AI Node simultaneously:
系统已完全容器化，使用 Docker 一键拉起微服务集群：
```bash
docker-compose up -d --build
```

### 3. Monitor the Live System (监控运行状态)
Watch the AI agents debate and execute trades in real-time:
实时监控多智能体的内部博弈与真实下单过程：
```bash
docker logs -f quant_python_agent
```

---

## ⚠️ Disclaimer / 免责声明

This project is for **educational and research purposes only**. The trading signals generated by the AI agent, even when executed on a Testnet, do not constitute financial advice. The author is not responsible for any financial losses incurred if this architecture is adapted for live trading.

本项目仅供**学术研究与架构探讨**。AI 智能体生成的交易信号及执行逻辑绝不构成任何投资理财建议。强烈建议仅在 Testnet（模拟盘）运行，作者对因修改源码用于实盘造成的任何财务损失概不负责。
```

***
