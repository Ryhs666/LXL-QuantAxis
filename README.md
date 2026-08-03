# LXL·QuantAxis v5.0

个人量化交易平台 — 15策略 · 18因子 · 5500+ A股 · AI驱动

## V2.0 架构升级状态

V2.0 已进入“审计基线与架构决策”阶段。本阶段仅固化现状、风险和迁移原则，不改变现有运行行为。

- [当前架构审计](docs/audit/current-architecture-review.md)
- [ADR-0001：采用模块化单体](docs/adr/0001-modular-monolith.md)
- [ADR-0002：分离研究面与交易面](docs/adr/0002-research-trading-separation.md)
- [ADR-0003：采用 Point-in-Time 数据语义](docs/adr/0003-point-in-time-data.md)

## 快速开始

```bash
pip install -r requirements.txt
python main.py          # CLI 菜单
python src/app.py       # 桌面应用 (tkinter)
python web_modern.py    # Web 平台 (Flask, http://127.0.0.1:5000)
```

## 功能

| 模块 | 功能 |
|------|------|
| 快速验证 | 选股票 → 选策略 → 回测 |
| 个股诊断 | 15策略排名 + 18因子 + 入场评分 |
| 智能推荐 | 最优策略 + 买入价 + 卖出价 + 止损价 + AI讨论 |
| AI策略战法 | 自然语言描述思路 → AI自动构建策略 → 回测 |
| 因子策略构建器 | 18因子自选配权重 → 自定义策略 |
| 每日快扫 | 13只默认标的信号排名 |
| AI复盘/对话/简报 | DeepSeek/OpenAI 兼容 |

## 策略库 (15个)

7个经典: 双均线交叉、RSI、MACD、布林带、海龟交易、均值回归、动量突破

4个因子: 逆势交易V1、趋势跟踪V1、量价突破V1、均值回归V2

4个高级: 自适应复合、趋势做空、双向交易、状态感知

## 因子体系 (18个)

趋势(4): ma_deviation, ma_alignment, ma_slope, trend_strength

动量(5): rsi_norm, macd_hist, roc_10, price_position, momentum_score

波动(4): volatility, bollinger_pos, bollinger_width, atr_ratio

成交量(3): volume_ratio, volume_trend, obv_divergence

形态(2): hammer, engulfing

## AI 配置

在桌面应用左侧 `AI智能体 → 配置AI` 中设置:

- API Key: 你的密钥
- Base URL: `https://api.deepseek.com` (或其他OpenAI兼容接口)
- Model: `deepseek-chat`

## 安全启动配置

本地开发默认只监听 `127.0.0.1`，JWT 使用进程级随机密钥，重启后旧登录令牌失效。
首次创建管理员时必须显式设置强密码，系统不会再创建默认密码或在日志中打印密码。

生产环境启动前必须配置：

```powershell
$env:LXL_ENV = "production"
$env:JWT_SECRET_KEY = "至少32位的随机密钥"
$env:ADMIN_PASSWORD = "首次启动使用的至少12位强密码"
python web_modern.py
```

管理员创建后可移除 `ADMIN_PASSWORD`。生产环境默认关闭自主注册；如确需开放，显式设置
`LXL_REGISTRATION_ENABLED=true`。对外监听也必须显式设置 `LXL_BIND_HOST`，默认仍为
`127.0.0.1`。

## 数据

首次使用会自动下载A股全市场股票列表和行情数据。

数据默认存储在 `~/.lxl_quantaxis/`。

可以通过环境变量 `QUANT_DATA_DIR` 修改数据目录。旧环境变量
`TRADING_DATA_DIR` 仍然兼容，但不再推荐使用。

## 项目结构

```
PythonProject1/
├── main.py              # CLI主菜单
├── web_modern.py        # Web平台 (Flask)
├── daily_runner.py      # 每日自动扫描脚本
├── USER_GUIDE.md        # 使用手册
├── src/
│   ├── app.py           # 桌面应用 (tkinter)
│   ├── dialogs.py       # 对话框模块
│   ├── config.py        # 配置管理
│   ├── models/          # 数据模型 (交易/策略)
│   ├── backtest/        # 回测引擎 + 数据源 + 优化器
│   ├── strategies/      # 策略库 (15个)
│   ├── factors/         # 因子体系 (18个)
│   ├── analysis/        # 图表 + 报表
│   ├── journal/         # 交易日志
│   ├── ai/              # AI助手 (引擎+复盘+工厂)
│   ├── index/           # 指数估值 + 轮动
│   └── dashboard/       # 可视化仪表盘
└── ARCHITECTURE.md      # 架构文档
```

## License

MIT
