# System Design — LXL·QuantAxis V2

## Engineering Principles

### 1. Modular Architecture

Each subsystem is independently importable and testable. The `src/lxl_quantaxis/` package is organized by domain:

```
lxl_quantaxis/
├── core/           # Config, logging, exceptions, contracts, security
├── research/       # Thesis, notebook, AI parser, factor mapper, strategy builder, report
├── strategy/       # Base spec, compiler, registry, validator, backtest bridge
├── factor/         # Base spec, pipeline, registry, validation
├── portfolio/      # Analytics, allocation, accounting, intelligence
├── backtest/       # Data portal, event loop, fill models, cost model, signal lag
├── ai/             # LLM ports, backtest analyzer, guardrails
├── data/           # Catalog, providers, storage, quality
├── api/            # Routes, middleware, schemas, services
├── execution/      # Broker interface, orders, paper trading
├── risk/           # Policies, pre-trade chain
├── memory/         # Alpha memory extraction, repository
├── ops/            # Backup, kill switch, release
└── dashboard/      # Feature flags, workspace registry
```

**Dependency rule**: V2 modules never import from legacy `src/` modules. Legacy modules may import V2 (14 modules do so, 0 reverse dependencies).

### 2. AI as Assistant, Not Decision Maker

- AI output is always schema-validated before use
- All AI-generated strategies must pass rule-based validation
- AI analysis includes a confidence score
- Human confirmation required for strategy activation
- Research notebook preserves the full audit trail

### 3. Safety First

**Code Execution**: Zero tolerance. AI output is parsed as structured JSON, validated against whitelists, and fed into an AST allowlist compiler. No `exec`, `eval`, or `compile` on AI output.

**Authentication**: JWT with mandatory secret in production. No hardcoded fallback keys. Default bind to `127.0.0.1`.

**Data Access**: All SQL uses parameterized queries. File paths derived from config, never hardcoded.

### 4. Research Reproducibility

- Immutable `ResearchNote` dataclass: once written, never modified
- `ResearchManifest`: captures git commit, Python version, timestamps, parameters
- All pipeline stages produce auditable intermediate outputs
- `ResearchReport` includes source attribution for every data point

### 5. Test-Driven Development

- 400+ tests covering core, factor, strategy, backtest, research, security
- Separate characterization tests for legacy behavior
- Contract tests for data provider interfaces
- Security tests for auth, ownership, route permissions

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| DSL over code generation | Safety: no executable AI output |
| SQLite over PostgreSQL | Zero-config, portable, sufficient for single-user |
| Frozen dataclasses | Immutability guarantees for research records |
| Dual V1/V2 architecture | Incremental migration without breaking existing users |
| Rule-based fallback for AI | Platform works without LLM, degrade gracefully |
| Separate test categories | Security/contract/characterization tests isolated from unit tests |
