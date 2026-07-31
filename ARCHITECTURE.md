# LXL QuantAxis — System Architecture

> v6.0 | 2026-07-31
> AI-Augmented Quantitative Research Platform
> LXL Equity Research Lab

---

## Architectural Overview

LXL QuantAxis is designed as a **layered research infrastructure** for systematic equity analysis. Each layer abstracts a distinct research concern, from data ingestion at the bottom to user interaction at the top, with AI augmentation woven through the stack.

```

                        LXL QuantAxis v6.0
            AI-Augmented Quantitative Research Platform

╔══════════════════════════════════════════════════════════════════╗
║                         USER LAYER                               ║
║                                                                  ║
║    ┌──────────┐    ┌──────────────┐    ┌──────────────────┐     ║
║    │   CLI    │    │  Web Platform│    │   Desktop (GUI)  │     ║
║    │ Console  │    │  (Flask SPA) │    │    (tkinter)     │     ║
║    └────┬─────┘    └──────┬───────┘    └────────┬─────────┘     ║
║         └──────────────────┼────────────────────┘               ║
║                            │                                    ║
║                   ┌────────┴────────┐                           ║
║                   │   Dashboards    │                           ║
║                   │  HTML · Plotly  │                           ║
║                   └─────────────────┘                           ║
╠══════════════════════════════════════════════════════════════════╣
║                      AI RESEARCH LAYER                           ║
║                                                                  ║
║  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐  ║
║  │  AI Analyst    │  │  Sentiment   │  │  Report Generator  │  ║
║  │  · Trade Coach │  │  Analysis    │  │  · Daily Brief     │  ║
║  │  · Strategy    │  │  · Social    │  │  · Backtest Report │  ║
║  │    Advisor     │  │    Sentiment │  │  · Equity Research │  ║
║  │  · Market      │  │  · Heat      │  │    Notes           │  ║
║  │    Analyst     │  │    Index     │  │                    │  ║
║  └───────┬────────┘  └──────┬───────┘  └─────────┬──────────┘  ║
║          └──────────────────┼─────────────────────┘             ║
║                             │                                   ║
║                   ┌─────────┴──────────┐                        ║
║                   │  AI Strategy Factory│                       ║
║                   │  · Genetic Evolution│                      ║
║                   │  · Factor Mining    │                      ║
║                   └────────────────────┘                        ║
╠══════════════════════════════════════════════════════════════════╣
║                    QUANT RESEARCH LAYER                          ║
║                                                                  ║
║  ┌─────────────────┐  ┌──────────────┐  ┌───────────────────┐  ║
║  │ Factor Lab       │  │ Strategy     │  │ Backtesting       │  ║
║  │ · 18 Technical   │  │ Engine       │  │ Engine            │  ║
║  │ · Fundamental    │  │ · 7 Classic  │  │ · Event-Driven    │  ║
║  │ · Signal         │  │ · 4 Composed │  │ · Grid Search     │  ║
║  │   Composer       │  │ · 4 Advanced │  │ · Walk-Forward    │  ║
║  │ · Regime Detect  │  │ · Ensemble   │  │ · Batch Runner    │  ║
║  └────────┬─────────┘  └──────┬───────┘  └─────────┬─────────┘  ║
║           └───────────────────┼─────────────────────┘            ║
║                               │                                  ║
║                     ┌─────────┴──────────┐                       ║
║                     │  Analysis Pipeline │                       ║
║                     │  · Metrics Engine  │                       ║
║                     │  · Charts (Plotly) │                       ║
║                     │  · Stress Testing  │                       ║
║                     └────────────────────┘                       ║
╠══════════════════════════════════════════════════════════════════╣
║                 PORTFOLIO INTELLIGENCE LAYER                      ║
║                                                                  ║
║  ┌─────────────────────┐    ┌──────────────────────────┐        ║
║  │ Portfolio Management│    │   Risk Management        │        ║
║  │ · Position Tracking │    │   · Trailing Stop        │        ║
║  │ · P&L Attribution   │    │   · Drawdown Circuit     │        ║
║  │ · Trade Journal     │    │   · Kelly Criterion      │        ║
║  │ · Execution Engine  │    │   · Position Limits      │        ║
║  │ · Audit Trail       │    │   · Stress Scenarios     │        ║
║  └─────────────────────┘    └──────────────────────────┘        ║
╠══════════════════════════════════════════════════════════════════╣
║                      DATA INFRASTRUCTURE                          ║
║                                                                  ║
║  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐  ║
║  │  Market Data   │  │ Fundamental  │  │  Real-time Data    │  ║
║  │  · A-Share     │  │    Data      │  │  · Tencent API     │  ║
║  │  · US Equity   │  │  · ROE / PE  │  │  · WebSocket Push  │  ║
║  │  · HK Equity   │  │  · PB / Rev  │  │  · Tick Streaming  │  ║
║  │  · Indices     │  │  · Fin. Stmt │  │  · K-line Cache    │  ║
║  │  · Multi-Source│  │              │  │                    │  ║
║  └───────┬────────┘  └──────┬───────┘  └─────────┬──────────┘  ║
║          └──────────────────┼─────────────────────┘             ║
║                             │                                   ║
║                   ┌─────────┴──────────┐                        ║
║                   │  Storage Layer     │                        ║
║                   │  SQLite · CSV ·    │                        ║
║                   │  Local File Cache  │                        ║
║                   └────────────────────┘                        ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Layer 1: User Layer

The presentation tier. Three access modes serve different research workflows.

### CLI Console (`main.py`)

The primary research console. Menu-driven, designed for rapid iteration:

| Command | Module | Function |
|---------|--------|----------|
| `V` | Quick Validate | Select equity → choose strategy → instant backtest |
| `D` | Equity Diagnosis | Full-strategy scan · investor profiling · entry timing · position sizing |
| `R` | Daily Scan | Refresh market data · scan watchlist · signal ranking |
| `1` | Trade Journal | Record entries/exits · positions · post-trade review · P&L |
| `2` | Strategy Backtest | Single equity × single strategy simulation |
| `3` | Batch Backtest | Cross-sectional: N equities × M strategies |
| `5` | Optimization | Grid search · Walk-Forward Analysis |
| `8` | Index Valuation | PE/PB percentile · valuation rating |
| `9` | Index Rotation | Momentum rotation · DCA backtest |
| `A` | AI Assistant | Trade review · strategy discussion · market dialogue |
| `4` | Performance | Reports · charts · benchmark comparison |
| `6` | Factor Lab | 18-factor browser · signal composition |
| `0` | Dashboard | KPI overview · strategy inventory · data health |

### Web Platform (`web_modern.py`)

Flask-based single-page application at `http://127.0.0.1:5000`. Provides:

