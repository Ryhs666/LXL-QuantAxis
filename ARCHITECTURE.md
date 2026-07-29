# 投资策略模型系统 — 架构文档

> v0.4 | 2026-07-29  
> 属于你自己的量化交易体系

---

## 1. 系统总览

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            main.py (主菜单)                               │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬────────┤
│📊 管理中枢 │🔍 快速验证│🩺 个股诊断│🔄 每日快扫│🧪 策略回测│🔬 批量回测│⚙️ 优化  │
│Dashboard │QuickTest│Diagnosis │DailyScan │Backtest  │  Batch   │Optimize│
├──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴────────┤
│                     📒 交易日志 · 🧬 因子体系 · 📊 绩效分析                 │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   🖥️ 可视化面板   │  │   回测 + 优化    │  │  诊断 + 因子     │
│  HTML Dashboard  │  │  Engine/Optimize│  │  Diagnosis/     │
│  (浏览器打开)     │  │  (核心计算引擎)   │  │  Factors/Scan   │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │   数据层 (双源)   │
                    │ 新浪 + 东方财富   │
                    │  + 本地CSV缓存   │
                    └─────────────────┘
```

### 🖥️ 主菜单结构 (v0.4)

| 选项 | 功能 | 说明 |
|------|------|------|
| `0` | 📊 系统总览 | 仪表盘 · 状态 · 可视化 |
| `7` | 📥 数据管理 | 下载 · 缓存 · 一览 |
| `V` | 🔍 快速验证 | 选股票 → 设时间 → 选策略 → 一键回测 |
| `D` | 🩺 个股诊断 | 全策略扫描 · 投资者适配 · 入场时机 · 仓位建议 |
| `R` | 🔄 每日快扫 | 刷新行情 · 扫描13只默认标的 · 信号排名 |
| `1` | 📒 交易日志 | 记录买卖 · 持仓 · 复盘 · 盈亏 |
| `2` | 🧪 策略回测 | 单标的 × 策略 |
| `3` | 🔬 批量回测 | N标的×N策略 |
| `5` | ⚙️ 参数优化 | 网格搜索 · Walk-Forward |
| `8` | 📊 指数估值 | PE/PB分位 · 估值评级 |
| `9` | 🔄 指数轮动 | 动量轮动 · 定投回测 |
| `A` | 🤖 AI助手 | 复盘 · 策略 · 对话 |
| `4` | 📊 绩效分析 | 报表 · 图表 · 对比 |
| `6` | 🧬 因子体系 | 18因子 · 信号组合 |

### 🖥️ 可视化管理系统

| 仪表盘 | 内容 | 入口 |
|--------|------|------|
| **管理面板** | KPI总览 + 策略清单 + 最近交易 | `菜单0→1` |
| **绩效仪表盘** | 夏普/收益矩阵 + TOP排名 | `菜单0→2` |
| **数据健康** | 缓存状态 + 覆盖范围 | `菜单0→3` |

所有仪表盘为自包含 HTML，浏览器直接打开，无需服务器。

## 2. 目录结构

```
PythonProject1/
│
├── main.py                           # 入口：13个菜单选项 (v0.4)
├── daily_runner.py                   # 每日自动诊断脚本 (新增)
├── web_app.py                        # Flask Web 平台
├── launcher.py                       # 桌面启动器
├── build_exe.py                      # 打包脚本
├── requirements.txt                  # 依赖
├── config.yaml                       # 全局配置 (可选)
├── ARCHITECTURE.md                   # 本文档
│
├── src/
│   ├── __init__.py
│   │
│   ├── config.py                     # 配置管理
│   │   ├── Config                    #   单例配置类
│   │   └── DEFAULTS                  #   默认值字典
│   │
│   ├── utils.py                      # 工具集
│   │   ├── get_logger()              #   结构化日志
│   │   ├── @retry                    #   重试装饰器
│   │   ├── ProgressBar               #   进度条
│   │   ├── Timer                     #   计时器
│   │   └── safe_call()               #   安全执行
│   │
│   ├── models/                       # ── 数据模型层 ──
│   │   ├── trade.py
│   │   │   ├── Trade                 #   交易数据类 (dataclass)
│   │   │   └── TradeRepository       #   SQLite CRUD + CSV导入导出
│   │   │       ├── add() / delete() / update()
│   │   │       ├── find_all() / find_open_positions()
│   │   │       ├── set_paired_trade() / calc_pnl()
│   │   │       ├── get_all_pnl()
│   │   │       └── export_csv() / import_csv()
│   │   │
│   │   └── strategy.py
│   │       ├── Signal                #   买卖信号 (action/symbol/date/price/quantity/reason)
│   │       └── StrategyConfig        #   策略参数 (资金/仓位/止损/手续费/滑点)
│   │
│   ├── backtest/                     # ── 回测引擎层 ──
│   │   ├── data_feed.py
│   │   │   ├── DataCache             #   本地缓存管理
│   │   │   ├── get_a_stock()         #   A股 (新浪→东方财富双源)
│   │   │   ├── get_us_stock()        #   美股 (yfinance)
│   │   │   ├── get_hk_stock()        #   港股 (akshare)
│   │   │   ├── get_index_data()      #   指数 (沪深300等)
│   │   │   ├── get_data()            #   统一入口
│   │   │   ├── download_watchlist()  #   批量下载
│   │   │   ├── download_all_default()#   一键下载13个默认标的
│   │   │   └── get_data_summary()    #   缓存概览
│   │   │
│   │   ├── engine.py
│   │   │   ├── Portfolio             #   模拟账户 (现金/持仓/净值/交易记录)
│   │   │   │   ├── buy() / sell()    #   买卖 (含手续费)
│   │   │   │   └── mark_to_market()  #   每日估值
│   │   │   └── BacktestEngine        #   事件驱动引擎
│   │   │       └── run(strategy, data) → {portfolio, signals, metrics}
│   │   │
│   │   ├── metrics.py
│   │   │   └── calc_all_metrics()    #   夏普/最大回撤/胜率/盈亏比/卡尔玛/年化收益
│   │   │
│   │   ├── optimizer.py
│   │   │   ├── GridSearch            #   参数网格搜索
│   │   │   │   └── run(strategy, param_grid) → DataFrame 排名
│   │   │   ├── WalkForward           #   Walk-Forward 分析
│   │   │   │   └── run(strategy, param_grid, train_years, test_months)
│   │   │   ├── benchmark_compare()   #   基准对比 (沪深300 + 买入持有)
│   │   │   ├── quick_optimize()      #   一键优化
│   │   │   └── quick_walkforward()   #   一键Walk-Forward
│   │   │
│   │   └── batch_runner.py
│   │       ├── ResultDB              #   结果数据库
│   │       │   ├── save_result()     #   保存回测结果
│   │       │   ├── query()           #   多条件查询
│   │       │   ├── ranking()         #   排名
│   │       │   └── summary()         #   汇总统计
│   │       ├── BatchRunner           #   批量运行器
│   │       │   ├── add_symbols()     #   添加标的
│   │       │   ├── add_strategies()  #   添加策略
│   │       │   ├── run()             #   执行批量回测
│   │       │   └── show_ranking()    #   展示排名
│   │       ├── quick_batch()         #   一键批量
│   │       └── compare_strategies()  #   策略对比
│   │
│   ├── strategies/                   # ── 策略层 ──
│   │   ├── base.py
│   │   │   └── BaseStrategy          #   抽象基类
│   │   │       ├── sma/ema/rsi/macd/bollinger/atr
│   │   │       ├── cross_above() / cross_below()
│   │   │       └── on_bar() / buy_signal() / sell_signal() [抽象]
│   │   │
│   │   ├── library.py                #   经典策略库 (7个)
│   │   │   ├── MACrossStrategy       #   双均线交叉
│   │   │   ├── RSIStrategy           #   RSI超买超卖
│   │   │   ├── MACDStrategy          #   MACD金叉死叉
│   │   │   ├── BollingerStrategy     #   布林带
│   │   │   ├── TurtleStrategy        #   海龟交易 (ATR止损)
│   │   │   ├── MeanReversionStrategy #   均值回归
│   │   │   └── MomentumStrategy      #   动量突破
│   │   │
│   │   └── examples/ma_cross.py      #   旧版双均线 (保留兼容)
│   │
│   ├── factors/                      # ── 因子体系层 ──
│   │   ├── definitions.py
│   │   │   ├── Factor                #   因子元数据
│   │   │   ├── FactorCalculator      #   因子计算引擎
│   │   │   │   ├── 趋势类: ma_deviation, ma_alignment, ma_slope, trend_strength
│   │   │   │   ├── 动量类: rsi_norm, macd_hist, roc_10, price_position, momentum_score
│   │   │   │   ├── 波动类: volatility, bollinger_pos, bollinger_width, atr_ratio
│   │   │   │   ├── 成交量类: volume_ratio, volume_trend, obv_divergence
│   │   │   │   └── 形态类: hammer, engulfing
│   │   │   └── FACTOR_REGISTRY       #   18个因子注册表
│   │   │
│   │   └── composer.py
│   │       ├── Condition             #   触发条件 (factor + operator + threshold + weight)
│   │       ├── SignalRule            #   信号规则 (条件组合 + 逻辑 + 方向)
│   │       ├── SignalComposer        #   信号组合器
│   │       │   ├── 快捷API: rsi_oversold() / volume_surge() / hammer_pattern() ...
│   │       │   ├── add_condition()   #   添加条件
│   │       │   ├── set_logic()       #   逻辑: and / or / weighted
│   │       │   ├── evaluate()        #   评估 → 返回 Signal
│   │       │   └── to_strategy()     #   转为回测引擎可用的策略对象
│   │       └── PRESET_STRATEGIES     #   4个预设独有策略
│   │           ├── contrarian_v1        逆势交易V1
│   │           ├── trend_following_v1   趋势跟踪V1
│   │           ├── volume_breakout_v1   量价突破V1
│   │           └── mean_reversion_v2    均值回归V2
│   │
│   ├── analysis/                     # ── 分析层 ──
│   │   ├── charts.py
│   │   │   ├── equity_curve()        #   资金曲线 + 回撤 (双面板)
│   │   │   ├── monthly_returns_heatmap() # 月度热力图
│   │   │   ├── pnl_distribution()    #   盈亏分布直方图
│   │   │   ├── portfolio_charts()    #   一键生成全套图表
│   │   │   └── plot_from_backtest()  #   从回测结果生成图表
│   │   │
│   │   └── reports.py
│   │       └── ReportGenerator       #   文本分析报表
│   │           ├── overview()        #   整体概览
│   │           ├── by_market()       #   按市场分组
│   │           ├── by_strategy()     #   按策略分组
│   │           ├── by_tags()         #   按标签分组
│   │           ├── by_month()        #   按月汇总
│   │           └── print_all()       #   打印完整报告
│   │
│   └── journal/                      # ── 交易日志层 ──
│       └── cli.py
│           └── JournalCLI            #   交互式命令行
│               ├── _record_buy()     #   记录买入
│               ├── _record_sell()    #   记录卖出 (自动配对)
│               ├── _view_history()   #   查看历史 (多条件筛选)
│               ├── _view_positions() #   当前持仓
│               ├── _add_review()     #   写复盘笔记 + 评分
│               ├── _pnl_summary()    #   盈亏汇总
│               ├── _export_csv()     #   导出CSV
│               └── _import_csv()     #   导入CSV
```

## 3. 数据流

```
                     ┌──────────────┐
                     │   数据源      │
                     │ 新浪/东方财富  │
                     │ yfinance     │
                     └──────┬───────┘
                            │ raw data
                            ▼
                     ┌──────────────┐
                     │  DataCache   │
                     │  本地CSV缓存   │
                     └──────┬───────┘
                            │ OHLCV DataFrame
                            ▼
              ┌─────────────────────────┐
              │    策略 / 因子评估        │
              │                          │
              │  ┌───────────────────┐   │
              │  │ FactorCalculator  │   │
              │  │ 计算18个因子       │   │
              │  └────────┬──────────┘   │
              │           │ 因子值        │
              │           ▼              │
              │  ┌───────────────────┐   │
              │  │ SignalComposer    │   │
              │  │ 条件组合 → 信号    │   │
              │  └────────┬──────────┘   │
              │           │ Signal       │
              │           ▼              │
              │  ┌───────────────────┐   │
              │  │ BacktestEngine    │   │
              │  │ 模拟交易 + 估值    │   │
              │  └────────┬──────────┘   │
              │           │ results      │
              └───────────┼──────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │     输出管道             │
              │                         │
              │  ┌──────────┐ ┌───────┐ │
              │  │ metrics  │ │charts │ │
              │  │ 绩效指标  │ │ 图表   │ │
              │  └──────────┘ └───────┘ │
              │  ┌──────────┐ ┌───────┐ │
              │  │ ResultDB │ │Report │ │
              │  │ 结果数据库 │ │ 报表  │ │
              │  └──────────┘ └───────┘ │
              └─────────────────────────┘
