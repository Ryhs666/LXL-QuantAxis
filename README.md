# LXL·QuantAxis

> AI-Native Quantitative Investment Research Platform  
> **Version**: 2.0.0 | **Status**: Active Development | **License**: MIT

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](.)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**LXL·QuantAxis** bridges the gap between **human investment intuition** and **systematic quantitative research**. It converts natural language investment ideas into structured factor models, executable strategies, validated backtests, and institutional research reports — all without requiring the researcher to write Python strategy code.

---

## 1. Overview

### The Problem

Traditional quant systems follow a rigid pipeline:

```
Data → Factors → Strategy → Backtest
```

The researcher manually codes every step. An investment idea ("AI servers will benefit from cloud CAPEX") requires translating qualitative insight into factor definitions, strategy rules, and backtest parameters — a process that takes days and creates friction between ideation and validation.

### The Solution

LXL·QuantAxis inverts the workflow:

```
Human Thesis → AI → Factors → Strategy → Validation → Report
```

You write what you believe. The platform handles the rest.

- **Say it**: "Cloud CAPEX growth benefits AI server supply chain."
- **Get back**: Factor model, strategy DSL, backtest metrics, risk assessment, and an institutional research report.

---

## 2. Core Innovation

### 2.1 AI Investment Research Pipeline

A 6-stage pipeline that transforms unstructured text into validated research output:

```
Natural Language → Thesis → Factor Model → Strategy DSL → Backtest → Report
```

Each stage is auditable, reversible, and works with or without LLM access.

### 2.2 Human Thesis → Quant Strategy

The platform understands investment language. "Growth at reasonable price" maps to momentum + value factors. "Defensive dividend play" maps to low-volatility + quality. The mapping is explainable — every factor choice comes with a reason.

### 2.3 Safe Strategy DSL

AI-generated strategies are expressed as a declarative DSL with AST-level validation. **No Python code is ever executed from AI output.** The compiler uses an allowlist of safe operations, blocking imports, attribute access, and arbitrary function calls.

### 2.4 Automated Research Reports

The pipeline produces institutional-style reports in Markdown and HTML with eight standard sections: investment summary, thesis, factor analysis, strategy construction, backtest results, portfolio analysis, risk assessment, and conclusion.

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web UI / CLI / Demo                      │
├─────────────────────────────────────────────────────────────┤
│  Research Layer   │  thesis · notebook · ai_parser · report  │
│  AI Layer         │  factor_mapper · strategy_builder        │
│                   │  backtest_analyzer                       │
│  Quant Layer      │  factors(28) · strategies(16)            │
│                   │  backtest engine · cost model            │
│  Portfolio Layer  │  analytics · allocation · intelligence   │
│  Data Layer       │  akshare · yfinance · SQLite ×10         │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. AI Research Pipeline

```
$ python demo_ai_research.py "AI servers benefiting from cloud CAPEX growth"

[1/6] AI Thesis Extraction
  → Note #1: AI服务器产业链看多

[2/6] Factor Model Mapping
  → Theme: AI Infrastructure, Factors: 4, Source: rule

[3/6] Strategy Building
  → Strategy: AI_growth_strategy, Source: rule

[4/6] Backtest (000001, 2024-01-01)
  → Status: backtested, Sharpe: 1.25

[5/6] AI Backtest Analysis
  → Summary: Viable strategy with moderate Sharpe

[6/6] Research Report
  → Report saved: reports/AI_growth_strategy.md
```

---

## 5. Features

### AI Research Agent
- Parse natural language into structured investment theses
- Dual mode: LLM (DeepSeek/OpenAI/Qwen) or rule-based fallback
- Schema-validated output — no hallucinated field values

### Factor Intelligence
- 28 built-in factors across trend, momentum, volatility, volume, pattern
- Style-to-factor mapping: growth, value, momentum, macro, event-driven
- Factor correlation analysis with redundancy detection

### Strategy Engine
- 16 built-in strategies (MA cross, RSI, MACD, Bollinger, Turtle, etc.)
- Safe DSL compiler: AST allowlist, no code execution
- T+1 execution with A-share cost model (commission, stamp duty, transfer fee)
- Validation: rule syntax, factor existence, parameter ranges

