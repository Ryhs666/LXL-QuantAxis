# LXL·QuantAxis v2.0.0-alpha.1

个人量化交易平台 — 28因子 · 16策略 · A股/港股/美股 · AI驱动 · Alpha记忆闭环

## 快速开始

```bash
pip install -r requirements.txt
python main.py          # CLI 菜单
python src/app.py       # 桌面应用 (tkinter)
python web_modern.py    # Web 平台 (Flask-SocketIO, http://127.0.0.1:5000)
```

## 核心特性

| 模块 | 功能 |
|------|------|
| **Alpha Memory 闭环** | 信号记忆 → IC衰减自动降权 → 因子持久化 → 策略银行统一 → 进化后自动复测 |
| **回测引擎** | T+1 无前视偏差成交 · A股真实成本(印花税+过户费+最低佣金) · 涨跌停检查 · 冲击成本 |
| **基准指标** | Alpha / Beta / IR / Tracking Error · 可配置无风险利率 |
| **AI 策略工厂** | AI分析回测 → 生成种子策略 → 遗传算法进化 → 跨股票复测 → 入银行 |
| **AI 自然语言策略** | 描述交易思路 → AI 解析 → 自动构建因子策略 → 回测 |
| **实时行情** | 腾讯财经 HTTP 轮询 · Flask-SocketIO WebSocket 推送 · K线聚合(1/5/15min) |
| **Paper Broker** | 统一纸面券商 · 订单持久化 · 会话恢复 · 实时信号自动交易桥接 |
| **专业仪表盘** | 系统总览/绩效热力图/数据健康/基本面/宏观/Alpha记忆 6 个面板 |
| **基本面数据** | PE/PB/ROE 历史序列 · 三张报表(资产/利润/现金流) · 申万行业分类 |
| **宏观数据** | CPI/PPI/PMI/LPR · 美联储利率/失业率/10Y国债 · 8 指标真实 akshare 连接 |
| **风控系统** | 移动止损 · 回撤熔断 · 凯利仓位 · 风险平价 · Black-Litterman |

## 策略库 (16 个)

### 经典策略 (7)
双均线交叉 · RSI超买超卖 · MACD金叉死叉 · 布林带 · 海龟交易 · 均值回归 · 动量突破

### 高级策略 (5)
自适应复合 · 趋势做空 · 双向交易 · 状态感知 · 策略集成投票

### 独有因子策略 (4)
逆势交易V1 · 趋势跟踪V1 · 量价突破V1 · 均值回归V2

## 因子体系 (28 个)

| 类别 | 数量 | 因子 |
|------|------|------|
| 趋势 | 4 | ma_deviation, ma_alignment, ma_slope, trend_strength |
| 动量 | 5 | rsi_norm, macd_hist, roc_10, price_position, momentum_score |
| 波动 | 4 | volatility, bollinger_pos, bollinger_width, atr_ratio |
| 成交量 | 4 | volume_ratio, volume_trend, obv_divergence, **vol_exhaustion** |
| 形态 | 2 | hammer, engulfing |
| 情绪 | 3 | sentiment_score, sentiment_heat, sentiment_extreme |
| 基本面 | 6 | pe_percentile, pb_percentile, roe_trend, profit_margin_change, revenue_acceleration, industry_relative_pe |

## 数据存储

| 数据库 | 内容 |
|--------|------|
| `alpha_memory.db` | Alpha 信号完整生命周期记忆 |
| `backtest_results.db` | 批量回测结果 (54+ 条) |
| `trades.db` | 交易日志与盈亏 |
| `financial_series.db` | PE/PB/ROE 历史序列 |
| `orders.db` | Paper Broker 订单持久化 |
| `strategy_bank.db` | 用户策略银行 |
| `strategy_bank/bank.json` | AI 进化策略银行 |
| `mined_factors/` | AI 挖掘因子持久化 |
| `users.db` | 多用户认证与配置 |
| `stock_names.db` | A股/港股 股票名称库 |

## AI 配置

```json
{
  "api_key": "你的密钥",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat"
}
```

支持 DeepSeek / OpenAI / Qwen 及所有 OpenAI 兼容接口。

## 项目结构

```
PythonProject1/
├── main.py                  # CLI 主菜单
├── web_modern.py            # Web 平台 (Flask-SocketIO, 实时推送)
├── web_app.py               # Web 平台 (Flask)
├── daily_runner.py          # 每日自动扫描
├── CHANGELOG.md             # 变更日志
├── ARCHITECTURE.md          # 详细架构文档
├── src/
│   ├── version.py           # 版本统一 (v2.0.0-alpha.1)
│   ├── config.py            # 配置管理
│   ├── app.py               # 桌面应用 (tkinter)
│   ├── dialogs.py           # 对话框
│   ├── models/              # Trade, Signal, StrategyConfig
│   ├── backtest/            # 引擎 · 数据源 · 指标 · 优化器 · 宏观 · 因子验证
│   ├── strategies/          # 16 策略 (经典+高级+集成+自适应)
│   ├── factors/             # 28 因子 · 信号组合器 · 基本面 · IC衰减
│   ├── portfolio/           # 组合收益/风险指标 · 用户持仓管理
│   ├── ai/                  # Alpha记忆 · 因子持久化 · 策略银行 · 进化工厂 · 情绪分析
│   ├── data/                # 财务报表 · 宏观数据 · 行业分类 · 行情DB
│   ├── execution/           # 执行引擎 · Paper Broker · 实时桥接
│   ├── analysis/            # 图表 · 报表 · 市场状态检测
│   ├── index/               # 指数估值 · 轮动策略
│   ├── dashboard/           # 6 面板: 总览/绩效/数据/基本面/宏观/Alpha
│   ├── realtime/            # 行情采集 · 策略引擎 · K线聚合
│   ├── risk/                # 止损/熔断/凯利/风险平价/Black-Litterman
│   ├── report/              # 每日报告生成
│   ├── auth/                # JWT 认证
│   └── database/            # SQLAlchemy ORM
└── tests/                   # 315 tests, 73 subtests
```

## 测试

```bash
python -m pytest tests/ -q    # 315 passed, 73 subtests, ~1s
```

## 数据

首次使用自动下载 A 股全市场列表和行情数据。通过环境变量 `QUANT_DATA_DIR` 修改数据目录。

## License

MIT
