# Changelog

## v2.0.0-alpha.1 (2026-08-04)

### Phase 0: Foundation Fix (已完成)
- **前视偏差修复**: 新增 `_run_next_bar()` 模式, T日信号 → T+1日开盘价成交
- **A股真实成本模型**: 印花税(0.05%, 卖出) + 过户费(沪市) + 最低佣金(5元)
- **涨跌停检查**: 涨停不买, 跌停不卖
- **基准相对指标**: Alpha/Beta/IR/Tracking Error, 无风险利率可配置
- **风控移动止损**: 接入主循环, 支持 add_position/check/remove_position

### Phase 1: Alpha Memory 端到端闭环 (Commit 21)
- **AlphaSignalStore**: 新 SQLite 信号记忆数据库, 记录每条 alpha 信号的完整生命周期
- **Factor Persistence**: AI 挖掘的因子持久化到磁盘, 启动自动恢复
- **IC Decay Auto-Action**: IC 衰减自动降权 (连续5天IC<0 → 禁用)
- **Strategy Bank Bridge**: `UnifiedStrategyBank` 统一 SQLite + JSON 两个策略银行
- **Auto-Revalidate**: 进化完成后自动跨全股票池复测
- **Sentiment Integration**: 情绪因子注册到 FACTOR_REGISTRY
- **Regime-Aware Memory**: 每条信号标记市场状态, 支持状态条件策略选择

### Phase 2: Real Data Adapters (Commit 22)
- **Macro Fetchers**: 8 个宏观指标连接真实 akshare 数据 (CPI/PPI/PMI/LPR/Fed Funds/Unemployment/10Y)
- **Financial Statements**: `FinancialDB` + 资产负债表/利润表/现金流量表获取
- **Historical Fundamental Series**: PE/PB/ROE 历史序列持久化
- **Industry Classification**: 申万行业分类 `IndustryClassifier`
- **6 New Fundamental Factors**: pe_percentile, pb_percentile, roe_trend, profit_margin_change, revenue_acceleration, industry_relative_pe

### Phase 3: Professional Dashboard (Commit 23)
- **LiveDashboard**: 实时数据服务, PnL/信号/持仓推送
- **Fundamental Panel**: PE/PB/ROE 历史 Plotly 折线图
- **Macro Panel**: 宏观指标网格仪表盘
- **Alpha Panel**: 因子胜率/市场状态矩阵/最近信号表

### Phase 4: Paper Broker (Commit 24)
- **PaperBroker**: 统一纸面券商 (ExecutionEngine + TradeRepository + PortfolioManager)
- **OrderDB**: 订单完整生命周期持久化 SQLite
- **Session Recovery**: `PaperBroker.recover()` 从数据库重建状态
- **RealtimePaperBridge**: 实时信号 → 自动纸面交易

### Changed
- `FactorCalculator`: 增加 `auto_reduce_weights()` IC 衰减自动操作
- `SignalComposer.Condition`: 增加 `decay_factor` 字段
- `StrategyGene`: 增加 `cross_symbol_performance`, `is_validated`, `regime_performance`
- `auto_evolve()`: 4 步流程 (AI → 进化 → 复测 → 入库)
- `FACTOR_REGISTRY`: 18 → 28 个因子 (新增 3 情绪 + 6 基本面 + 1 AI)
- `Config.version`: 统一为 `2.0.0-alpha.1`

### Tests
- 315 tests, 73 subtests, 1.04s (273 original + 42 new for alpha memory)

---

## Historical (pre-v2.0.0)

### v0.3.0 (legacy)
- Initial Tkinter GUI (LXL·QuantAxis v5.0)
- 11 strategies (7 classic + 4 preset)
- 18 factor library
- Backtest engine with cost model
- AI strategy factory with genetic evolution
- Real-time Tencent Finance polling
- Multi-user auth system