- Real-time dashboard with holdings overview
- TradingView-integrated candlestick charts
- Strategy backtest UI with parameter controls
- Factor research interface
- AI chat panel for research discussion

### Desktop Application (`src/app.py`)

Tkinter-based GUI with tabbed interface:

- Market data browser
- Strategy configuration panels
- AI agent configuration and chat
- Trade journal entry forms

### Dashboards (`src/dashboard/`)

Self-contained HTML dashboards with Plotly interactive charts:

| Dashboard | Content |
|-----------|---------|
| Management Panel | KPI overview · strategy registry · recent trades |
| Performance Dashboard | Sharpe/return matrix · top-N ranking |
| Data Health | Cache status · coverage summary |

---

## Layer 2: AI Research Layer

AI augmentation services woven through the research workflow. Compatible with OpenAI, DeepSeek, and any OpenAI-compatible LLM endpoint.

### AI Analyst (`src/ai/assistants.py`)

Three specialized analyst personas, each with dedicated system prompts:

| Analyst | Role | Input | Output |
|---------|------|-------|--------|
| **Trade Review Coach** | Behavioral analysis of trading records | Trade history from SQLite | Pattern recognition, bias detection, improvement suggestions |
| **Strategy Advisor** | Strategy evaluation and optimization | Backtest results from ResultDB | Performance critique, parameter adjustment, regime-fit analysis |
| **Market Analyst** | Daily market synthesis | Market data summary + index levels | Morning/evening briefs, sector commentary, risk alerts |

### Sentiment Analysis (`src/ai/sentiment.py`)

Social sentiment pipeline for market psychology:

- Crawls East Money Guba (股吧) and Xueqiu (雪球) for trending posts
- LLM-based sentiment scoring: -1 (bearish) → +1 (bullish)
- Computes aggregate sentiment heat index per equity
- Extreme sentiment detection as contrarian signal

### Report Generator (`src/report/generator.py`)

Automated research report production:

- **Daily Brief** — positions, watchlist signals, market summary
- **Backtest Report** — performance attribution, risk decomposition, regime context
- **Equity Research Notes** — AI-synthesized fundamental + technical summary

### AI Strategy Factory (`src/ai/factory.py`)

Self-improving strategy discovery loop:

1. **Analyze** — scan all historical backtest results for profitable patterns
2. **Generate** — LLM writes new strategy code based on discovered patterns
3. **Evolve** — genetic algorithm: crossover top strategies + random mutation
4. **Validate** — automatic backtest of candidate strategies
5. **Retain** — strategies beating benchmark enter the strategy library

