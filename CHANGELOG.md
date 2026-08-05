# Changelog

## v2.0.0-stable (2026-08-05) — Release Candidate

### Release Notes
- All 30+ commits from `fix/portfolio-metrics-v2` merged
- Hardcoded paths eliminated (8 → 0 in runtime code; 3 remain as config defaults)
- Full test suite passing
- CI pipeline configured (pytest + ruff + bandit)
- Professional documentation: 24 docs across architecture, pipeline, cases, ecosystem
- Open source ready: MIT license, CONTRIBUTING.md, issue/PR templates

## v2.0.0-alpha (2026-08-04)

### Architecture Upgrade
- Dual-layer V1/V2 architecture with clean dependency direction (14 V1→V2, 0 V2→V1)
- Domain-driven design in `src/lxl_quantaxis/` across 50+ submodules
- Unified configuration system (`QuantConfig`) replacing hardcoded paths
- Structured logging replacing `print()`/`logging` mix
- Domain-specific exception hierarchy (`DataError`, `StrategyError`, `BacktestError`, etc.)

### AI Research Pipeline
- **AI Thesis Extraction** (`ai_parser.py`): Natural language → structured `InvestmentThesis`
- **Factor Mapping** (`factor_mapper.py`): Thesis → 28-factor registry with style-to-factor templates
- **Strategy Builder** (`strategy_builder.py`): Factor model → safe DSL strategy (no code generation)
- **Backtest Bridge** (`backtest_bridge.py`): StrategySpec → `BacktestEngine.run()` with validation
- **Backtest Analyst** (`backtest_analyzer.py`): Metrics → structured assessment with grading
- **Report Generator** (`report_generator.py`): Pipeline output → institutional Markdown/HTML report

### Quant Engine
- **Factor System**: 28 factors across 5 categories with IC analysis, decay detection, correlation heatmap
- **Strategy System**: 16 strategies (7 classic, 5 advanced, 4 factor-composed) with V2 `StrategySpec`
- **Backtest Engine**: T+1 execution, A-share cost model, benchmark metrics, signal lag queue
- **Portfolio Analytics**: Explicit `ReturnType` (simple/log) and `RebalanceMode` (periodic/buy-and-hold)
- **Allocation Models**: Equal weight, risk parity, mean-variance, true hierarchical risk parity

### Portfolio Intelligence
- Multi-strategy factor exposure analysis across 6 categories
- Three allocation methods with walk-forward validation
- Correlation and concentration risk warnings

### Safety & Security
- Zero AI code execution: declarative DSL with AST allowlist compiler
- JWT authentication with mandatory production secrets
- Default `127.0.0.1` binding, CORS control, rate limiting
- Pre-trade risk gate with 6 validation rules

### Documentation
- Architecture migration plan, dependency map, code quality report
- Professional README with pipeline diagram and demo output
- 3 research case studies (AI infrastructure, consumer recovery, semiconductor cycle)
- Application materials (project profile, resume bullets, interview guide)
- CI pipeline (GitHub Actions: pytest, ruff, bandit, compile check)

### Engineering
- 400+ tests across 5 categories (unit, integration, security, contract, characterization)
- Logical commit history with conventional commit messages
- `.gitignore` hardened for privacy (transaction data, config, secrets)

---

## Earlier Versions

### v0.3 – v1.x (2024-2025)
- Initial Tkinter GUI and Flask web application
- 7 classic strategies, factor composer, batch runner
- A-share/HK/US data via akshare and yfinance
- LLM integration for chat, strategy analysis, market briefs
- Real-time market data (Tencent API) with SocketIO push
- Multi-user auth, paper trading with leaderboard
