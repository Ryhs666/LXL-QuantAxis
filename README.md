# LXL QuantAxis

## AI-Augmented Quantitative Research Platform

**Quantitative Finance × Artificial Intelligence × Equity Research**

*Developed by LXL Equity Research Lab*

---

## Overview

LXL QuantAxis is an AI-powered quantitative research infrastructure designed for systematic equity research and investment analysis. It provides a comprehensive research pipeline spanning data acquisition, factor engineering, strategy development, historical simulation, and portfolio intelligence — augmented by LLM-based AI assistants for research synthesis and strategy discussion.

**Core research capabilities:**

- **Quantitative Research** — systematic strategy development and evaluation
- **Factor Modeling** — multi-dimensional factor engineering with 18 registered factors across 5 categories
- **Strategy Evaluation** — event-driven backtesting engine with grid search and walk-forward optimization
- **Portfolio Analytics** — position monitoring, P&L attribution, and risk assessment
- **AI-Assisted Research** — LLM-powered analysis, strategy brainstorming, and research summaries

---

## Research Framework

```
         ┌──────────────────────┐
         │     Market Data      │
         │  (Sina + East Money  │
         │   + yfinance + CSRC) │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │   Factor Research    │
         │  18 factors · 5 cats │
         │  Compute → Evaluate  │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │ Strategy Development │
         │  15 registered ·     │
         │  Composable rules    │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │    Backtesting        │
         │  Event-driven engine  │
         │  Grid Search · WFA    │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  Portfolio Analysis   │
         │  Metrics · Charts     │
         │  Risk decomposition   │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  Investment Insight   │
         │  AI synthesis ·       │
         │  Research reports     │
         └──────────────────────┘
```

---

## Core Modules

### Quant Strategy Engine

A systematic strategy research and evaluation framework. Design, test, and refine trading strategies within a unified API.

**Classic strategies (7):**

| Strategy | Description |
|----------|-------------|
| `ma_cross` | Dual Moving Average Crossover |
| `rsi` | RSI Overbought/Oversold Reversal |
| `macd` | MACD Golden Cross / Death Cross |
| `bollinger` | Bollinger Band Mean Reversion |
| `turtle` | Turtle Trading with ATR-based Stops |
| `mean_reversion` | Statistical Mean Reversion |
| `momentum` | Momentum Breakout with Volume Confirmation |

**Factor-composed strategies (4):**

| Strategy | Logic |
|----------|-------|
| `contrarian_v1` | RSI oversold + Bollinger lower band + Volume surge → weighted signal |
| `trend_following_v1` | MA golden cross + strong trend + momentum → weighted signal |
| `volume_breakout_v1` | Volume surge 2× + momentum + trend strength → weighted signal |
| `mean_reversion_v2` | MA deviation + low volatility + hammer pattern → weighted signal |

**Advanced strategies (4):**

| Strategy | Description |
|----------|-------------|
| `adaptive_composite` | Multi-signal adaptive weighting across regimes |
| `trend_short` | Dedicated short-side trend following |
| `dual_direction` | Long/short bidirectional trading |
| `regime_aware` | Market-regime-aware signal modulation |

### Factor Research Laboratory

A multi-factor modeling framework for systematic alpha research. Compose, weight, and evaluate factor combinations.

**Trend (4):** `ma_deviation` · `ma_alignment` · `ma_slope` · `trend_strength`

**Momentum (5):** `rsi_norm` · `macd_hist` · `roc_10` · `price_position` · `momentum_score`

**Volatility (4):** `volatility` · `bollinger_pos` · `bollinger_width` · `atr_ratio`

**Volume (3):** `volume_ratio` · `volume_trend` · `obv_divergence`

**Pattern (2):** `hammer` · `engulfing`

### Backtesting Engine

Event-driven historical simulation engine with:

