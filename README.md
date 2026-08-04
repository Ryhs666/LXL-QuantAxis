# LXL·QuantAxis v2.0

> 个人量化交易平台 — 28因子 · 16策略 · A股/港股/美股 · AI驱动 · Alpha记忆闭环

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-315%20passed-brightgreen.svg)](.)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0--alpha.1-orange.svg)](.)

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 (三选一)
python web_modern.py    # Web 平台 → http://127.0.0.1:5000  (推荐)
python main.py          # CLI 菜单
python src/app.py       # 桌面应用 (Tkinter)
```

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                  Web / CLI / Desktop                     │
├─────────────────────────────────────────────────────────┤
│  Alpha Memory   │  Backtest    │  Realtime   │  Paper   │
│  Signal Lifecycle│  T+1 Engine  │  Collector  │  Broker  │
├─────────────────────────────────────────────────────────┤
│  16 Strategies  │  28 Factors  │  Risk Gate  │  Alerts  │
├─────────────────────────────────────────────────────────┤
│  AI: LLM Chat · Genetic Miner · Strategy Evolver        │
├─────────────────────────────────────────────────────────┤
│  Data: akshare · yfinance · SQLite ×10 · CSV Cache      │
└─────────────────────────────────────────────────────────┘
```

## 核心特性

### 交易与回测
- **无前视偏差回测**: T+1 成交 · 涨跌停检查 · 冲击成本 · 限价单模拟
- **A股真实成本**: 佣金(最低5元) · 印花税(0.05%卖出) · 过户费(沪市)
- **基准指标**: Alpha · Beta · IR · Tracking Error · 可配置无风险利率
- **参数优化**: Optuna 贝叶斯优化 + 网格搜索 + Walk-Forward

### Alpha Memory 闭环
- **信号记忆**: 每条信号完整生命周期 → 因子胜率 · 状态矩阵 · IC衰减线
- **自动降权**: IC 连续 5 天为负 → 自动禁用衰减因子
- **因子持久化**: AI 挖掘因子重启后自动恢复
- **策略银行**: 进化银行 + 用户银行统一接口

### AI 智能体
- **策略工厂**: AI分析 → 种子策略 → 遗传进化 → 跨股票复测 → 入银行
- **自然语言策略**: 描述思路 → AI 解析 → 自动构建因子策略 → 回测
- **因子挖掘**: 遗传编程自动发现高 IC 因子表达式
- **AI 助手**: 复盘 · 市场简报 · 策略顾问

### 实时行情
- HTTP 轮询腾讯财经 · Flask-SocketIO WebSocket 推送
- K线聚合 (1/5/15min) · 策略信号实时评估
- **告警引擎**: 价格突破/成交量异动/回撤告警 → 钉钉/邮件/微信/Telegram

### 风控体系
- **闸门**: 6 道规则 (总仓位·单票集中·回撤止损·日内亏损·现金·黑名单)
- **风控器**: 移动止损 · 回撤熔断 · 凯利仓位 · 风险平价 · Black-Litterman
- **速率限制**: 敏感 API 自动限频 (HTTP 429)

### 数据层
- A股/港股/美股 OHLCV · 宏观指标 (CPI/PPI/PMI/LPR/Fed) · 三张报表
- PE/PB/ROE 历史序列 · 申万行业分类 · 统一数据仓库 (CSV/SQLite/Parquet)

## Web 界面

| 页面 | 路由 | 功能 |
|------|------|------|
| **v2.0 仪表盘** | `/` `/v2` | K线蜡烛图 · Alpha信号 · Broker · 宏观 · 策略银行 |
| **经典面板** | `/classic` | 全功能: 回测 · AI · 策略 · 因子 · 诊断 · 快扫 |
| **交易工作室** | `/studio` | K线图表 + 实时信号推送 |
| **模拟交易** | `/game` | 100万模拟金 · T+1买卖 · 排行榜 |
| **管理后台** | `/admin` | 用户管理 · 系统状态 |

## CLI 命令

```bash
python main.py                          # 交互菜单
python main.py --tune ma_cross          # 策略参数优化
python main.py --allocate               # 策略权重分配
python main.py --discover 600519        # AI 因子发现
python main.py --report                 # 生成每日简报
```

## 策略库 (16个)

