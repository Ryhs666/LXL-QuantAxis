# LXL·QuantAxis — 架构文档

> v2.0.0-alpha.1 | 2026-08-04
> 个人量化交易平台 · Alpha 记忆闭环

---

## 1. 系统总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    web_modern.py (Flask-SocketIO)                        │
│                    app.py (Tkinter 桌面) · main.py (CLI)                 │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Dashboard│ │Backtest  │ │  AI      │ │Realtime  │ │ Paper    │      │
│  │ 6 Panels │ │ Engine   │ │ Alpha    │ │ Collector│ │ Broker   │      │
│  │          │ │ T+1 成交  │ │ Memory   │ │ + Engine │ │ + Bridge │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 16       │ │ 28       │ │ Risk     │ │ Data     │ │ Portfolio│      │
│  │Strategies│ │ Factors  │ │ Manager  │ │Adapters  │ │ Metrics  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
   ┌──────────┐          ┌──────────────┐         ┌──────────┐
   │ akshare  │          │  SQLite × 10 │         │ yfinance │
   │ 新浪/东财 │          │  Persistence │         │ US/HK    │
   └──────────┘          └──────────────┘         └──────────┘
```

## 2. Alpha Memory 闭环

```
                    ┌─────────────────────────┐
                    │   AlphaSignalStore       │
                    │   alpha_memory.db        │
                    │                          │
   FactorCalculator │  信号记录 → 结果更新      │
   SignalComposer   │  因子胜率 · 状态矩阵      │
   SentimentAnalyzer│  IC衰减时间线             │
   StrategyEngine   │  因子健康度评估            │
                    └──────────┬──────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │ IC Decay     │   │FactorPersistence│ │UnifiedBank   │
  │ Auto-Action  │   │  mined_factors │   │ Bridge       │
  │ 自动降权/禁用 │   │  重启自动恢复   │   │ 双银行统一    │
  └──────────────┘   └──────────────┘   └──────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  auto_evolve()      │
                    │  1. AI 分析回测数据  │
                    │  2. AI 生成种子策略  │
                    │  3. 遗传算法进化     │
                    │  4. 跨股票全市场复测  │
                    │  5. 最佳策略入银行   │
                    └─────────────────────┘
```

## 3. 数据流

```
  腾讯财经 API ──HTTP──▶ RealtimeCollector (3s轮询)
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              KLineAggregator  StrategyEngine  LiveDashboard
              1/5/15min K线    RSI/MA/BB信号   PnL/持仓推送
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                          Flask-SocketIO
                          WebSocket emit
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              price_update   strategy_signal  kline_update
              alert_triggered   (浏览器前端)
```

## 4. Paper Broker 架构

```
  StrategyEngine 信号
        │
        ▼
  RealtimePaperBridge
  auto_trade_enabled?
        │
        ▼
  PaperBroker.place_order()
        │
        ├──▶ OrderDB (orders.db) ── 持久化
        ├──▶ TradeRepository (trades.db) ── 交易记录
        └──▶ PortfolioManager (users.db) ── 持仓更新
                │
                ▼
        PaperBroker.recover() ── 会话恢复
```

## 5. 回测引擎

```
  BacktestEngine.run(strategy, data, execution_mode="next_open")
        │
        ├── _run_next_bar (默认, 无前视偏差)
        │      T日收盘信号 → T+1日开盘价成交
        │      涨跌停检查 · 冲击成本 · 限价单模拟
        │
        └── _run_legacy (旧模式, 同日收盘价成交)
               仅用于对比验证

  Portfolio (模拟账户)
        ├── A股真实成本: 佣金(最低5元) + 印花税(0.05%卖出) + 过户费(沪市)
        ├── 做多/做空/平空 双向交易
        └── mark_to_market() 每日估值

  绩效指标:
        绝对指标: CAGR · Sharpe · Sortino · MaxDD · Calmar · 胜率 · 盈亏比
        相对指标: Alpha · Beta · IR · Tracking Error (vs 基准)
