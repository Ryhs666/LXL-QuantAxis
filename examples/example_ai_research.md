# LXL·QuantAxis V2.0 — AI Research Demo

## Input

**Investment Idea**: 看好AI服务器产业链。云厂商资本开支提升利好算力需求。风险：估值过高。

**Symbol**: 000001 (for demo backtest)

## Pipeline Output

### 1. AI Thesis Extraction

```
Title: AI服务器产业链看多
Thesis: 云厂商资本开支提升驱动算力需求增长
Bull: CAPEX扩张 + 订单增长
Bear: 估值过高 + 竞争加剧
Risk: 政策变化 + 技术迭代
Conviction: High
```

### 2. Factor Model

| Factor | Weight | Category | Reason |
|--------|--------|----------|--------|
| momentum_score | 0.30 | momentum | Growth momentum |
| trend_strength | 0.25 | trend | CAPEX trend confirmation |
| roc_10 | 0.25 | momentum | Short-term price strength |
| volume_trend | 0.20 | volume | Volume confirming trend |

### 3. Strategy DSL

```
Name: AI_server_growth_strategy
Entry: momentum_score > 0.6 AND trend_strength > 0.5
Exit: max_drawdown > 0.10
Risk: max_drawdown_pct=10%, stop_loss_pct=5%
```

### 4. Backtest Results

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 1.25 |
| Total Return | +18.5% |
| Win Rate | 58% |
| Max Drawdown | -12% |
| Trades | 24 |

### 5. AI Analysis

```
Summary: Viable strategy with moderate Sharpe and acceptable drawdown.
Strengths: Positive risk-adjusted returns, sufficient sample size
Weaknesses: Moderate win rate, could improve entry timing
Risk: Drawdown within 15% limit but worth monitoring
Suggestions: Add market regime filter, tighten stop loss
```

### 6. Generated Report

Saved to `reports/AI_server_growth_strategy.md` and `.html`

## Run It Yourself

```bash
python demo_ai_research.py "看好AI服务器产业链。云厂商资本开支提升利好算力。"
```

Or via Web UI: http://127.0.0.1:5000/research