- Multi-asset support (A-shares, US equities, HK equities, indices)
- Realistic transaction cost and slippage modeling
- Grid search hyperparameter optimization
- Walk-forward analysis for out-of-sample robustness testing
- Batch runner for cross-sectional strategy evaluation
- Performance metrics: Sharpe ratio, max drawdown, Calmar ratio, win rate, profit factor

### Portfolio Intelligence

Portfolio monitoring and risk analytics:

- Real-time position tracking with cost basis and P&L
- Trade journaling with post-trade review scoring
- Portfolio-level performance attribution
- Multi-strategy return decomposition
- Interactive HTML dashboards with Plotly visualizations

### AI Investment Research Assistant

LLM-powered research capabilities (compatible with DeepSeek, OpenAI, and other API providers):

- **Strategy Discussion** — natural language strategy ideation and critique
- **Market Analysis** — AI-synthesized market commentary
- **Research Summaries** — automated post-backtest analysis reports
- **Diagnostic Reports** — AI-generated equity diagnostics with entry/exit reasoning

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Core Compute | Python 3, NumPy, Pandas |
| Data Acquisition | AKShare, yfinance, Sina Finance, East Money |
| Technical Analysis | pandas-ta |
| Visualization | Plotly, Matplotlib |
| Web Server | Flask |
| Data Persistence | SQLAlchemy, SQLite |
| AI Integration | LLM API (OpenAI-compatible) |
| Authentication | bcrypt, PyJWT |

---

## Project Architecture

```
PythonProject1/
├── main.py                  # CLI research console
├── web_modern.py            # Web platform (Flask, http://127.0.0.1:5000)
├── daily_runner.py          # Automated daily signal scanner
├── ARCHITECTURE.md          # Full architecture documentation
├── USER_GUIDE.md            # User manual
├── requirements.txt         # Dependencies
│
├── src/
│   ├── app.py               # Desktop application (tkinter)
│   ├── config.py            # Configuration management
│   ├── utils.py             # Utilities (logging, retry, progress)
│   ├── models/              # Data models (Trade, Strategy)
│   ├── backtest/            # Engine, data feed, optimizer, batch runner
│   ├── strategies/          # Strategy library (15 strategies)
│   ├── factors/             # Factor definitions + signal composer
│   ├── analysis/            # Charts + performance reports
│   ├── journal/             # Trade journal CLI
│   ├── ai/                  # AI assistant (engine, review, factory)
│   ├── index/               # Index valuation + rotation
│   └── dashboard/           # HTML dashboards
```

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Launch

```bash
# Web research platform (Flask)
python web_modern.py
# Open http://127.0.0.1:5000

# CLI research console
python main.py

# Desktop application (tkinter)
python src/app.py
```

### AI Configuration

Configure your LLM provider in the desktop application under **AI Agent → Settings**:

- **API Key** — your provider key
- **Base URL** — `https://api.deepseek.com` (or any OpenAI-compatible endpoint)
- **Model** — `deepseek-chat`

### Data

On first run, the system auto-downloads the full A-share universe (5,500+ listed equities) and historical price data.

Data is stored at `D:/trading_data/` by default. Override via the `QUANT_DATA_DIR` environment variable.

---

## Research Coverage

| Market | Source | Instruments |
|--------|--------|-------------|
| China A-Shares | Sina Finance + East Money | 5,500+ stocks |
| US Equities | yfinance | NYSE / NASDAQ |
| Hong Kong Equities | AKShare | HKEX |
| Indices | Multiple sources | CSI 300, SSE 50, S&P 500, etc. |

---

## Roadmap

- **Global Equity Market Support** — expanded data coverage across APAC and EMEA
- **Advanced Factor Models** — machine learning factor discovery and IC analysis
- **Portfolio Optimization** — mean-variance optimization and risk parity
- **AI Research Agent** — autonomous multi-turn research workflows
- **Automated Equity Research Reports** — scheduled report generation with AI synthesis

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*LXL QuantAxis v6.0 · AI-Augmented Quantitative Research Platform · LXL Equity Research Lab*