```

## 4. 核心类关系图

```
BaseStrategy (抽象)
    ├── MACrossStrategy
    ├── RSIStrategy
    ├── MACDStrategy
    ├── BollingerStrategy
    ├── TurtleStrategy
    ├── MeanReversionStrategy
    └── MomentumStrategy

SignalComposer.to_strategy()
    └── ComposedStrategy (动态生成，兼容 BacktestEngine)

BacktestEngine.run(strategy, data)
    ├── 输入: BaseStrategy + OHLCV DataFrame
    ├── 内部: Portfolio (模拟账户)
    └── 输出: {portfolio, signals, metrics}

GridSearch.run(strategy_name, param_grid)
    └── 内部循环: BacktestEngine.run() × N次
    └── 输出: DataFrame (按指标排名)

BatchRunner.run()
    └── 内部: GridSearch × (symbols × strategies)
    └── 输出: DataFrame + SQLite持久化

WalkForward.run(strategy_name, param_grid)
    └── 内部: GridSearch(训练期) → BacktestEngine(测试期) × N窗口
    └── 输出: {windows, summary, metrics}
```

## 5. 数据存储

| 存储 | 位置 | 格式 | 内容 |
|------|------|------|------|
| 交易日志 | `D:\trading_data\trades.db` | SQLite | 买卖记录、复盘笔记、配对盈亏 |
| 回测结果 | `D:\trading_data\backtest_results.db` | SQLite | 每次回测的绩效指标、参数、排名 |
| 行情缓存 | `D:\trading_data\cache\*.csv` | CSV | 各标的日线OHLCV数据 |
| 因子导出 | `D:\trading_data\factors_*.csv` | CSV | 全因子计算结果 |
| 图表输出 | `D:\trading_data\charts\*\*.html` | HTML | Plotly 交互图表 |
| 日志文件 | `D:\trading_data\logs\quant_*.log` | TXT | 结构化运行日志 |
| 诊断报告 | `D:\trading_data\reports\*.txt` | TXT | 每日诊断快报 (新增) |

## 6. 已注册策略清单

### 经典策略 (7)

| 键 | 名称 | 描述 |
|----|------|------|
| `ma_cross` | 双均线交叉 | 短期均线上穿长期均线买入，下穿卖出 |
| `rsi` | RSI超买超卖 | RSI低于超卖线买入，高于超买线卖出 |
| `macd` | MACD金叉死叉 | DIF上穿DEA买入，下穿卖出 |
| `bollinger` | 布林带 | 触及下轨反弹买入，触及中轨卖出 |
| `turtle` | 海龟交易 | 突破N日高点买入，跌破M日低点卖出，ATR止损 |
| `mean_reversion` | 均值回归 | 远离均线逆势入场，回归均线离场 |
| `momentum` | 动量突破 | 突破N日高点买入，配合成交量+趋势过滤 |

### 独有策略模板 (4)

| 键 | 名称 | 逻辑 |
|----|------|------|
| `contrarian_v1` | 逆势交易V1 | RSI超卖(权重3) + 布林下轨(权重2) + 放量(权重1) → 总分≥4买入 |
| `trend_following_v1` | 趋势跟踪V1 | 均线金叉(权重3) + 强趋势(权重2) + 动量(权重1) → 总分≥4买入 |
| `volume_breakout_v1` | 量价突破V1 | 放量2倍(权重3) + 动量强(权重2) + 趋势强(权重1) → 总分≥4买入 |
| `mean_reversion_v2` | 均值回归V2 | 偏离均线(权重2) + 低波动(权重1) + 锤子线(权重2) → 总分≥3买入 |

## 7. 已注册因子清单 (18)

### 趋势类 (4)
| 因子 | 说明 | 输出范围 |
|------|------|----------|
| `ma_deviation` | 价格偏离20日均线程度 | 0~1 (0.5=均线) |
| `ma_alignment` | 多空排列 (短>中>长=1) | 0~1 |
| `ma_slope` | 均线斜率 | 0~1 |
| `trend_strength` | 趋势强度 (类ADX) | 0~1 |

### 动量类 (5)
| 因子 | 说明 | 输出范围 |
|------|------|----------|
| `rsi_norm` | RSI标准化 | 0~1 (0=超卖, 1=超买) |
| `macd_hist` | MACD动能柱 | 0~1 |
| `roc_10` | 10日变化率 | 0~1 |
| `price_position` | 60日高低区间位置 | 0~1 |
| `momentum_score` | 多周期动量综合 | 0~1 |

### 波动类 (4)
| 因子 | 说明 | 输出范围 |
|------|------|----------|
| `volatility` | 历史波动率 (低波=高分) | 0~1 |
| `bollinger_pos` | 布林带位置 | 0~1 (1=上轨) |
| `bollinger_width` | 布林带宽度 | 正值 |
| `atr_ratio` | ATR/价格比 | 正值 |

### 成交量类 (3)
| 因子 | 说明 | 输出范围 |
|------|------|----------|
| `volume_ratio` | 短/长期量比 | 0~1 |
| `volume_trend` | 量价配合健康度 | 0~1 |
| `obv_divergence` | OBV与价格背离 | 0~1 |

### 形态类 (2)
| 因子 | 说明 | 输出范围 |
|------|------|----------|
| `hammer` | 锤子线检测 | 0~1 |
| `engulfing` | 吞没形态检测 | 0~1 |

## 8. 信号组合逻辑

```
买入规则 = 条件1 AND/OR/WEIGHTED 条件2 AND/OR/WEIGHTED 条件3 ...
卖出规则 = 同上

