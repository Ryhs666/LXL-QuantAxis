# LXL·QuantAxis

个人量化交易平台 — A股/港股/美股 · AI辅助 · 回测 + 模拟交易

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-349%20passed-brightgreen)](.)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 快速开始

```bash
pip install -r requirements.txt

python web_modern.py     # Web 平台 → http://127.0.0.1:5000
python main.py           # CLI 菜单
python src/app.py        # 桌面应用 (Tkinter)
```

## 安全启动

本地开发默认监听 `127.0.0.1`，JWT 使用进程级随机密钥。生产环境必须配置：

```powershell
$env:LXL_ENV = "production"
$env:JWT_SECRET_KEY = "至少32位的随机密钥"
$env:ADMIN_PASSWORD = "首次启动使用的至少12位强密码"
python web_modern.py
```

## 功能

| 模块 | 功能 |
|------|------|
| 回测引擎 | T+1 成交 · 事件驱动 · A 股手续费 · 滑点 · 涨跌停 |
| 策略库 | 双均线/RSI/MACD/布林带/海龟/均值回归/动量 + 自适应/做空/双向/状态感知 |
| 因子体系 | 趋势/动量/波动/成交量/形态 + 情绪 + 基本面 |
| AI 助手 | LLM 对话 · 策略工厂 · 复盘 · 市场简报 (DeepSeek/OpenAI/Qwen) |
| 实时行情 | 腾讯财经 HTTP 轮询 · SocketIO WebSocket · K 线聚合 |
| 模拟交易 | 100 万模拟金 · T+1 · 排行榜 |
| 风控 | 移动止损 · 回撤熔断 · 凯利仓位 · 下单前闸门 |
| 仪表盘 | v2.0 仪表盘 + 经典面板 + 交易工作室 + 管理后台 |
| 组合分析 | 显式 simple/log 收益语义 · periodic/buy-and-hold 再平衡 · Sharpe/Calmar/MaxDD |

## 组合指标语义

- **SIMPLE**: `r = p_t/p_{t-1} - 1`, 累计 `prod(1+r) - 1`
- **LOG**: `r = ln(p_t/p_{t-1})`, 累计 `exp(sum(r)) - 1`
- **PERIODIC**: 每期恢复目标权重
- **BUY_AND_HOLD**: 权重随价格漂移
- 零波动率时 Sharpe 返回 `None`，不返回误导性 inf
- bool 类型参数明确拒绝，不隐式转换
- 重复/乱序日期明确报错

## 数据

数据默认存储在 `~/.lxl_quantaxis/`。通过 `QUANT_DATA_DIR` 修改。

## 测试

```bash
python -m pytest tests/ -q
# 349 passed, 119 subtests
```

## AI 配置

`D:/trading_data/ai_config.json`:
```json
{"api_key": "sk-xxx", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"}
```

## 安全说明

- AI 因子生成使用白名单算子，不执行任何 AI 输出的代码
- Paper Broker 为模拟交易，未接入真实券商
- 自动交易需显式开启，默认仅记录信号
- 组合优化器使用 walk-forward 样本外评估
- 生产环境强制 JWT + 强密码

## License

MIT