### Backtesting
- Event-driven engine with next-bar fill (no look-ahead bias)
- Benchmark-relative metrics: Alpha, Beta, IR, Tracking Error
- Walk-forward evaluation with strict train/test separation

### Portfolio Analytics
- Explicit return semantics: simple vs log, periodic vs buy-and-hold
- 4 allocation models: equal, risk parity, mean-variance, HRP
- Factor exposure analysis across 6 categories

### Research Report Generator
- 8-section institutional report in Markdown and HTML
- Auto-populated from pipeline outputs
- One-click save to disk

---

## 6. Research Examples

Three detailed case studies demonstrate the full AI research workflow:

| Case | Theme | Style | Question |
|------|-------|-------|-----------|
| [AI Infrastructure](examples/research_cases/case_ai_infrastructure.md) | AI服务器产业链 | Growth | Is the AI investment cycle sustainable? |
| [Consumer Recovery](examples/research_cases/case_consumer_recovery.md) | 消费板块复苏 | Value | Is the consumer sector undervalued? |
| [Semiconductor Cycle](examples/research_cases/case_semiconductor_cycle.md) | 半导体周期 | Macro-Momentum | Are we at a cycle bottom? |

Each case walks through: research question → thesis → factor mapping → strategy construction → backtest interpretation → risk analysis → conclusion.

See [Research Case Library](examples/research_cases/README.md) for the full collection.

## 7. Quick Start

```bash
# Install
pip install -r requirements.txt

# Launch Web UI
python web_modern.py            # → http://127.0.0.1:5000

# Run AI Research Pipeline
python demo_ai_research.py "Your investment idea"

# CLI
python main.py                  # Interactive menu
python main.py --research list  # View research notebook
```

### Web Pages

| Page | Path | Description |
|------|------|-------------|
| Research Center | `/research` | AI pipeline runner + notebook browser |
| Classic Panel | `/classic` | Full-featured quant dashboard |
| Trading Studio | `/studio` | Real-time charts + signals |
| Paper Trading | `/game` | Simulated trading with leaderboard |
| Admin | `/admin` | User management |

---

## 8. Tech Stack

| Layer | Technology |
|-------|-----------|
| Core | Python 3.12, NumPy, Pandas |
| Web | Flask, Flask-SocketIO, Plotly |
| Storage | SQLite (10 databases) |
| Data | akshare (A-share), yfinance (US/HK) |
| AI | OpenAI-compatible API (DeepSeek/Qwen/Ollama) |
| Optimization | SciPy (optional), Optuna (optional) |
| Security | JWT, bcrypt, AST allowlist |

---

## 9. Project Philosophy

LXL·QuantAxis is built on a research-driven workflow:

```
Hypothesis → Model → Validation → Review
```

Every investment thesis is: (1) recorded as a research note, (2) mapped to measurable factors, (3) tested against historical data, (4) reviewed by AI analysis, and (5) preserved for future reference. Nothing is ephemeral. The research notebook is the system of record.

### What It Is
- An AI-assisted investment research platform
- A DSL-based strategy construction system
- A backtest engine with institutional reporting

### What It Is Not
- A live trading system (paper trading only)
- A market data vendor (relies on akshare/yfinance)
- A replacement for professional judgment (AI output requires human review)

---

## 10. LXL Ecosystem

LXL·QuantAxis is part of the LXL Investment Research Ecosystem:

| Component | Role |
|-----------|------|
| **LXL Equity Research Lab** | Fundamental analysis: company research, industry mapping, financial modeling, valuation |
| **LXL·QuantAxis V2.0** | Quantitative intelligence: AI thesis extraction, factor mapping, strategy validation, automated reporting |

Together they form a technology-driven research platform where **human analysts generate investment ideas** and **AI validates, structures, and documents them**.

See [LXL Ecosystem Overview](docs/lxl_ecosystem/LXL_ECOSYSTEM_OVERVIEW.md) for details.

## License

MIT