逻辑模式:
  "and"      → 所有条件都满足才触发
  "or"       → 任一条件满足就触发
  "weighted" → 加权总分 >= threshold 才触发
                (每个条件有 weight 权重)
```

## 9. 使用示例

```python
# ===== 场景1: 快速批量回测 =====
from src.backtest.batch_runner import quick_batch
df = quick_batch(
    symbols=["601398", "000858", "600036"],
    strategies=["ma_cross", "rsi", "contrarian_v1"],
)
# → 9次回测，结果自动保存到数据库

# ===== 场景2: 创建自己的策略 =====
from src.factors.composer import SignalComposer

my = (SignalComposer("我的独门策略")
    .rsi_oversold(14, 30, weight=3)        # RSI<30，权重3
    .volume_surge(1.5, weight=2)            # 放量1.5倍，权重2
    .set_logic("weighted", threshold=4.0)   # 总分≥4触发买入
    .rsi_overbought(14, 70, weight=2)       # RSI>70，权重2
    .set_logic("or", threshold=0, action="SELL"))  # 满足即卖

# 转为策略对象，直接传入回测引擎
strategy = my.to_strategy()
engine.run(strategy, data)

# ===== 场景3: 网格搜索最优参数 =====
from src.backtest.optimizer import GridSearch
gs = GridSearch("601398", "A股", start_date="2022-01-01")
df = gs.run("ma_cross", {
    "fast_period": [5, 10, 20, 30],
    "slow_period": [20, 30, 40, 60],
    "vol_confirm": [True, False],
})
# → 4×4×2=32种组合，按夏普排名

