# LXL·QuantAxis v2.0

> 个人量化交易平台 — 28因子 · 16策略 · 84模块 · 26,700行 · A股/港股/美股 · AI驱动

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-315%20passed-brightgreen)](.)
[![Lines](https://img.shields.io/badge/code-26,700_lines-blue)](.)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0--alpha.1-orange)](.)

---

## 快速开始

```bash
pip install -r requirements.txt

# 三选一启动:
python web_modern.py     # Web 平台 → http://127.0.0.1:5000  (推荐)
python main.py           # CLI 交互菜单 + --tune/--allocate/--discover
python src/app.py        # 桌面应用 (Tkinter GUI)
```

## 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                Web (Flask-SocketIO) / CLI / Desktop           │
├──────────────────────────────────────────────────────────────┤
│  Alpha Memory   │ Backtest    │ Realtime    │ Paper Broker   │
│  信号生命周期     │ T+1 引擎    │ HTTP轮询     │ 订单持久化       │
│  因子胜率/状态   │ A股成本模型  │ K线聚合      │ 会话恢复         │
│  IC衰减自动降权  │ 基准指标     │ SocketIO推送 │ 实时自动交易      │
├──────────────────────────────────────────────────────────────┤
│  16 Strategies │ 28 Factors │ Risk Gate │ Alerts │ Tuner    │
├──────────────────────────────────────────────────────────────┤
│  AI: LLM Chat · Genetic Miner · Auto Evolve · Factor Mine   │
├──────────────────────────────────────────────────────────────┤
│  Data: akshare · yfinance · SQLite ×10 · Macro · Financials │
└──────────────────────────────────────────────────────────────┘
```

## Web 界面 (5 个页面, 60+ API)

| 页面 | 路由 | 功能 |
|------|------|------|
| **v2.0 仪表盘** | `/` `/v2` | K线蜡烛图 · Alpha信号面板 · Broker订单 · 宏观指标 · 策略银行 · 自动交易开关 |
| **经典面板** | `/classic` | 全功能: 回测 · AI对话 · 策略构建 · 因子分析 · 个股诊断 · 每日快扫 · 指数估值 |
| **交易工作室** | `/studio` | K线实时图表 · 策略信号推送 |
| **模拟交易** | `/game` | 100万模拟金 · T+1买卖 · 全平台排行榜 |
| **管理后台** | `/admin` | 用户管理 · 系统状态 · 数据库迁移 |

## CLI 命令

```bash
python main.py                          # 交互菜单 (20+ 功能)
python main.py --tune ma_cross          # 策略参数优化 (Optuna)
python main.py --tune rsi --trials 100  # 自定义尝试次数
python main.py --allocate               # 策略权重分配 (风险平价等4种方法)
python main.py --allocate --method hrp  # 分层风险平价
python main.py --discover 600519        # AI 因子发现 (遗传编程)
python main.py --report                 # 生成每日简报
```

## 策略库 (16个)

### 经典策略 (7)
| 键 | 名称 | 描述 |
|----|------|------|
| `ma_cross` | 双均线交叉 | 金叉买入, 死叉卖出 |
| `rsi` | RSI超买超卖 | RSI<超卖线买入, >超买线卖出 |
| `macd` | MACD金叉死叉 | DIF上穿DEA买入 |
| `bollinger` | 布林带 | 下轨反弹买入 |
| `turtle` | 海龟交易 | 突破N日高点, ATR止损 |
| `mean_reversion` | 均值回归 | 偏离均线逆势入场 |
| `momentum` | 动量突破 | 突破高点+成交量确认 |

### 高级策略 (5)
| 键 | 名称 | 描述 |
|----|------|------|
| `adaptive` | 自适应复合 | 检测趋势/震荡/下跌, 切换最优子策略 |
| `trend_short` | 趋势破位做空 | 价格破位做空+回升平仓 |
| `dual_direction` | 双向交易 | 趋势向上做多, 向下做空 |
| `regime_aware` | 状态感知 | 5状态分类, 自适应双向 |
| `ensemble` | 策略集成投票 | 多策略加权投票 |

### 因子策略 (4)
| 键 | 名称 | 信号逻辑 |
|----|------|----------|
| `contrarian_v1` | 逆势V1 | RSI超卖(3) + 布林下轨(2) + 放量(1) |
| `trend_following_v1` | 趋势跟踪V1 | 金叉(3) + 强趋势(2) + 动量(1) |
| `volume_breakout_v1` | 量价突破V1 | 放量2x(3) + 动量(2) + 趋势(1) |
| `mean_reversion_v2` | 均值回归V2 | 偏离均线(2) + 低波动(1) + 锤子线(2) |

## 因子体系 (28个)

| 类别 | 数量 | 因子 | 来源 |
|------|------|------|------|
| 趋势 | 4 | ma_deviation, ma_alignment, ma_slope, trend_strength | 内置 |
| 动量 | 5 | rsi_norm, macd_hist, roc_10, price_position, momentum_score | 内置 |
| 波动 | 4 | volatility, bollinger_pos, bollinger_width, atr_ratio | 内置 |
| 成交量 | 4 | volume_ratio, volume_trend, obv_divergence, **vol_exhaustion** | 内置+v2.0 |
| 形态 | 2 | hammer, engulfing | 内置 |
| 情绪 | 3 | sentiment_score, sentiment_heat, sentiment_extreme | v2.0 (AI) |
| 基本面 | 6 | pe_percentile, pb_percentile, roe_trend, profit_margin_change, revenue_acceleration, industry_relative_pe | v2.0 |

## 完整功能清单

### 回测系统
- T+1 无前视偏差成交 (信号T日 → T+1开盘)
- A股真实成本: 佣金(最低5元) · 印花税(0.05%卖出) · 过户费(沪市)
- 涨跌停检查 · 冲击成本 · 限价单模拟 · 做多/做空
- 基准指标: Alpha · Beta · IR · Tracking Error · 可配置无风险利率
- Brinson 收益归因: 选股贡献 vs 择时贡献
- 滑点敏感度分析
- 参数优化: Optuna贝叶斯 + 网格搜索 + Walk-Forward

### Alpha Memory (v2.0 核心)
- 信号记忆数据库: 每条信号完整生命周期追踪
- 因子胜率 · 市场状态表现矩阵 · IC衰减时间线
- **IC衰减自动降权**: IC<0 连续5天→禁用, 3天→0.3, 弱效→0.5
- 因子持久化: AI挖掘因子重启自动恢复
- 策略银行统一: 进化银行 + 用户银行双库统一查询
- 进化后自动跨股票复测

### AI 智能体
- LLM 对话 (DeepSeek/OpenAI/Qwen)
- 策略工厂: AI分析→种子→遗传进化→复测→入银行
- 自然语言→策略: 描述思路→AI构建因子策略→回测
- 遗传编程因子发现 (GeneticFactorMiner)
- AI 复盘 · 市场简报 · 策略顾问

### 实时系统
- 腾讯财经 HTTP 轮询 (3s间隔, 自动降级)
- Flask-SocketIO WebSocket 推送
- K线聚合: 1min/5min/15min
- 策略信号实时评估 (RSI/MA/布林)
- **告警引擎**: 规则+YAML配置 → 钉钉/邮件/微信/Telegram
- 信号冷却 (5分钟内不重复触发)

### 风控体系
- **闸门** (PreTradeRiskGate): 6道规则 — 总仓位/单票集中/回撤止损/日内亏损/现金/黑名单
- 移动止损 · 回撤熔断 · 凯利仓位
- 风险平价 · Black-Litterman · 分层风险平价 (HRP)
- API 速率限制 (HTTP 429, 6条敏感路由)

### Paper Broker
- 统一纸面券商: ExecutionEngine + TradeRepository + PortfolioManager
- 订单持久化 (SQLite) · 会话恢复 · 冰山订单
- 实时信号→自动纸面交易桥接
- 券商适配器: PaperBroker + QMTAdapter (工厂模式)

### 数据层
- A股/港股/美股 OHLCV (akshare + yfinance)
- 宏观指标: CPI/PPI/PMI/LPR/Fed/失业率/10Y国债 (8个, 真实akshare)
- 三张报表: 资产负债表/利润表/现金流量表
- PE/PB/ROE 历史序列 (SQLite 持久化)
- 申万行业分类
- 统一数据仓库 (CSV/SQLite/Parquet)

### 仪表盘 (6个面板)
- 系统总览 · 绩效热力图 · 数据健康
- 基本面面板 (PE/PB/ROE 折线图)
- 宏观面板 (8指标网格)
- Alpha记忆面板 (因子胜率/状态矩阵/信号表)

### 其他
- 每日简报 (持仓分析 + 强势股扫描)
- 模拟交易 (100万金, T+1, 排行榜)
- 多用户认证 (JWT)
- 信号延迟垫片 (消除未来函数)
- 研究复现清单 (自动生成 JSON)
- Prometheus 监控指标

## 数据存储

| 数据库 | 路径 | 内容 |
|--------|------|------|
| `alpha_memory.db` | D:/trading_data/ | 信号生命周期记忆 |
| `backtest_results.db` | D:/trading_data/ | 批量回测结果 |
| `trades.db` | D:/trading_data/ | 交易日志+盈亏 |
| `financial_series.db` | D:/trading_data/ | PE/PB/ROE 历史 |
| `financials.db` | D:/trading_data/ | 三张财务报表 |
| `orders.db` | D:/trading_data/ | Paper Broker 订单 |
| `market_data.db` | D:/trading_data/ | OHLCV 行情缓存 |
| `strategy_bank.db` | D:/trading_data/ | 用户策略+回测 |
| `users.db` | D:/trading_data/ | 用户+持仓+配置 |
| `bank.json` | D:/trading_data/strategy_bank/ | AI进化策略 |

## 项目结构

```
LXL-QuantAxis/
├── main.py                  # CLI (交互+ --tune/--allocate/--discover)
├── web_modern.py            # Web (Flask-SocketIO, 60+ API, 5页面)
├── web_app.py               # Web (Flask)
├── src/app.py               # 桌面 (Tkinter, 侧边栏全部功能)
├── daily_runner.py          # 每日自动扫描
├── CHANGELOG.md             # 变更日志
├── ARCHITECTURE.md          # 详细架构文档
├── config/
│   └── alerts.yaml          # 告警规则配置
├── src/                     # 84 模块, 26,700 行
│   ├── ai/                  # AlphaStore, FactorPersistence, BankBridge,
│   │                        #   Factory, Sentiment, FactorDiscovery
│   ├── analysis/            # Charts, Reports, Attribution, FactorCorr, RegimeDetector
│   ├── backtest/            # Engine, DataFeed, Metrics, Optimizer, BatchRunner,
│   │                        #   FactorValidator, Macro, MarketMeta, Symbols, Providers
│   ├── dashboard/           # Visual, Live, AlphaPanel, MacroPanel, FundamentalPanel
│   ├── data/                # Loader, Financials, MacroFetchers, StockDB, MarketDB
│   ├── execution/           # Executor, PaperBroker, Bridge, Engine, Brokers/
│   ├── factors/             # Definitions, Composer, Fundamental, VolumeExhaustion
│   ├── journal/             # CLI, Manifest
│   ├── portfolio/           # Metrics, UserPortfolioManager, Optimizer
│   ├── realtime/            # Collector, Engine, KLine, AlertEngine
│   ├── risk/                # Manager, Gate
│   ├── strategies/          # Library(12), Base, Adaptive, Short, Regime, Ensemble
│   ├── utils/               # SignalLag, RateLimiter, StrategyTuner
│   ├── auth/                # JWT认证
│   ├── database/            # SQLAlchemy ORM
│   ├── report/              # 每日报告
│   └── index/               # 估值+轮动
└── tests/                   # 315 passed, 73 subtests, ~1s
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `QUANT_DATA_DIR` | `D:/trading_data` | 数据根目录 |
| `QUANT_BROKER` | `paper` | 券商: paper/qmt |
| `QUANT_MONITOR` | (空) | 设 `true` 开启停滞监控 |
| `QMT_ACCOUNT` | (空) | QMT 账户ID |
| `AI_API_KEY` | (空) | LLM API Key |

## AI 配置

`D:/trading_data/ai_config.json`:
```json
{"api_key": "sk-xxx", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"}
```
支持所有 OpenAI 兼容接口。

## 测试

```bash
python -m pytest tests/ -q
# 315 passed, 73 subtests in ~1.0s
```

## License

MIT © Ryhs666
