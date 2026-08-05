# LXL·QuantAxis

> **AI-Native Quantitative Investment Research Platform**  
> Convert investment ideas into validated research — without writing strategy code.

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](.)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0-orange)](https://github.com/Ryhs666/LXL-QuantAxis/releases/tag/v2.0.0)

---

## What It Does

```
You write:  "AI servers will benefit from cloud CAPEX growth"
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
     Investment Thesis   Factor Model    Strategy DSL
            │               │               │
            └───────────────┼───────────────┘
                            ▼
                    Backtest Results
                            │
                            ▼
                 Institutional Report
                    (.md + .html)
```

**LXL·QuantAxis** bridges human investment intuition and systematic quantitative research. You provide the thesis. The platform handles factor mapping, strategy construction, backtesting, and report generation — through a **safe DSL that never executes AI-generated code**.

## Quick Demo

```bash
# One command, 7 stages, 0 code to write
$ python demo/demo_ai_research.py "AI servers benefiting from cloud CAPEX"

[1/7] Thesis Extraction       [OK]  → Note #1: AI服务器产业链看多
[2/7] Factor Mapping          [OK]  → momentum_score: 30%, trend: 25%
[3/7] Strategy Generation     [OK]  → Entry: momentum > 0.6 AND trend > 0.5
[4/7] Validation              [OK]  → All checks passed
[5/7] Backtest                [OK]  → Sharpe: 1.25
[6/7] AI Analysis             [OK]  → Viable strategy with moderate Sharpe
[7/7] Report Generation       [OK]  → reports/AI_growth_strategy.md

Complete: 7/7 stages passed
```

**[→ More examples](examples/research_cases/)**

## Quick Start

```bash
pip install -r requirements.txt

# Web UI (recommended)
python web_modern.py                # → http://127.0.0.1:5000

# CLI demo
python demo/demo_ai_research.py     # Built-in example
python demo/demo_ai_research.py "Your investment thesis"

# Interactive CLI
python main.py                      # 20+ functions menu
python main.py --research list      # View research notebook
```

### Web Pages

| Page | URL | What It Does |
|------|-----|-------------|
| Research Center | `/research` | Type an idea → get a full research report |
| Classic Dashboard | `/classic` | Backtest, strategies, factors, diagnostics |
| Trading Studio | `/studio` | Real-time K-line charts + signal alerts |
| Paper Trading | `/game` | ¥1M simulated portfolio with leaderboard |
| Admin | `/admin` | User management |

## Core Innovation

### Safe AI Strategy DSL
AI-generated strategies use declarative rules, never executable code:
```
entry: "momentum_score > 0.6 AND trend_strength > 0.5"
exit:  "max_drawdown > 0.10"
```
Rules pass through **3 safety layers**: token blocklist → AST allowlist → factor whitelist. Zero `exec`/`eval`.

### Research Pipeline (7 stages)
1. **Thesis Extraction** — Natural language → structured investment thesis
2. **Factor Mapping** — Thesis → 28-factor registry with style templates
3. **Strategy Builder** — Factors → safe DSL rules
4. **Validation** — Syntax, factors, parameters, risk checks
5. **Backtest** — T+1 execution, A-share cost model, benchmark metrics
6. **AI Analysis** — Metrics → strengths, weaknesses, suggestions
7. **Report Generation** — 8-section institutional report (Markdown + HTML)

### Research Cases
Three detailed walkthroughs showing the complete workflow:

| # | Case | Style |
|---|------|-------|
| 1 | [AI Infrastructure Supply Chain](examples/research_cases/case_ai_infrastructure.md) | Growth |
| 2 | [Consumer Sector Value Recovery](examples/research_cases/case_consumer_recovery.md) | Value |
| 3 | [Semiconductor Cycle Bottom](examples/research_cases/case_semiconductor_cycle.md) | Macro-Momentum |

## Architecture

```
┌──────────────────────────────────────────────────┐
│           Web UI / CLI / Desktop GUI              │
├──────────────────────────────────────────────────┤
│  V2 Research Layer (src/lxl_quantaxis/)           │
│  AI Pipeline · Strategy DSL · Portfolio Intel     │
├──────────────────────────────────────────────────┤
│  V1 Quant Engine (src/)                           │
│  28 Factors · 16 Strategies · Backtest Engine     │
├──────────────────────────────────────────────────┤
│  Data: akshare (A-share) · yfinance (US/HK)       │
│  Storage: SQLite ×10 · CSV Cache                  │
└──────────────────────────────────────────────────┘
```

[Full architecture documentation →](docs/ARCHITECTURE_V2.md)

## Features

| Category | Capabilities |
|----------|-------------|
| **AI Research** | Thesis extraction, factor mapping, strategy DSL, backtest analysis, report generation |
| **Factors** | 28 factors (trend, momentum, volatility, volume, pattern, sentiment, fundamental) |
| **Strategies** | 16 strategies (7 classic, 5 advanced, 4 factor-composed) with V2 compiler |
| **Backtest** | T+1 execution, A-share cost model, benchmark metrics, signal lag queue |
| **Portfolio** | 4 allocation models, walk-forward, factor exposure, diversification scoring |
| **Risk** | Pre-trade gate (6 checks), trailing stop, circuit breaker, Kelly sizing |
| **Research** | Immutable notebook, thesis builder, AI parser, correlation analyzer |

## Tech Stack

Python 3.12 · Flask · Pandas/NumPy · Plotly · SQLite · JWT/bcrypt · akshare/yfinance · SciPy

## Roadmap

| Version | Focus |
|---------|-------|
| v2.0.0 (current) | AI pipeline, safe DSL, research notebook, portfolio intelligence |
| v2.1 | Real fundamental data (financial statements, macro), live paper trading |
| v2.2 | Multi-step AI agent with iterative refinement, Docker support |
| v3.0 | Collaborative research, multi-user notebooks, cloud deployment |

## Documentation

| Document | Content |
|----------|---------|
| [Architecture V2](docs/ARCHITECTURE_V2.md) | System design with Mermaid diagrams |
| [AI Pipeline](docs/AI_PIPELINE.md) | 7-stage pipeline detail |
| [System Design](docs/SYSTEM_DESIGN.md) | Engineering principles |
| [Research Cases](examples/research_cases/) | 3 complete research walkthroughs |
| [Contributing](CONTRIBUTING.md) | Dev setup, conventions |
| [Changelog](CHANGELOG.md) | All versions |
| [Release Notes](docs/RELEASE_NOTES_v2.0.0.md) | v2.0.0 details |

## License

MIT · [Ryhs666](https://github.com/Ryhs666)