# ===== 场景4: 导出因子数据 =====
from src.backtest.data_feed import get_data
from src.factors.definitions import FactorCalculator

data = get_data("601398", "A股", start_date="2024-01-01")
calc = FactorCalculator(data)
factors = calc.compute_all()
factors.to_csv("D:/trading_data/factors_601398.csv")
# → 18个因子的完整时序数据
```

## 10. 新增功能 (v0.4)

### 🔍 快速验证 (`V`)

选股票 → 设时间 → 选策略 → 一键回测。适合快速验证交易想法。

```
主菜单 V → 输入股票代码 → 输入时间区间 → 从11个策略中选一个 → 自动回测出结果
```

相关函数：`_quick_validate()`, `_pick_strategy()`, `_print_backtest_metrics()`

### 🩺 个股诊断 (`D`)

对单只股票做全面体检，包含 5 部分报告：

| 部分 | 内容 | 回答的问题 |
|------|------|-----------|
| 历史策略表现 | 11个策略全部回测排名 | 什么策略有效？ |
| 投资者适配 | 4种画像（保守/稳健/进取/逆向）匹配评分 | 什么类型的人适合？ |
| 入场时机 | 8个因子加权评分 (0-100) | 现在是不是好时机？ |
| 仓位建议 | ATR止损 + 波动调整 + 风险偏好 | 仓位多少？ |
| 行动计划 | 具体买入价、止损价、股数、金额 | 怎么操作？ |

- 自动检查数据新鲜度，非今日数据自动拉取最新行情
- 报告头部显示 `🟢 今日` 或 `⚠️ 仅到 YYYY-MM-DD`

相关函数：`_stock_diagnosis()`, `_run_all_strategies_on_stock()`, `_match_investor_profiles()`, `_analyze_entry_timing()`, `_calculate_position_sizing()`, `_print_diagnosis_report()`

### 🔄 每日快扫 (`R`)

一键扫描默认13只股票，刷新行情数据，计算因子评分，输出信号排名。

- 快速模式：仅因子评分 (0-100) + 信号汇总
- 完整模式：含全策略回测

### 📡 每日自动诊断 (daily_runner.py)

独立脚本，支持 Windows 定时任务。

```bash
python daily_runner.py                        # 扫描13只默认股票
python daily_runner.py 000858 601398          # 指定股票
python daily_runner.py --full                 # 完整诊断模式
```

- 输出报告到控制台 + 保存 `D:/trading_data/reports/daily_scan_*.txt`
- Windows 定时任务：每天 15:30 自动运行

### 投资者画像

| 画像 | 风险 | 回撤容忍 | 偏好策略 | 推荐仓位 |
|------|------|----------|----------|----------|
| 🛡️ 保守型 | 低 | <5% | 均值回归、布林带 | 10-20% |
| ⚖️ 稳健型 | 中 | <15% | 均线交叉、MACD、RSI | 20-30% |
| 🚀 进取型 | 高 | <30% | 动量突破、海龟交易 | 30-50% |
| 🔄 逆向型 | 中高 | <15% | 逆势V1、均值回归V2 | 15-25% |

### 入场评分算法

```python
基准分 50 + 加权因子信号:
  RSI超卖(rsi_norm<0.3)   +20     RSI超买(rsi_norm>0.7)   -20
  布林下轨(bb<0.2)        +20     布林上轨(bb>0.8)        -20
  均线多头(ma>0.7)        +15     均线空头(ma<0.3)        -10
  MACD向上(macd_h>0.55)   +15     MACD向下(macd_h<0.45)   -10
  放量(vol>0.7)           +10     缩量(vol<0.3)            -5
  锤子线/吞没             +10     趋势不明                  -3
  动量强劲                +10
→ 80+:🟢强烈买入 60+:🟡谨慎 40+:⚪观望 <40:🔴回避
```

---

## 11. 扩展指南

### 添加新策略
```python
# 在 src/strategies/library.py 中添加
class MyStrategy(BaseStrategy):
    def on_bar(self, i, data, portfolio):
        # 你的逻辑
        ...
    def buy_signal(self, data): ...
    def sell_signal(self, data): ...

# 注册到 STRATEGIES 字典
STRATEGIES["my_strategy"] = {...}
```

### 添加新因子
```python
# 在 src/factors/definitions.py 的 FactorCalculator 中添加
def f_my_factor(self, param=10):
    # 你的计算逻辑
    return result

# 注册到 FACTOR_REGISTRY
FACTOR_REGISTRY["my_factor"] = Factor(...)
```

### 添加新数据源
```python
# 在 src/backtest/data_feed.py 中添加
def get_xxx_data(symbol, start_date, end_date):
    # 你的数据获取逻辑
    ...
    return df  # 标准 OHLCV DataFrame

# 在 get_data() 中添加分支
```