| 类型 | 策略 |
|------|------|
| 经典 (7) | 双均线 · RSI · MACD · 布林带 · 海龟 · 均值回归 · 动量突破 |
| 高级 (5) | 自适应复合 · 趋势做空 · 双向交易 · 状态感知 · 集成投票 |
| 因子 (4) | 逆势V1 · 趋势跟踪V1 · 量价突破V1 · 均值回归V2 |

## 因子体系 (28个)

| 类别 | 数量 | 示例 |
|------|------|------|
| 趋势 | 4 | ma_deviation, ma_alignment, ma_slope, trend_strength |
| 动量 | 5 | rsi_norm, macd_hist, roc_10, price_position, momentum_score |
| 波动 | 4 | volatility, bollinger_pos, bollinger_width, atr_ratio |
| 成交量 | 4 | volume_ratio, volume_trend, obv_divergence, vol_exhaustion |
| 形态 | 2 | hammer, engulfing |
| 情绪 | 3 | sentiment_score, sentiment_heat, sentiment_extreme |
| 基本面 | 6 | pe_percentile, pb_percentile, roe_trend, revenue_acceleration, ... |

## 项目结构

```
LXL-QuantAxis/
├── main.py                  # CLI 主菜单 + --tune/--allocate/--discover
├── web_modern.py            # Web 平台 (Flask-SocketIO, 50+ API, 实时推送)
├── daily_runner.py          # 每日自动扫描
├── CHANGELOG.md             # 变更日志
├── ARCHITECTURE.md          # 详细架构文档 (必读)
├── config/
│   └── alerts.yaml          # 告警规则配置
├── src/
│   ├── version.py           # 版本统一
│   ├── config.py            # 配置管理 (YAML + ENV)
│   ├── app.py               # 桌面应用 (Tkinter, 侧边栏)
│   ├── dialogs.py           # 对话框 (快速验证/诊断/因子策略)
│   ├── models/              # Trade, Signal, StrategyConfig
│   ├── backtest/            # 引擎 · 数据源 · 指标 · 优化器 · 宏观 · 因子验证
│   ├── strategies/          # 16 策略 (经典+高级+集成+自适应)
│   ├── factors/             # 28 因子 · 信号组合器 · 基本面 · 量能耗尽
│   ├── portfolio/           # 组合收益/风险指标 · 用户持仓 · 策略优化器
│   ├── ai/                  # Alpha记忆 · 因子持久化 · 策略银行 · 进化工厂 · 情绪 · 因子发现
│   ├── data/                # 统一仓库 · 财务报表 · 宏观数据 · 行业分类
│   ├── execution/           # 执行引擎 · Paper Broker · 实时桥接 · 券商适配器
│   ├── analysis/            # 图表 · 报表 · 归因分析 · 因子相关性 · 市场状态
│   ├── dashboard/           # 6 面板: 总览/绩效/数据/基本面/宏观/Alpha
│   ├── realtime/            # 行情采集 · 策略引擎 · K线聚合 · 告警引擎
│   ├── risk/                # 闸门 · 止损/熔断/凯利/风险平价
│   ├── journal/             # CLI日志 · 复现清单生成
│   ├── utils/               # 信号延迟 · 限频器 · 策略调优器
│   ├── report/              # 每日报告
│   ├── auth/                # JWT 认证
│   └── database/            # SQLAlchemy ORM
└── tests/                   # 315 tests, 73 subtests, ~1s
```

## AI 配置

在 `D:/trading_data/ai_config.json` 中配置:

```json
{
  "api_key": "your-api-key",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat"
}
```

支持 DeepSeek / OpenAI / Qwen 及所有 OpenAI 兼容接口。

## 测试

```bash
python -m pytest tests/ -q
# 315 passed, 73 subtests in ~1.0s
```

## 数据

首次使用自动下载A股全市场列表和行情数据。

环境变量:
- `QUANT_DATA_DIR` — 数据根目录 (默认 `D:/trading_data`)
- `QUANT_BROKER` — 券商类型 `paper`/`qmt`
- `QUANT_MONITOR` — 开启停滞监控 (`true`)
- `AI_API_KEY` / `AI_BASE_URL` / `AI_MODEL` — AI 配置

## License

MIT © Ryhs666