### Factor Miner (`src/ai/factor_miner.py`)

AI-assisted factor discovery: LLM proposes novel factor definitions from data patterns, which are then tested for IC significance.

---

## Layer 3: Quant Research Layer

The core computational engine. All quantitative research workflows live here.

### Factor Laboratory (`src/factors/`)

Multi-dimensional factor modeling framework.

#### Technical Factors (18 registered)

**Trend (4):**
| Factor | Description | Range |
|--------|-------------|-------|
| `ma_deviation` | Price deviation from 20-day MA | 0–1 (0.5 = at MA) |
| `ma_alignment` | Multi-timeframe alignment (short > mid > long = 1) | 0–1 |
| `ma_slope` | Moving average slope | 0–1 |
| `trend_strength` | Trend strength (ADX-like) | 0–1 |

**Momentum (5):**
| Factor | Description | Range |
|--------|-------------|-------|
| `rsi_norm` | Normalized RSI | 0–1 (0 = oversold, 1 = overbought) |
| `macd_hist` | MACD histogram momentum | 0–1 |
| `roc_10` | 10-day rate of change | 0–1 |
| `price_position` | Position within 60-day high-low range | 0–1 |
| `momentum_score` | Multi-period momentum composite | 0–1 |

**Volatility (4):**
| Factor | Description | Range |
|--------|-------------|-------|
| `volatility` | Historical volatility (low vol = high score) | 0–1 |
| `bollinger_pos` | Position within Bollinger Bands | 0–1 (1 = upper band) |
| `bollinger_width` | Bollinger Band width | positive |
| `atr_ratio` | ATR / price ratio | positive |

**Volume (3):**
| Factor | Description | Range |
|--------|-------------|-------|
| `volume_ratio` | Short/long-term volume ratio | 0–1 |
| `volume_trend` | Price-volume coordination health | 0–1 |
| `obv_divergence` | OBV vs price divergence | 0–1 |

**Pattern (2):**
| Factor | Description | Range |
|--------|-------------|-------|
| `hammer` | Hammer candlestick detection | 0–1 |
| `engulfing` | Engulfing pattern detection | 0–1 |

#### Fundamental Factors (`src/factors/fundamental.py`)

A-share fundamental data via AKShare:

- ROE (TTM) — return on equity
- PE ratio — trailing and forward
- PB ratio — price to book
- Revenue growth rate
- Financial statement indicators

#### Signal Composer (`src/factors/composer.py`)

```python
# Compose custom strategies from factor conditions
composer = (SignalComposer("My Strategy")
    .rsi_oversold(14, 30, weight=3)
    .volume_surge(1.5, weight=2)
    .set_logic("weighted", threshold=4.0)
    .rsi_overbought(14, 70, weight=2)
    .set_logic("or", action="SELL"))
strategy = composer.to_strategy()
```

Logic modes: `and` (all conditions) · `or` (any condition) · `weighted` (score ≥ threshold)

### Strategy Engine (`src/strategies/`)

Hierarchical strategy framework built on `BaseStrategy`:

```
BaseStrategy (abstract)
├── MACrossStrategy         — Dual moving average crossover
├── RSIStrategy             — Overbought/oversold reversal
├── MACDStrategy            — MACD golden/death cross
├── BollingerStrategy       — Bollinger Band mean reversion
├── TurtleStrategy          — Turtle trading with ATR stops
├── MeanReversionStrategy   — Statistical mean reversion
├── MomentumStrategy        — Momentum breakout + volume filter
│
├── [Factor-composed, via SignalComposer.to_strategy()]
│   ├── contrarian_v1       — RSI + Bollinger + Volume → weighted
│   ├── trend_following_v1  — MA cross + Trend + Momentum → weighted
│   ├── volume_breakout_v1  — Volume ×2 + Momentum + Trend → weighted
│   └── mean_reversion_v2   — MA dev + Low vol + Hammer → weighted
│
├── AdaptiveComposite       — Multi-signal regime-adaptive weighting
├── TrendShortStrategy      — Dedicated short-side trend following
├── DualDirectionStrategy   — Long/short bidirectional
├── RegimeAwareStrategy     — Market-regime-aware modulation
└── EnsembleStrategy        — Multi-strategy voting ensemble
```

### Backtesting Engine (`src/backtest/`)

Event-driven simulation framework.

**Core Engine** (`engine.py`):
- `BacktestEngine.run(strategy, data)` → `{portfolio, signals, metrics}`
- Internal `Portfolio` class: cash, positions, NAV, transaction log
- Realistic modeling: commission, slippage, stamp duty (A-shares)

