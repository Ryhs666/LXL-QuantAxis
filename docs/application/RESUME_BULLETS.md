# Resume Bullets — LXL·QuantAxis

Adapt these for your target role. Choose 3-4 bullets per application.

## Quant Research Intern

**LXL·QuantAxis — AI Quantitative Investment Research Platform**
*Python, Pandas, NumPy, Flask, SQLite*

- Designed a 6-stage AI research pipeline that converts natural language investment theses into structured factor models, executable strategies, and institutional research reports — reducing research cycle time from days to minutes
- Built a declarative Strategy DSL with AST-level safety validation, eliminating code execution risk from AI-generated strategies while maintaining full expressiveness for 16 built-in strategies
- Implemented event-driven backtest engine with T+1 execution (zero look-ahead bias) and A-share cost model (commission, stamp duty, transfer fee), producing benchmark-relative metrics (Alpha, Beta, IR)
- Developed 28-factor registry with IC analysis, stratified backtest, decay detection, and factor correlation heatmap for redundancy identification
- Created centralized transaction cost model (`CostConfig`) ensuring consistent fee calculations across all trading paths (buy, sell, short, cover)

## Financial Engineering Applicant

**LXL·QuantAxis — AI-Native Quant Research Infrastructure**
*Python, Flask, SQLite, SciPy, AST Compiler*

- Architected modular quantitative research platform with domain-driven design across 25 packages (287 files, 37,500+ lines) supporting AI-assisted investment thesis extraction, factor mapping, and strategy construction
- Implemented portfolio analytics with explicit return semantics (simple/log, periodic/buy-and-hold) and four allocation models (equal, risk parity, mean-variance, hierarchical risk parity) with walk-forward validation
- Built safe strategy compiler using AST allowlist — only `Compare`, `BoolOp`, `Name`, and `Constant` AST nodes permitted, blocking arbitrary code execution from AI output
- Engineered dual-layer V1/V2 migration architecture with 14 forward imports and zero reverse dependencies, enabling incremental system upgrades without breaking existing functionality

## FinTech / Software Engineer Applicant

**LXL·QuantAxis — Quantitative Research Platform**
*Python, Flask, Pandas, Plotly, JWT, SQLite, GitHub Actions*

- Built full-stack quantitative research web application with 60+ REST API endpoints, real-time WebSocket market data, and 5-page dashboard including AI research center
- Implemented comprehensive security: JWT authentication with mandatory production secrets, route-level authorization (public/authenticated/admin), rate limiting on sensitive endpoints, and CORS control
- Designed automated CI pipeline (GitHub Actions) with pytest (400+ tests), Ruff linting, Bandit security scanning, and compile verification
- Created institutional research report generator producing 8-section Markdown and HTML reports from pipeline outputs with professional formatting
- Established research notebook system with immutable `ResearchNote` dataclass providing full audit trail from thesis to backtest results

## Key Metrics (for any role)

- **400+ tests** passing, covering unit, integration, security, contract, and characterization
- **28 factors** across 5 categories with IC analysis and correlation detection
- **16 strategies** with parameter optimization and walk-forward validation
- **7-stage AI pipeline**: thesis → factors → strategy → validation → backtest → analysis → report
- **Zero AI code execution**: all strategy generation uses declarative DSL with AST safety
