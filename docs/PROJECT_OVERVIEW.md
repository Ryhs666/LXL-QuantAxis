# LXL QuantAxis — Project Overview

## Why This Project Exists

Quantitative finance research has a barrier problem. Professional platforms (Bloomberg, Wind, FactSet) cost tens of thousands of dollars annually. Open-source tools are fragmented — you stitch together data from one library, backtesting from another, factors from a third, none of them talking to each other. Meanwhile, AI is reshaping how research is done, but most quant tools treat it as an afterthought.

**LXL QuantAxis exists to bridge this gap.**

It is a single, integrated research infrastructure where data flows into factors, factors compose into strategies, strategies are rigorously tested, and AI assists at every step — all running on a laptop, all open-source.

We are not building a trading bot. We are building a **research laboratory** — the kind of infrastructure that lets you ask rigorous questions about markets and get answers backed by data, not hunches.

---

## Research Philosophy

### 1. Systematic, Not Speculative

Every investment idea must be:
- **Formalized** as a testable hypothesis
- **Quantified** through factors and rules
- **Validated** via historical simulation
- **Reviewed** with performance attribution

We don't chase tips. We build and test models.

### 2. Factors as First-Class Citizens

Factors are the atomic unit of quantitative research. Every strategy, every signal, every diagnostic begins with factor computation. QuantAxis treats its 18 registered factors as a living taxonomy — you can inspect them, combine them, weight them, and create new ones through the same interface.

### 3. AI as Research Partner, Not Oracle

LLMs don't predict stock prices. They are reasoning engines. QuantAxis uses AI to:
- **Synthesize** — turn raw backtest output into readable analysis
- **Brainstorm** — propose strategy variations a human might not consider
- **Review** — critique trading decisions with behavioral finance lens
- **Generate** — automate the mechanical parts of research writing

The human remains the portfolio manager. AI is the analyst.

### 4. Full Pipeline Ownership

Every component — data ingestion, factor computation, backtesting, risk management — runs locally. Your research data never leaves your machine. Your strategies are your IP.

---

## Architecture Design

QuantAxis is organized as a **five-layer research stack**:

```
User Layer          — CLI, Web, Desktop, Dashboards
AI Research Layer   — Analyst, Sentiment, Reports, Strategy Factory
Quant Research      — Factors, Strategies, Backtesting, Analysis
Portfolio Intel     — Positions, Risk, Journal, Execution
Data Infrastructure — Market, Fundamental, Real-time, Storage
```

### Design Principles

**Separation of concerns.** Each layer depends only on the layer below it. The AI layer can call the Quant layer for backtest results, but the Quant layer never depends on AI being available. This means core research works even without an LLM API key.

**Multiple entry points.** A CLI for speed, a web dashboard for visualization, a desktop app for configuration — same engine underneath, different interfaces on top.

**Extensible by design.** Strategies, factors, and data sources all follow a registration pattern. Adding a new strategy is a single Python class. Adding a new factor is a single method. The extension surface is deliberately small.

**Local-first.** SQLite for structured data, CSV for time series, HTML for visualization. Zero cloud dependencies. Everything runs on a single machine.

---

## Project Identity

### Student-Led FinTech Research Infrastructure

LXL QuantAxis is developed and maintained by **LXL Equity Research Lab**, a student-led research initiative focused on the intersection of quantitative finance, artificial intelligence, and equity research.

Being student-led shapes how we build:

- **Learning-first design** — every module exposes its internals. The factor lab shows you how each factor is computed. The backtest engine logs every trade. Nothing is a black box.
- **Cost-conscious** — free data sources (Sina, East Money, yfinance), local computation, no paid APIs required.
- **Ambitious scope** — we tackle the full stack because understanding how the pieces fit together is the point. A factor without a backtest is theory. A backtest without risk management is dangerous. A strategy without AI-assisted review is incomplete.

### Lab Direction

```
AI × Quant Finance × Equity Research × FinTech
```

We sit at the intersection of four disciplines:
- **AI** — LLM integration, sentiment analysis, automated research
- **Quant Finance** — factor models, strategy evaluation, portfolio construction
- **Equity Research** — fundamental analysis, sector coverage, valuation
- **FinTech** — data engineering, system design, tooling infrastructure

---

## Research Coverage

| Dimension | Current | Target |
|-----------|---------|--------|
| Geographies | China A, US, HK | + Japan, Europe, Emerging Markets |
| Asset classes | Equities, Indices | + ETFs, Convertible Bonds |
| Factors | 18 technical + fundamentals | + Alternative data factors |
| Strategies | 15 registered | + User-contributed strategy marketplace |
| Data frequency | Daily | + Intraday tick for selected symbols |

---

## Future Vision

### Short-term (v6.x)
- Complete factor IC (Information Coefficient) analysis framework
- Web platform UX overhaul with real-time data streaming
- AI Research Agent with multi-turn reasoning

### Medium-term (v7.x)
- Portfolio optimization engine (mean-variance, risk parity, Black-Litterman)
- Cross-asset factor model with style factor decomposition
- Automated equity research report generation pipeline

### Long-term
- Collaborative research platform — share strategies and factors without sharing data
- Live paper trading with broker API integration
- Academic publication support — export results in journal-ready formats
- Community factor and strategy marketplace

### The Bigger Picture

The ultimate goal is not to build the best backtester. It's to build infrastructure that makes **rigorous, AI-augmented quantitative research** accessible to anyone with curiosity and a laptop — starting with students, growing with its users.

---

## Getting Involved

LXL QuantAxis is an active research project. Whether you're a student learning quantitative finance, a researcher testing factor models, or a practitioner validating strategies — the platform is designed for you.

- **Use it** — `pip install -r requirements.txt && python main.py`
- **Extend it** — write a strategy, register a factor, add a data source
- **Question it** — find what breaks, suggest what's missing
- **Build with us** — the lab is always looking for contributors who care about systematic research

---

*LXL QuantAxis v6.0 · Student-Led FinTech Research Infrastructure · LXL Equity Research Lab*
