# Graduate Application Supplement — LXL·QuantAxis

*For MFE (Financial Engineering), FinTech, and Computational Finance programs.*

## Project: LXL·QuantAxis — AI-Assisted Quantitative Investment Research Platform

**Role**: Sole developer, architect, and researcher  
**Duration**: 2025-2026  
**Stack**: Python, Pandas/NumPy, Flask, SQLite, Plotly, JWT  
**Repository**: github.com/Ryhs666/LXL-QuantAxis

## Project Motivation

Traditional quantitative research follows a rigid pipeline: data collection → factor engineering → strategy coding → backtesting → analysis. Each stage requires manual coding, creating friction between having an investment hypothesis and testing it. A researcher who believes "cloud CAPEX growth will drive AI server demand" must manually translate this qualitative insight into factor definitions, strategy rules, and backtest parameters — a process that can take days.

I built LXL·QuantAxis to reduce this friction. The platform automates the mechanical aspects of quant research — factor selection, strategy construction, report generation — while preserving the researcher's role as the source of investment insight and the final decision maker. AI assists; humans decide.

## Research Contribution

### 1. Structured Investment Thesis Extraction

The platform demonstrates that natural language investment theses can be reliably mapped to quantitative factors without AI-generated code. The extraction pipeline uses a dual-mode architecture: LLM-based parsing with structured JSON output validated against a strict schema, with deterministic rule-based fallback using keyword heuristics. This ensures the platform functions regardless of LLM availability.

### 2. Safe Strategy DSL Design

A key contribution is the design of a declarative strategy DSL that is expressive enough for real strategies but restrictive enough to be provably safe. The compiler uses Python's `ast` module with an explicit allowlist — only `Compare`, `BoolOp`, `Name`, and `Constant` AST nodes are permitted. This design choice eliminates the entire class of risks associated with AI-generated executable code while maintaining the ability to express complex multi-factor trading rules.

### 3. Research Reproducibility Infrastructure

Every stage of the research pipeline produces immutable, auditable outputs. The `ResearchNote` frozen dataclass ensures that once a thesis is recorded, it cannot be modified. The research manifest captures git commit hash, Python version, parameters, and timestamps — enabling exact reproduction of any research session.

## Technical Innovation

### Architecture

The dual-layer V1/V2 architecture demonstrates a practical approach to large-scale refactoring of a production system. Rather than rewriting 37,500 lines of working code, the V2 layer (`src/lxl_quantaxis/`) is built as a clean extension with domain-driven design. Fourteen V1 modules import V2; zero V2 modules import V1 — a clean dependency direction that enables incremental migration without downtime.

### Safety-First Design

Financial software has unique safety requirements. The platform implements:
- Zero AI code execution (declarative DSL only)
- JWT authentication with mandatory production secrets
- Default localhost binding
- Rate limiting on sensitive endpoints
- Immutable research records

### Testing Rigor

400+ tests across five categories: unit tests (core logic), integration tests (pipeline stages), security tests (auth, ownership, route permissions), contract tests (data provider interfaces), and characterization tests (legacy behavior preservation).

## Quantitative Finance Connection

The platform applies several concepts from quantitative finance coursework:

- **Factor models**: 28-factor registry with IC analysis, demonstrating practical implementation of academic factor research
- **Portfolio theory**: Four allocation models (equal, risk parity, mean-variance, HRP) with walk-forward validation
- **Transaction cost modeling**: Centralized A-share cost model (commission, stamp duty, transfer fee, short borrow)
- **Risk management**: Pre-trade gate with 6 risk checks, drawdown circuit breaker, Kelly position sizing
- **Performance attribution**: Brinson decomposition, Alpha/Beta/IR calculation

## Learning Outcomes

This project developed skills in:

1. **Large-scale system architecture**: Managing a 37,500-line codebase through a major architecture migration
2. **Financial software safety**: Designing systems where errors have real consequences
3. **AI system design**: Building AI-assisted workflows that respect human decision authority
4. **Quantitative methods**: Implementing factor research, backtesting, and portfolio analytics from first principles
5. **Software engineering practices**: CI/CD, test-driven development, security-first design

## Program Fit

**Financial Engineering (MFE)**: The project demonstrates applied quant finance skills — factor models, portfolio construction, risk management, backtesting — combined with software engineering rigor.

**Financial Technology (FinTech)**: The project showcases full-stack development of a financial application with security-first design, API architecture, and AI integration.

**Computational Finance**: The project implements numerical methods (optimization, time series analysis, Monte Carlo-adjacent validation) in a practical financial context.

---

*The platform is paper trading only. No real capital was deployed. All investment theses in documentation are for methodological illustration only.*
