# LXL·QuantAxis — Project Profile

## Project Overview

**LXL·QuantAxis** is an AI-native quantitative investment research platform that bridges human investment intuition with systematic factor-based analysis. It converts natural language investment theses into validated quantitative strategies without requiring the researcher to write Python strategy code.

The platform addresses a fundamental friction in quantitative research: the gap between having an investment idea ("cloud CAPEX will benefit AI server supply chains") and testing it systematically against historical data. Traditional quant workflows require manual coding at every step — factor definition, strategy construction, backtest configuration. LXL·QuantAxis automates this pipeline while maintaining safety through a declarative DSL and AST-level validation.

**Core innovation**: Human Thesis → AI Understanding → Factor Mapping → Strategy DSL → Backtest Validation → Institutional Report.

## Technical Highlights

### 1. AI Thesis Extraction
Natural language investment text is parsed into structured `InvestmentThesis` objects with dual-mode support: LLM-based extraction (DeepSeek/OpenAI/Qwen) with JSON schema validation, or deterministic rule-based fallback using keyword heuristics for Chinese and English investment terminology.

### 2. Factor Intelligence
28 built-in technical factors across 5 categories (trend, momentum, volatility, volume, pattern). A style-to-factor mapper converts investment theses (growth, value, momentum, macro, event-driven) into weighted factor models, with every factor choice justified by a natural language rationale.

### 3. Strategy DSL (Not Code Generation)
AI-generated strategies are expressed as declarative rule strings (`momentum_score > 0.6 AND trend_strength > 0.5`), never as executable Python code. The compiler uses an AST allowlist — only `Compare`, `BoolOp`, `Name`, and `Constant` nodes are permitted. Blocked operations include imports, attribute access, function calls (except allowlisted ones), and subscript access. This is a deliberate architectural choice: no amount of sandboxing makes AI-generated code safe enough for financial applications.

### 4. Backtesting Framework
Event-driven engine with T+1 execution (no look-ahead bias), A-share cost model (commission, stamp duty, transfer fee), and benchmark-relative metrics (Alpha, Beta, Information Ratio, Tracking Error). A centralized `CostConfig` ensures fee calculations are consistent across all code paths.

### 5. Portfolio Risk Analysis
Explicit return semantics (`ReturnType.SIMPLE` / `ReturnType.LOG`) and rebalance modes (`PERIODIC` / `BUY_AND_HOLD`). Four allocation models (equal weight, risk parity, mean-variance, hierarchical risk parity) with walk-forward evaluation ensuring strict train/test separation.

### 6. Automated Research Reports
Institutional-style 8-section reports in Markdown and HTML, auto-populated from pipeline outputs. Each report includes investment summary, thesis, factor analysis (with weight table), strategy construction, backtest metrics, portfolio analysis, risk assessment, and conclusion.

## Engineering Contributions

### Architecture Design
- Dual-layer V1/V2 architecture enabling incremental migration without breaking existing functionality
- 14 V1 modules import V2; 0 V2 modules import V1 — clean dependency direction
- Domain-driven design in V2: `core/`, `research/`, `strategy/`, `factor/`, `portfolio/`, `backtest/`

### Modular System
- 287 Python files, 37,500+ lines, organized into 25 domain packages
- Each subsystem independently importable and testable
- `QuantConfig` frozen dataclass replaces 15 hardcoded `D:/trading_data` paths

### Testing
- 400+ tests across unit, integration, security, contract, and characterization categories
- Tests verify: backtest correctness (no look-ahead), cost model accuracy, factor registry integrity, strategy ownership isolation, DSL safety rules

### Safety Design
- Zero AI code execution: all AI output goes through JSON extraction → schema validation → AST allowlist compilation
- JWT authentication with mandatory secret in production, no hardcoded fallback keys
- Default bind to `127.0.0.1`, CORS controlled, rate limiting on sensitive endpoints

## Technology Stack

Python 3.12 | Flask | SQLite | Pandas/NumPy | Plotly | JWT/bcrypt | akshare/yfinance | SciPy | AST compiler

## Repository

https://github.com/Ryhs666/LXL-QuantAxis
