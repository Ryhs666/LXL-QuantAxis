# LXL QuantAxis — Roadmap

> v6.0 · July 2026
> This roadmap is a living document. Priorities shift as research evolves.

---

## Guiding Principles

Every roadmap item is evaluated against three criteria:

1. **Research value** — does it enable better, more rigorous quantitative research?
2. **Learning leverage** — does building it teach something worth knowing?
3. **Infrastructure quality** — does it make the platform more capable for everything else?

Features that score high on all three move to the top.

---

## Current Phase: v6.0 — Rebranding & Foundation

### Completed (July 2026)

- [x] Project rebranding: Personal Trading Tool → AI-Augmented Research Platform
- [x] Architecture redesign: 5-layer research stack documentation
- [x] English documentation suite (README, ARCHITECTURE, PROJECT_OVERVIEW, ROADMAP)
- [x] GitHub-ready presentation layer

---

## Phase 1: Research Infrastructure Hardening (v6.1 – v6.3)

**Goal:** Make the platform production-grade for daily research use.

### Factor Research Enhancement

- [ ] **Factor IC Analysis** — Information Coefficient computation with decay profiling across holding periods
- [ ] **Factor Correlation Matrix** — cross-factor correlation heatmap with hierarchical clustering
- [ ] **Factor Backtest** — single-factor long/short portfolio simulation (quintile spreads)
- [ ] **Turnover Analysis** — factor-induced turnover and capacity estimation

### Data Pipeline

- [ ] **Incremental Data Update** — delta-only daily refresh instead of full re-download
- [ ] **Data Quality Dashboard** — missing data alerts, outlier detection, stale cache warnings
- [ ] **Corporate Actions Handling** — dividend adjustment, split adjustment in price series
- [ ] **Multi-currency Support** — unified currency conversion for cross-market analysis

### Platform

- [ ] **Configuration as Code** — full `config.yaml` support with validation schema
- [ ] **Logging Overhaul** — structured JSON logging with rotation and retention
- [ ] **Test Suite Foundation** — core engine regression tests and factor computation validation
- [ ] **CLI Autocomplete** — tab completion for symbols, strategy names, and commands

---

## Phase 2: AI Research Augmentation (v6.4 – v6.6)

**Goal:** Move AI from auxiliary feature to integral research layer.

### AI Research Agent

- [ ] **Multi-turn Research Workflow** — AI agent that orchestrates: data pull → factor scan → strategy backtest → report generation, in a single conversation
- [ ] **Strategy Critique Mode** — given a backtest result, AI identifies overfitting signs, regime dependency, and suggests robustness checks
- [ ] **Natural Language Factor Builder** — "I want to capture mean reversion with volume confirmation" → AI proposes factor composition
- [ ] **Research Memory** — persistent research context across sessions (past analyses, preferences, watchlists)

### Sentiment & Alternative Data

- [ ] **News Sentiment Pipeline** — scheduled crawling + scoring for watchlist equities
- [ ] **Earnings Call Analysis** — transcript summarization and tone scoring
- [ ] **Macro Event Detection** — policy change, rate decision, regulatory news impact flagging
- [ ] **Social Media Heat Index** — aggregate sentiment dashboard for A-share market

### Automated Research Reports

- [ ] **Daily Market Brief** — automated morning report: overnight moves, key levels, signal summary
- [ ] **Weekly Strategy Review** — performance attribution, factor exposure breakdown, regime context
- [ ] **Equity Deep Dive** — AI-synthesized fundamental + technical + sentiment summary for a single stock
- [ ] **PDF Export** — formatted report export with charts, tables, and AI commentary

---

## Phase 3: Portfolio Intelligence (v6.7 – v7.0)

**Goal:** From strategy evaluation to portfolio construction.

### Portfolio Optimization

- [ ] **Mean-Variance Optimizer** — Markowitz efficient frontier with constraints
- [ ] **Risk Parity** — equal risk contribution portfolio construction
- [ ] **Black-Litterman Model** — Bayesian portfolio blending views with equilibrium returns
- [ ] **Minimum Variance** — global minimum variance portfolio with shrinkage estimators
- [ ] **Optimization Constraints** — sector limits, position caps, turnover penalties