```

## 6. 数据存储全景

| 数据库 | 路径 | 引擎 | 内容 |
|--------|------|------|------|
| alpha_memory.db | D:/trading_data/ | sqlite3 | Alpha 信号生命周期记忆 |
| backtest_results.db | D:/trading_data/ | sqlite3 | 批量回测结果 |
| trades.db | D:/trading_data/ | sqlite3 | 交易日志+配对盈亏 |
| financial_series.db | D:/trading_data/ | sqlite3 | PE/PB/ROE历史序列 |
| financials.db | D:/trading_data/ | sqlite3 | 三张财务报表 |
| orders.db | D:/trading_data/ | sqlite3 | Paper Broker 订单 |
| market_data.db | D:/trading_data/ | sqlite3 | OHLCV 行情缓存 |
| strategy_bank.db | D:/trading_data/ | sqlite3 | 用户策略+回测记录 |
| bank.json | D:/trading_data/strategy_bank/ | JSON | AI进化策略基因 |
| mined_factors/ | D:/trading_data/ | JSON | AI挖掘因子持久化 |
| users.db | D:/trading_data/ | SQLAlchemy | 用户+持仓+配置 |

## 7. 因子体系 (28)

| 类别 | 因子 | 新增于 |
|------|------|--------|
| trend (4) | ma_deviation, ma_alignment, ma_slope, trend_strength | v0.x |
| momentum (5) | rsi_norm, macd_hist, roc_10, price_position, momentum_score | v0.x |
| volatility (4) | volatility, bollinger_pos, bollinger_width, atr_ratio | v0.x |
| volume (4) | volume_ratio, volume_trend, obv_divergence, vol_exhaustion | v2.0 |
| pattern (2) | hammer, engulfing | v0.x |
| sentiment (3) | sentiment_score, sentiment_heat, sentiment_extreme | v2.0 |
| fundamental (6) | pe_percentile, pb_percentile, roe_trend, profit_margin_change, revenue_acceleration, industry_relative_pe | v2.0 |

## 8. 已注册策略清单

### 经典策略 (7)
| 键 | 名称 | 描述 |
|----|------|------|
| ma_cross | 双均线交叉 | 金叉买入, 死叉卖出 |
| rsi | RSI超买超卖 | RSI<超卖线买入, >超买线卖出 |
| macd | MACD金叉死叉 | DIF上穿DEA买入, 下穿卖出 |
| bollinger | 布林带 | 下轨反弹买入, 中轨卖出 |
| turtle | 海龟交易 | 突破N日高点买入, ATR止损 |
| mean_reversion | 均值回归 | 偏离均线逆势入场 |
| momentum | 动量突破 | 突破高点+成交量确认 |

### 高级策略 (5)
| 键 | 名称 | 描述 |
|----|------|------|
| adaptive | 自适应复合 | 自动检测趋势/震荡/下跌, 切换最优子策略 |
| trend_short | 趋势破位做空 | 价格破位做空+回升平仓 |
| dual_direction | 双向交易 | 趋势向上做多, 向下做空 |
| regime_aware | 状态感知 | 5状态分类, 自适应双向交易 |
| ensemble | 策略集成投票 | 多策略加权投票, 动态调整权重 |

### 独有因子策略 (4)
| 键 | 名称 | 信号逻辑 |
|----|------|----------|
| contrarian_v1 | 逆势交易V1 | RSI超卖(3) + 布林下轨(2) + 放量(1) → ≥4 |
| trend_following_v1 | 趋势跟踪V1 | 金叉(3) + 强趋势(2) + 动量(1) → ≥4 |
| volume_breakout_v1 | 量价突破V1 | 放量2x(3) + 动量(2) + 趋势(1) → ≥4 |
| mean_reversion_v2 | 均值回归V2 | 偏离均线(2) + 低波动(1) + 锤子线(2) → ≥3 |

## 9. WebSocket 配置

| 参数 | 值 | 说明 |
|------|-----|------|
| async_mode | threading | Windows 兼容 |
| ping_interval | 25s | 心跳间隔 |
| ping_timeout | 120s | 弱网兜底 |
| max_http_buffer_size | 1MB | 消息缓冲区 |

错误码日志: 1000 / 1001 / 1006 / 1008(鉴权失败) / 1009 / 1011 / 1012 / 401

## 10. 关键文件索引

| 文件 | 核心类/函数 | 用途 |
|------|-----------|------|
| src/ai/alpha_store.py | AlphaSignalStore | 信号记忆 |
| src/ai/factor_persistence.py | FactorPersistence | 因子持久化 |
| src/ai/bank_bridge.py | UnifiedStrategyBank | 双银行统一 |
| src/ai/factory.py | auto_evolve() | 策略进化 |
| src/backtest/engine.py | BacktestEngine | 回测引擎 |
| src/backtest/metrics.py | calc_all_metrics() | 绩效指标 |
| src/execution/paper_broker.py | PaperBroker | 纸面券商 |
| src/execution/bridge.py | RealtimePaperBridge | 实时桥接 |
| src/data/macro_fetchers.py | 8 fetchers | 宏观数据 |
| src/data/financials.py | FinancialDB | 基本面数据 |
| src/data/stock_db.py | IndustryClassifier | 申万行业 |
| src/factors/volume_exhaustion.py | compute_volume_exhaustion_factor() | 量能耗尽因子 |
| src/dashboard/live.py | LiveDashboard | 实时仪表盘 |
| src/realtime/collector.py | RealtimeCollector | 行情采集 |
| src/realtime/engine.py | StrategyEngine | 策略信号引擎 |
| src/realtime/kline.py | KLineAggregator | K线聚合 |

---

## 11. 测试

```bash
python -m pytest tests/ -q    # 315 passed, 73 subtests, ~1s
```

测试覆盖: data_path, symbols, providers, market_metadata, macro, portfolio_metrics, alpha_store, factor_persistence, bank_bridge, ic_decay_autoaction