**Performance Metrics** (`metrics.py`):
- Sharpe ratio · Max drawdown · Calmar ratio · Win rate · Profit factor
- Annualized return · Volatility · MAR ratio

**Optimization** (`optimizer.py`):
- `GridSearch` — exhaustive parameter grid with ranking
- `WalkForward` — train/test window rolling analysis
- `benchmark_compare()` — vs CSI 300 + buy-and-hold

**Batch Runner** (`batch_runner.py`):
- `BatchRunner` — cross-sectional: N symbols × M strategies
- `ResultDB` — SQLite-persisted results with query/ranking/summary
- `quick_batch()` — one-liner batch backtest API

**Validation** (`factor_validator.py`, `stress_test.py`):
- Factor IC analysis and decay profiling
- Stress scenario simulation (historical crash replay, volatility shock)

### Analysis Pipeline (`src/analysis/`)

- `charts.py` — equity curves, monthly heatmaps, P&L distributions, full portfolio chart suites
- `reports.py` — `ReportGenerator`: overview, by-market, by-strategy, by-tag, by-month breakdowns
- `regime_detector.py` — market regime classification (trending / mean-reverting / high-vol)

---

## Layer 4: Portfolio Intelligence Layer

Live portfolio management and risk control.

### Portfolio Management (`src/portfolio/`)

- `UserPortfolioManager` — per-user position tracking via SQLAlchemy
- Multi-account support with persistent `portfolios` table
- Position-level P&L attribution and cost-basis tracking
- CSV import/export for external tool integration

### Risk Management (`src/risk/`)

- **Trailing Stop** — dynamic stop-loss trailing from peak price
- **Drawdown Circuit** — account-level circuit breaker at configurable peak-to-trough threshold
- **Kelly Criterion** — optimal position sizing from win rate and profit factor
- **Single-Equity Cap** — position concentration limit (default: 15%)

### Trade Journal (`src/journal/`)

Interactive CLI for trade logging:
- Record entries/exits with automatic trade pairing
- Post-trade review with 1–5 scoring
- P&L summary with filtering by symbol, date range, tags
- Full CSV import/export pipeline

### Execution Engine (`src/execution/`)

Trade execution abstraction layer for strategy-to-broker pipeline (framework ready).

### Audit Trail (`src/audit/`)

Trade audit and compliance logging for research integrity.

---

## Layer 5: Data Infrastructure

Multi-source, multi-market data acquisition with unified access patterns.

### Market Data (`src/data/`, `src/backtest/data_feed.py`)

`MarketDataAdapter` — unified interface across markets:

| Market | Source | Suffix | Instruments |
|--------|--------|--------|-------------|
| China A-Shares | Sina Finance + East Money | `.SH` / `.SZ` | 5,500+ stocks |
| US Equities | yfinance | `.US` | NYSE / NASDAQ |
| Hong Kong Equities | AKShare | `.HK` | HKEX |
| China Indices | AKShare | `.CSI` | CSI 300, SSE 50, etc. |

Output: standardized OHLCV DataFrame (`date, open, high, low, close, volume`).

### Fundamental Data (`src/factors/fundamental.py`, `src/data/stock_db.py`)

- ROE, PE, PB, revenue growth via AKShare
- Stock universe database with sector/industry classification
- Market-wide metadata (listings, IPO dates, ST status)

### Real-time Data (`src/realtime/`)

- `collector.py` — Tencent Finance batch quote API → normalized tick format
- `engine.py` — streaming data engine with callback/SocketIO push
- `kline.py` — intraday K-line aggregation and caching

### Data Integrity (`src/data/integrity.py`)

Data quality checks: missing value detection, outlier flagging, cross-source validation.

### Storage Layout

| Store | Location | Format | Content |
|-------|----------|--------|---------|
| Trade Journal | `D:\trading_data\trades.db` | SQLite | Entry/exit records, review notes, paired P&L |
| Backtest Results | `D:\trading_data\backtest_results.db` | SQLite | Per-run metrics, parameters, rankings |
| Market Cache | `D:\trading_data\cache\*.csv` | CSV | Daily OHLCV per symbol |
| Factor Export | `D:\trading_data\factors_*.csv` | CSV | Full factor time series |
| Charts | `D:\trading_data\charts\*\*.html` | HTML | Plotly interactive charts |
| Reports | `D:\trading_data\reports\*.txt` | TXT | Daily scan reports |
| Logs | `D:\trading_data\logs\quant_*.log` | TXT | Structured runtime logs |