### Risk Analytics

- [ ] **VaR & CVaR** — parametric, historical, and Monte Carlo Value at Risk
- [ ] **Stress Test Scenarios** — replay historical crises (2008, 2015 A-share crash, 2020 COVID)
- [ ] **Scenario Builder** — custom shock scenarios: "what if rates rise 200bp?"
- [ ] **Risk Decomposition** — factor-level risk attribution for multi-strategy portfolios
- [ ] **Drawdown Forensics** — automated analysis of what caused each significant drawdown

### Execution Simulation

- [ ] **Market Impact Model** — Almgren-Chriss style temporary + permanent impact
- [ ] **TWAP/VWAP Slicing** — schedule-based order execution simulation
- [ ] **Liquidity Analysis** — volume profile-based capacity estimation per symbol
- [ ] **Slippage Modeling** — spread + impact + delay comprehensive cost model

---

## Phase 4: Global Expansion (v7.1 – v7.3)

**Goal:** Cross-border, cross-asset research capability.

### Market Coverage

- [ ] **Japan Equities** — Tokyo Stock Exchange via yfinance / Stooq
- [ ] **European Equities** — LSE, Euronext, Xetra major listings
- [ ] **Emerging Markets** — selected coverage (India NSE, Brazil B3, Korea KRX)
- [ ] **ETF Universe** — major market and sector ETFs with holdings transparency
- [ ] **Convertible Bonds** — China convertible bond data and basic pricing

### Cross-Market Research

- [ ] **Global Factor Model** — single factor definition evaluated across all covered markets
- [ ] **Currency-Hedged Returns** — return decomposition: local return + FX return
- [ ] **Cross-Market Correlation** — dynamic correlation matrix across global indices
- [ ] **Time Zone-Aware Scheduling** — data refresh orchestration across trading sessions

---

## Phase 5: Collaboration & Community (v8.0+)

**Goal:** From personal tool to shared infrastructure.

### Strategy & Factor Marketplace

- [ ] **Strategy Packaging** — self-contained strategy bundle with metadata, parameters, and sample backtest
- [ ] **Factor Registry Sharing** — import community factors without sharing underlying data
- [ ] **Benchmark Leaderboard** — standardized benchmark for strategy comparison (same universe, same period)
- [ ] **Reproducibility Guarantee** — cryptographic hash of data snapshot ensures backtest results are verifiable

### Academic Integration

- [ ] **LaTeX Export** — backtest results and factor stats in academic paper-ready table format
- [ ] **Reproduction Package** — one-click export of full research pipeline for paper appendix
- [ ] **Citation Support** — generated BibTeX entry for the QuantAxis version used

### Platform

- [ ] **Plugin System** — third-party strategy, factor, and data source extensions
- [ ] **REST API** — headless operation with programmatic access to all research functions
- [ ] **Docker Distribution** — one-command deployment with all dependencies bundled
- [ ] **Multi-user Instance** — lab deployment with shared data layer and per-user workspaces

---

## Horizon: What We're Watching

These are ideas we find compelling but aren't committing to yet. They depend on how the project, the technology, and the research landscape evolve.

- **Reinforcement Learning Strategies** — RL agents for dynamic strategy parameter adaptation
- **Crypto Market Module** — on-chain data integration for digital asset research
- **Alternative Data Pipeline** — satellite imagery, shipping data, footfall traffic
- **Real-time Paper Trading** — broker API integration for live simulation
- **QuantAxis Cloud** — optional cloud data sync for multi-machine research setups
- **LLM Fine-tuning** — domain-adapted model for equity research analysis

---

## Contribution

This roadmap is a conversation, not a contract. If you're working on something aligned with these directions, or think something important is missing, open an issue or reach out to LXL Equity Research Lab.

---

*LXL QuantAxis v6.0 Roadmap · LXL Equity Research Lab*