Override data directory via `QUANT_DATA_DIR` environment variable.

---

## Research Data Flow

```
┌──────────────────┐
│   Data Sources   │
│  Sina · East     │
│  Money · yfinance│
│  · AKShare       │
└────────┬─────────┘
         │ raw data
         ▼
┌──────────────────┐
│   DataCache      │
│   Local CSV      │
│   + SQLite       │
└────────┬─────────┘
         │ OHLCV DataFrame
         ▼
┌──────────────────────────────────────┐
│         Quant Research Pipeline       │
│                                       │
│  FactorCalculator ──► 18 factors     │
│        │                              │
│        ▼                              │
│  SignalComposer ──► trade signals    │
│        │                              │
│        ▼                              │
│  BacktestEngine ──► portfolio sim    │
│        │                              │
│        ├──────────────┬───────────────┤
│        ▼              ▼               ▼
│    Metrics        Charts          Reports
│    (Sharpe,       (Plotly,        (Text +
│     drawdown,     equity curve,   AI synthesis)
│     win rate)     heatmap)
└──────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  AI Augmentation │
│  · Sentiment     │
│  · Strategy      │
│    Discussion    │
│  · Report Gen    │
└──────────────────┘
```

---

## Class Relationships

```
BaseStrategy (abstract)
    ├── MACrossStrategy
    ├── RSIStrategy
    ├── MACDStrategy
    ├── BollingerStrategy
    ├── TurtleStrategy
    ├── MeanReversionStrategy
    ├── MomentumStrategy
    ├── AdaptiveComposite
    ├── TrendShortStrategy
    ├── DualDirectionStrategy
    └── RegimeAwareStrategy

SignalComposer.to_strategy()
    └── ComposedStrategy (dynamically generated, BacktestEngine-compatible)

BacktestEngine.run(strategy, data)
    ├── Input:  BaseStrategy + OHLCV DataFrame
    ├── Internal: Portfolio (simulated account)
    └── Output: {portfolio, signals, metrics}

GridSearch.run(strategy_name, param_grid)
    └── Internal loop: BacktestEngine.run() × N combinations
    └── Output: DataFrame ranked by metric

BatchRunner.run()
    └── Internal: GridSearch × (symbols × strategies)
    └── Output: DataFrame + SQLite persistence

WalkForward.run(strategy_name, param_grid)
    └── Internal: GridSearch(train) → BacktestEngine(test) × N windows
    └── Output: {windows, summary, metrics}

AI Strategy Factory
    └── Analyze → Generate → Evolve → Validate → Retain loop
```

---

## Extension Guide

### Add a New Strategy

```python
# In src/strategies/library.py
class MyStrategy(BaseStrategy):
    def on_bar(self, i, data, portfolio):
        # Strategy logic here
        ...

    def buy_signal(self, data): ...
    def sell_signal(self, data): ...

# Register
STRATEGIES["my_strategy"] = {...}
```

### Add a New Factor

```python
# In src/factors/definitions.py, inside FactorCalculator
def f_my_factor(self, param=10):
    # Factor computation
    return result

# Register
FACTOR_REGISTRY["my_factor"] = Factor(
    name="My Factor",
    category="custom",
    description="...",
    range=(0, 1)
)
```

### Add a New Data Provider

```python
# In src/data/providers/
from src.data.providers.base import BaseProvider

class MyProvider(BaseProvider):
    name = "my_provider"
    supported_markets = (Market.JP,)  # Extend Market enum if needed
    supported_asset_types = (AssetType.STOCK, AssetType.ETF)

    def get_history(self, request: DataRequest) -> pd.DataFrame:
        # Fetch data from your source
        df = my_fetch_function(request.symbol, ...)
        return validate_ohlcv(df, request.symbol, request.market)

# Register with the service
from src.data.service import service
service.register_provider(MyProvider())

### Add a New AI Analyst

```python
# In src/ai/assistants.py
# Define system prompt
MY_ANALYST_SYSTEM = """You are a quantitative research analyst..."""

# Add method using the existing LLMClient from src/ai/engine.py
```

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Core | Python 3, NumPy, Pandas |
| Data | AKShare, yfinance, requests |
| Technical Analysis | pandas-ta |
| Visualization | Plotly, Matplotlib |
| Web | Flask, HTML5 |
| Desktop | tkinter |
| Database | SQLAlchemy, SQLite |
| AI/LLM | OpenAI-compatible API (DeepSeek, GPT, Qwen, etc.) |
| Auth | bcrypt, PyJWT |
| Configuration | PyYAML |

---

*LXL QuantAxis v6.0 Architecture · LXL Equity Research Lab*
