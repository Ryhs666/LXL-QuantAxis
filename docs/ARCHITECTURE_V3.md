# LXL·QuantAxis V3.0 — Architecture Design

> **AI Investment Research Operating System**  
> From AI Research Showcase → Production-Grade Research OS

**Status**: Design Phase | **Base**: v2.0.0 stable showcase | **Target**: v3.0.0  
**Role**: Buy-side Quant Research Lead × FinTech Product Architect  
**Date**: 2026-08-06

---

## Table of Contents

1. [Vision & Strategic Rationale](#1-vision--strategic-rationale)
2. [V2 → V3 Evolution Map](#2-v2--v3-evolution-map)
3. [System Architecture](#3-system-architecture)
4. [Fundamental Intelligence](#4-fundamental-intelligence)
5. [Investment Journal Memory](#5-investment-journal-memory)
6. [Research Agent Framework](#6-research-agent-framework)
7. [Backtesting Engine V3](#7-backtesting-engine-v3)
8. [Report Generation System](#8-report-generation-system)
9. [Data Architecture](#9-data-architecture)
10. [API & Integration Layer](#10-api--integration-layer)
11. [Web Workspace V3](#11-web-workspace-v3)
12. [Safety & Compliance](#12-safety--compliance)
13. [V2 Compatibility Guarantee](#13-v2-compatibility-guarantee)
14. [Development Roadmap](#14-development-roadmap)
15. [Key Design Decisions](#15-key-design-decisions)

---

## 1. Vision & Strategic Rationale

### 1.1 The OS Metaphor

LXL·QuantAxis V2 is a **pipeline**: linear, one-shot, single-user. LXL·QuantAxis V3 is an **operating system**: event-driven, persistent, multi-agent, with scheduling, memory, and a unified workspace.

| OS Primitive | V3 System Component |
|--------------|---------------------|
| **Process** | Research Agent (autonomous, scheduled) |
| **Memory** | Investment Journal + Research Memory |
| **File System** | Data Catalog + Report Archive |
| **Scheduler** | Research Orchestrator (cron, event-triggered) |
| **Kernel** | Quant Engine (factors, strategies, backtest) |
| **UI Shell** | Web Workspace (multi-tab, project-based) |
| **Permissions** | RBAC + Audit Trail |

### 1.2 Core Value Proposition

```
V2: "Convert an investment idea into a backtest report."
V3: "Run a persistent investment research operation that continuously
     generates, validates, tracks, and refines investment theses —
     with full auditability, reproducibility, and organizational memory."
```

### 1.3 Target User Profile

| Persona | Need | V3 Feature |
|---------|------|------------|
| **Independent Quant** | Systematic idea generation & validation | Research Agent Framework |
| **Buy-side Analyst** | Fundamental + quantitative integration | Fundamental Intelligence |
| **Portfolio Manager** | Decision tracking & performance attribution | Investment Journal Memory |
| **Research Director** | Team coordination & audit trail | Multi-user Workspace + RBAC |
| **Quant Developer** | Extensible strategy platform | Plugin SDK + Backtesting Engine V3 |

---

## 2. V2 → V3 Evolution Map

### 2.1 What Changes

| Dimension | V2.0 | V3.0 |
|-----------|------|------|
| **Paradigm** | Linear pipeline | Event-driven OS |
| **AI Role** | Single-pass assistant | Persistent multi-agent framework |
| **Fundamentals** | Technical factors only (28) | Technical + Fundamental + Macro + Sentiment |
| **Memory** | None (stateless) | Journal + Memory + Audit Trail |
| **Backtesting** | Single-asset event loop | Multi-asset, multi-frequency, PIT-aware |
| **Reports** | Markdown + HTML template | Multi-format, multi-audience, scheduled |
| **UI** | 9 standalone pages | Unified workspace with project context |
| **Users** | Single-user localhost | Multi-user with RBAC |
| **Data** | CSV cache + SQLite ×10 | Data catalog with quality gates + PIT storage |
| **Execution** | Simulation only | Paper trading + broker interface (read-only) |
| **Scheduling** | Manual trigger | Cron, event-triggered, conditional |

### 2.2 What Stays (V2 Compatibility)

All V2 modules remain importable with the same public API:

- `src/lxl_quantaxis/factor/` — 28-factor registry, pipeline, validation
- `src/lxl_quantaxis/strategy/` — DSL compiler, spec, validator, backtest bridge
- `src/lxl_quantaxis/backtest/` — event loop, fill models, cost model, signal lag
- `src/lxl_quantaxis/research/` — AI parser, factor mapper, strategy builder, report generator
- `src/lxl_quantaxis/portfolio/` — analytics, allocation, accounting
- `src/lxl_quantaxis/ai/` — LLM ports, guardrails, backtest analyzer
- `src/lxl_quantaxis/core/` — config, contracts, events, observability
- `src/lxl_quantaxis/data/` — providers, storage, catalog, quality gates
- `src/lxl_quantaxis/api/` — REST routes, middleware, schemas

V2 pipeline continues to work identically: `demo/demo_ai_research.py` unchanged.

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Web Workspace V3 (SPA)                                │
│   Projects · Agents · Journal · Pipeline · Portfolio · Reports · Admin       │
├─────────────────────────────────────────────────────────────────────────────┤
│                         API Gateway (Flask → FastAPI migration)               │
│              REST · WebSocket · JWT Auth · Rate Limiting · Audit              │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────────────┤
│ Research │ Journal  │ Fundam.  │ Backtest │ Report   │   Scheduling &       │
│ Agent    │ Memory   │ Intelli- │ Engine   │ Gen      │   Orchestration       │
│ Framework│ Engine   │ gence    │ V3       │ System   │                       │
├──────────┴──────────┴──────────┴──────────┴──────────┴──────────────────────┤
│                           Quant Kernel (V2 Compatible)                        │
│   Factors (28+) · Strategies (16+) · DSL Compiler · Portfolio Analytics       │
├──────────────────────────────────────────────────────────────────────────────┤
│                           Data Fabric                                         │
│   Catalog · Quality Gates · PIT Storage · Provider Adapters · Cache Layers    │
├──────────────────────────────────────────────────────────────────────────────┤
│                           Infrastructure                                      │
│   SQLite/PostgreSQL · Redis · File System · Docker · Prometheus               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Layered Architecture Detail

```
Layer 5: Presentation     web_workspace/     SPA (React/HTMX), multi-tab, project-based
──────────────────────────────────────────────────────────────────────────
Layer 4: Application      api/v3/            REST + WebSocket, RBAC, rate limiting
                          orchestration/     Scheduler, event bus, workflow engine
──────────────────────────────────────────────────────────────────────────
Layer 3: Intelligence     agents/            Research agent framework, multi-agent orchestration
                          journal/           Investment journal, memory, decision tracking
                          fundamental/       Financial data, macro, industry, factor bridge
                          report/            Multi-format report generation pipeline
──────────────────────────────────────────────────────────────────────────
Layer 2: Quant Kernel     factor/            28+ factors, registry, pipeline, validation
  (V2 Compatible)         strategy/          DSL compiler, spec, validator, backtest bridge
                          backtest/          Event loop, fill models, cost model, PIT portal
                          portfolio/         Analytics, allocation, risk parity, HRP
                          ai/                LLM ports, guardrails, analyzer, prompts
──────────────────────────────────────────────────────────────────────────
Layer 1: Data Fabric      data/              Catalog, quality gates, PIT storage
                          providers/         Market, fundamental, macro, news, sentiment
                          storage/           SQLite, PostgreSQL, file system, Redis cache
──────────────────────────────────────────────────────────────────────────
Layer 0: Infrastructure   core/              Config, contracts, events, telemetry, security
                          ops/               Backup, kill switch, release, health checks
```

### 3.3 Event-Driven Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Event Bus (Redis Pub/Sub)                │
├────────────┬────────────┬────────────┬────────────┬──────────┤
│ Market     │ Research   │ Portfolio  │ System     │ User     │
│ Events     │ Events     │ Events     │ Events     │ Events   │
├────────────┼────────────┼────────────┼────────────┼──────────┤
│ Price tick │ Thesis     │ Position   │ Schedule   │ Manual   │
│ Signal     │ created    │ change     │ trigger    │ trigger  │
│ Data ready │ Backtest   │ P&L update │ Error      │ Config   │
│ Corp action│ complete   │ Risk alert │ Health     │ change   │
└────────────┴────────────┴────────────┴────────────┴──────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Event Handlers                             │
│  on_market_data_ready()  → trigger scheduled research         │
│  on_signal_generated()   → log to journal, notify user        │
│  on_backtest_complete()  → generate report, update memory     │
│  on_risk_breach()        → alert, log, suggest action         │
│  on_schedule_tick()      → run daily/weekly/monthly jobs      │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Fundamental Intelligence

### 4.1 Purpose

Technical factors tell you **what** is happening. Fundamentals tell you **why**. V3 integrates fundamental analysis as a first-class citizen — not a bolt-on, but a core intelligence module that feeds the entire research pipeline.

### 4.2 Data Domains

```
Fundamental Intelligence
├── Financial Statements (Quarterly)
│   ├── Balance Sheet: assets, liabilities, equity, goodwill, intangibles
│   ├── Income Statement: revenue, COGS, operating profit, net income, EPS
│   └── Cash Flow: operating CF, investing CF, free cash flow, CAPEX
│
├── Financial Metrics (TTM + Historical Series)
│   ├── Valuation: PE(TTM), PB, PS, EV/EBITDA, PEG
│   ├── Profitability: ROE (DuPont decomposition), ROA, ROIC, gross/net margin
│   ├── Growth: revenue YoY, earnings YoY, FCF growth, margin expansion
│   ├── Quality: accruals ratio, earnings variability, asset turnover
│   └── Health: debt/equity, current ratio, interest coverage, Altman Z-score
│
├── Industry & Peer Context
│   ├── Shenwan (申万) industry classification → sector aggregates
│   ├── Peer comparison: percentile rank within industry
│   ├── Industry lifecycle stage assessment
│   └── Supply chain position & concentration risk
│
├── Macro Intelligence
│   ├── China: GDP, CPI, PPI, PMI (mfg/services), LPR, M2, social financing
│   ├── US: GDP, CPI, Fed funds rate, ISM PMI, non-farm payrolls, treasury yields
│   ├── Global: commodity prices (copper, oil, gold), Baltic Dry Index, VIX
│   └── Policy: fiscal stimulus, monetary stance, regulatory changes
│
├── Corporate Actions & Events
│   ├── Dividends: history, yield, payout ratio, ex-dividend dates
│   ├── Splits, rights issues, buybacks
│   ├── Insider trading: reported purchases/sales
│   └── Major announcements: M&A, restructuring, guidance changes
│
└── Alternative Data (Phase 2)
    ├── Supply chain: shipping data, satellite imagery
    ├── Consumer: credit card transactions, app downloads
    └── Sentiment: news NLP, social media, analyst consensus
```

### 4.3 Module Design

```
src/lxl_quantaxis/fundamental/
├── __init__.py
├── contracts.py              # FundamentalSnapshot, FundamentalSeries, IndustryContext
├── fetcher/
│   ├── __init__.py
│   ├── financials.py         # akshare: balance sheet, income, cash flow
│   ├── metrics.py            # Derived financial metrics (PE, ROE, etc.)
│   ├── industry.py           # Shenwan classification + peer data
│   ├── macro_cn.py           # China macro indicators
│   ├── macro_us.py           # US macro indicators
│   └── corporate.py          # Dividends, splits, insider trades
├── storage/
│   ├── __init__.py
│   ├── series_db.py          # FundamentalSeriesDB (SQLite + PostgreSQL)
│   ├── snapshot_db.py        # FundamentalSnapshotDB (point-in-time)
│   └── cache.py              # Intelligent caching with staleness policies
├── analysis/
│   ├── __init__.py
│   ├── dupont.py             # DuPont ROE decomposition
│   ├── quality.py            # Earnings quality assessment
│   ├── peer.py               # Industry-relative scoring
│   └── trend.py              # Multi-period trend analysis
├── bridge/
│   ├── __init__.py
│   ├── factor_bridge.py      # Register fundamental-derived factors
│   ├── signal_bridge.py      # Fundamental signal generation
│   └── thesis_bridge.py      # Enrich thesis with fundamental context
└── scheduler/
    ├── __init__.py
    └── update_jobs.py        # Scheduled fundamental data refresh
```

### 4.4 Fundamental Factor Bridge

Registers 15+ fundamental-derived factors into the existing FACTOR_REGISTRY:

| Factor Key | Description | Category | Update Freq |
|------------|-------------|----------|-------------|
| `pe_percentile_5y` | PE relative to 5-year range (0=cheap, 1=expensive) | Valuation | Weekly |
| `pb_percentile_5y` | PB relative to 5-year range | Valuation | Weekly |
| `roe_level` | ROE absolute level (normalized) | Profitability | Quarterly |
| `roe_trend_4q` | ROE direction over last 4 quarters | Profitability | Quarterly |
| `revenue_growth_yy` | Year-over-year revenue growth | Growth | Quarterly |
| `earnings_growth_yy` | Year-over-year earnings growth | Growth | Quarterly |
| `earnings_revision` | Analyst estimate revision trend | Sentiment | Weekly |
| `margin_trend` | Gross/net margin direction (2-year) | Quality | Quarterly |
| `fcf_yield` | Free cash flow / market cap | Quality | Quarterly |
| `debt_health` | Composite: debt/equity + coverage ratio | Health | Quarterly |
| `altman_z` | Altman Z-score (normalized) | Health | Quarterly |
| `industry_relative_pe` | PE vs industry median | Relative | Weekly |
| `industry_relative_roe` | ROE vs industry median | Relative | Quarterly |
| `macro_pmi_sensitivity` | Stock beta to PMI changes | Macro | Monthly |
| `macro_rate_sensitivity` | Stock beta to interest rate changes | Macro | Monthly |
| `dividend_yield` | Trailing dividend yield | Income | Weekly |

### 4.5 Data Freshness Policies

| Data Type | Staleness Threshold | Refresh Trigger |
|-----------|-------------------|-----------------|
| Real-time price | 1 minute | On access |
| Daily OHLCV | End of trading day | Scheduled (15:30 CST) |
| Financial statements | Next quarter + 45 days | Scheduled (weekly check) |
| Macro indicators | Next release date | Scheduled (calendar-based) |
| Industry classification | Monthly | Scheduled (monthly) |
| Analyst estimates | Weekly | Scheduled (weekly) |

---

## 5. Investment Journal Memory

### 5.1 Purpose

The Investment Journal Memory is the **persistent consciousness** of the system. It remembers every thesis, every decision, every backtest result, and — critically — tracks how predictions performed against reality. This transforms the platform from a "research tool" into a "learning system."

### 5.2 Memory Architecture

```
Investment Journal Memory
├── Research Memory (Thesis Lifecycle)
│   ├── Thesis creation → factor mapping → strategy → backtest → review
│   ├── Outcome tracking: was the thesis correct? what was the realized return?
│   └── Conviction calibration: do high-conviction theses outperform?
│
├── Decision Memory (Trade Decisions)
│   ├── Entry: date, price, size, rationale, confidence, market context
│   ├── Exit: date, price, P&L, reason (target/stop/thesis change/time)
│   └── Attribution: how much was skill vs beta vs luck?
│
├── Observation Memory (Market Notes)
│   ├── Macro observations: rate changes, policy shifts, sentiment extremes
│   ├── Sector observations: rotation signals, regulatory changes, supply chain
│   └── Company observations: earnings surprises, management changes, product launches
│
├── Lesson Memory (Learning)
│   ├── Pattern library: recurring setups that worked/failed
│   ├── Mistake taxonomy: categorized errors with corrective actions
│   └── Rule evolution: how strategy rules changed based on experience
│
└── Context Memory (State)
    ├── Current portfolio state snapshot
    ├── Active theses with confidence levels
    ├── Pending decisions and deadlines
    └── Market regime assessment
```

### 5.3 Data Model

```python
# src/lxl_quantaxis/journal/models.py

@dataclass(frozen=True, slots=True)
class ResearchMemory:
    """Complete lifecycle of an investment thesis."""
    memory_id: str              # UUID
    project_id: str | None      # FK → ResearchProject
    thesis_id: int              # FK → research_notes

    # Pipeline outputs (immutable snapshots)
    original_text: str          # raw natural language input
    parsed_thesis: dict         # structured thesis JSON
    factor_model: dict          # selected factors + weights
    strategy_spec: dict         # compiled DSL strategy
    backtest_result: dict       # full backtest metrics
    ai_assessment: dict         # AI quality assessment
    report_path: str | None     # path to generated report

    # Conviction tracking
    conviction_score: float     # 0.0–1.0, self-assessed at creation
    conviction_rationale: str   # why this confidence level?

    # Outcome tracking (filled later)
    outcome_status: str         # "pending" | "validated" | "invalidated" | "expired" | "inconclusive"
    realized_return: float | None
    benchmark_return: float | None  # for attribution
    outcome_notes: str | None
    reviewed_at: str | None

    # Metadata
    tags: list[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """Single journal entry — observation, decision, or lesson."""
    entry_id: int
    date: str
    entry_type: str             # "observation" | "decision" | "lesson" | "review" | "daily_note"
    title: str
    content: str                # Markdown body

    # Cross-references
    symbols: list[str]
    tags: list[str]
    related_thesis_ids: list[int]
    related_memory_ids: list[str]
    related_journal_ids: list[int]

    # Context
    mood: str | None            # "bullish" | "bearish" | "neutral" | "uncertain" | "anxious"
    market_regime: str | None   # "bull" | "bear" | "range" | "high_vol" | "crisis"
    urgency: str                # "low" | "medium" | "high" | "critical"

    # For decisions
    decision_type: str | None   # "buy" | "sell" | "hold" | "size_change" | "watchlist"
    decision_rationale: str | None
    decision_outcome: str | None  # filled later: "good" | "bad" | "neutral" | "pending"

    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class MarketContext:
    """Snapshot of market conditions at a point in time."""
    context_id: str             # UUID
    date: str
    # Major indices
    shanghai_composite: float
    csi300: float
    sse_star: float             # 科创50
    sp500: float
    nasdaq: float
    hang_seng: float

    # Macro
    cpi_yoy: float | None
    pmi_mfg: float | None
    lpr_1y: float | None
    us10y_yield: float | None
    vix: float | None

    # Regime signals
    regime_label: str           # "risk_on" | "risk_off" | "rotation" | "sector_dispersion"
    breadth_pct: float          # % stocks above 50-day MA
    volume_ratio: float         # current vs 20-day average

    created_at: str
```

### 5.4 Memory Operations

```
┌──────────────────────────────────────────────────────────┐
│                  Memory Engine API                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  CREATE:  Thesis → register memory                       │
│           Decision → log to journal                      │
│           Observation → log to journal                   │
│           Lesson → log as lesson entry                   │
│                                                          │
│  READ:    memory.search("growth stocks Q1 2026")         │
│           memory.get_by_thesis(thesis_id)                │
│           memory.get_outcomes(symbol="000858")           │
│           journal.query(type="lesson", tag="position_sizing") │
│                                                          │
│  UPDATE:  memory.review(thesis_id, outcome, notes)       │
│           journal.update_outcome(entry_id, outcome)       │
│           memory.attach_report(memory_id, report_path)    │
│                                                          │
│  ANALYZE: memory.calibration() → conviction vs accuracy │
│           memory.hit_rate(period="6m") → thesis accuracy │
│           journal.decision_quality() → decision review   │
│           journal.mood_correlation() → mood vs returns   │
│           memory.factor_style_performance() → what works │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 5.5 Memory Analytics Dashboard

| Metric | Formula | Purpose |
|--------|---------|---------|
| **Thesis Hit Rate** | correct / total (by time window) | How accurate are your theses? |
| **Conviction Calibration** | high-conviction hit rate vs low-conviction | Are you properly calibrated? |
| **Decision Win Rate** | profitable exits / total exits | Trading decision quality |
| **Thesis-to-Decision Lag** | avg days from thesis to first trade | Action orientation |
| **Review Cadence** | days since last review per active thesis | Discipline tracking |
| **Factor Style P&L** | cumulative return by factor category | What styles work for you? |
| **Mood-Return Correlation** | scatter: mood at entry vs subsequent return | Emotional awareness |
| **Lesson Density** | lessons per month | Learning velocity |

### 5.6 Database: `investment_memory.db`

```sql
-- Research memory
CREATE TABLE research_memory (
    memory_id TEXT PRIMARY KEY,
    project_id TEXT,
    thesis_id INTEGER NOT NULL REFERENCES research_notes(id),
    original_text TEXT NOT NULL,
    parsed_thesis TEXT,           -- JSON
    factor_model TEXT,            -- JSON
    strategy_spec TEXT,           -- JSON
    backtest_result TEXT,         -- JSON
    ai_assessment TEXT,           -- JSON
    report_path TEXT,
    conviction_score REAL CHECK(conviction_score >= 0 AND conviction_score <= 1),
    conviction_rationale TEXT,
    outcome_status TEXT DEFAULT 'pending',
    realized_return REAL,
    benchmark_return REAL,
    outcome_notes TEXT,
    reviewed_at TEXT,
    tags TEXT DEFAULT '[]',       -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT
);

-- Journal entries
CREATE TABLE journal_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    entry_type TEXT NOT NULL CHECK(entry_type IN (
        'observation','decision','lesson','review','daily_note'
    )),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    symbols TEXT DEFAULT '[]',    -- JSON array
    tags TEXT DEFAULT '[]',       -- JSON array
    related_thesis_ids TEXT DEFAULT '[]',
    related_memory_ids TEXT DEFAULT '[]',
    related_journal_ids TEXT DEFAULT '[]',
    mood TEXT,
    market_regime TEXT,
    urgency TEXT DEFAULT 'low',
    decision_type TEXT,
    decision_rationale TEXT,
    decision_outcome TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

-- Market context snapshots
CREATE TABLE market_contexts (
    context_id TEXT PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    shanghai_composite REAL,
    csi300 REAL,
    sse_star REAL,
    sp500 REAL,
    nasdaq REAL,
    hang_seng REAL,
    cpi_yoy REAL,
    pmi_mfg REAL,
    lpr_1y REAL,
    us10y_yield REAL,
    vix REAL,
    regime_label TEXT,
    breadth_pct REAL,
    volume_ratio REAL,
    created_at TEXT NOT NULL
);

-- Indices
CREATE INDEX idx_memory_project ON research_memory(project_id);
CREATE INDEX idx_memory_thesis ON research_memory(thesis_id);
CREATE INDEX idx_memory_outcome ON research_memory(outcome_status);
CREATE INDEX idx_memory_created ON research_memory(created_at);
CREATE INDEX idx_journal_date ON journal_entries(date);
CREATE INDEX idx_journal_type ON journal_entries(entry_type);
CREATE INDEX idx_journal_mood ON journal_entries(mood);
CREATE INDEX idx_journal_decision ON journal_entries(decision_outcome);
CREATE INDEX idx_market_date ON market_contexts(date);

-- Full-text search
CREATE VIRTUAL TABLE memory_fts USING fts5(
    original_text, conviction_rationale, outcome_notes, tags,
    content='research_memory', content_rowid='rowid'
);
CREATE VIRTUAL TABLE journal_fts USING fts5(
    title, content, tags,
    content='journal_entries', content_rowid='rowid'
);
```

---

## 6. Research Agent Framework

### 6.1 Purpose

V2's AI pipeline is a **single-pass processor**: input thesis → output report. V3's Research Agent Framework is a **persistent multi-agent system** where specialized agents collaborate, compete, and learn over time. Agents are scheduled, event-triggered, or manually invoked — each with its own memory scope and tool access.

### 6.2 Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                            │
│  Scheduling · Dispatch · Monitoring · Conflict Resolution        │
├──────────┬──────────┬──────────┬──────────┬─────────────────────┤
│          │          │          │          │                     │
│  Alpha   │  Risk    │  Fundam. │  Sentim. │  Custom Agents      │
│  Agent   │  Agent   │  Agent   │  Agent   │  (User-defined)     │
│          │          │          │          │                     │
├──────────┴──────────┴──────────┴──────────┴─────────────────────┤
│                    Agent Base Class                              │
│  schedule · memory_scope · tools · guardrails · output_schema    │
├──────────────────────────────────────────────────────────────────┤
│                    Tool Library                                   │
│  Market Data · Factor Calc · Backtest · Fundamental · News ·     │
│  Portfolio · Journal · Report · Web Search · File I/O             │
└──────────────────────────────────────────────────────────────────┘
```

### 6.3 Standard Agent Types

#### 6.3.1 Alpha Agent (Idea Generation)

```
Purpose:    Continuously scan for investment opportunities
Schedule:   Daily after market close (configurable)
Input:      Market data, factor signals, fundamental changes, news flow
Processing: Screen → Filter → Score → Rank → Generate thesis draft
Output:     Ranked list of ThesisProposal objects (score, rationale, risks)
Memory:     Tracks all generated proposals, learns from outcomes
Tools:      factor_screener, fundamental_screener, news_analyzer,
            technical_scanner, peer_comparator
```

**Screening Pipeline:**

```
Universe (5000+ A-shares)
    │
    ├── Liquidity Filter: avg daily volume > ¥50M, market cap > ¥5B
    ├── Factor Screen: composite score from selected factor categories
    ├── Fundamental Filter: ROE > 0, debt/equity < threshold, no ST/PT
    ├── Technical Filter: above 200-day MA, not overbought
    ├── Catalyst Check: upcoming earnings, policy event, industry news
    │
    ▼
Shortlist (20–50 candidates)
    │
    ▼
Deep Dive → Thesis Proposal (3–10 per run)
```

#### 6.3.2 Risk Agent (Portfolio Surveillance)

```
Purpose:    Monitor portfolio risk and alert on breaches
Schedule:   Continuous (intraday) + daily close
Input:      Positions, market data, correlations, stress scenarios
Processing: Risk decomposition → limit check → scenario analysis → recommendation
Output:     RiskReport, Alert objects, suggested position adjustments
Memory:     Risk event log, breach history, adjustment effectiveness
Tools:      var_calculator, correlation_matrix, stress_tester,
            position_sizer, liquidity_checker
```

**Risk Dashboard:**

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| Portfolio VaR (95%) | > 5% of NAV | Suggest hedge / reduce |
| Single position concentration | > 20% | Alert + rebalancing suggestion |
| Sector concentration | > 40% | Alert + diversification plan |
| Correlation matrix change | > 0.2 shift | Flag regime change |
| Max drawdown (rolling) | > 15% from peak | Suggest stop-loss review |
| Liquidity ratio | Position > 5% of ADV | Sizing warning |

#### 6.3.3 Fundamental Agent (Deep Dive)

```
Purpose:    Perform comprehensive fundamental analysis on a target
Trigger:    Manual (user request) or scheduled (earnings season)
Input:      Stock symbol, lookback period
Processing: Financial statement analysis → peer comparison → DCF model →
            quality assessment → fair value range
Output:     FundamentalReport (40+ pages), FairValueEstimate, RiskFlags
Memory:     Historical valuations, forecast accuracy tracking
Tools:      financial_fetcher, dupont_analyzer, dcf_model,
            peer_comparator, quality_scorer, sensitivity_analyzer
```

#### 6.3.4 Sentiment Agent (Market Pulse)

```
Purpose:    Aggregate and analyze market sentiment from multiple sources
Schedule:   Daily + event-triggered
Input:      News feeds, social media, analyst reports, fund flows, options
Processing: NLP sentiment → source weighting → anomaly detection → signal
Output:     SentimentDashboard, AnomalyAlert, ContrarianSignal
Memory:     Sentiment history, extreme-reading follow-up tracking
Tools:      news_scraper, nlp_sentiment, fund_flow_analyzer,
            analyst_consensus, fear_greed_index
```

#### 6.3.5 Custom Agent (User-Defined)

```python
# Users define agents via a declarative spec
from lxl_quantaxis.agents import AgentSpec, Schedule, ToolGrant

my_agent = AgentSpec(
    name="Consumer Recovery Scanner",
    description="Scan consumer sector for post-pandemic recovery plays",
    schedule=Schedule(cron="30 15 * * 1-5", timezone="Asia/Shanghai"),  # 3:30pm weekdays
    tools=[
        ToolGrant("factor_screener", params={"categories": ["momentum", "volume"]}),
        ToolGrant("fundamental_fetcher", params={"industry": "consumer"}),
        ToolGrant("peer_comparator"),
    ],
    prompt_template="consumer_recovery_v1",
    output_schema=ThesisProposal,
    memory_scope=["consumer_sector", "recovery_theme"],
    guardrails={
        "max_positions_per_run": 5,
        "min_market_cap_billion": 10,
        "exclude_st_flag": True,
    },
)
```

### 6.4 Agent Safety Framework

Every agent operates within a **layered safety envelope**:

```
Layer 1: Tool Access Control
    ├── Allowlist of permitted tools per agent type
    ├── Parameter constraints (e.g., max symbols, max lookback)
    └── Rate limiting (calls per minute, data volume per hour)

Layer 2: Output Validation
    ├── Schema validation against Pydantic models
    ├── Value range checks (e.g., confidence 0–1, weights sum to 1)
    ├── Sanity checks (e.g., can't recommend both buy and sell for same stock)
    └── Cross-agent conflict detection

Layer 3: Execution Guardrails
    ├── Max positions per run (prevents flood of trades)
    ├── Max notional exposure per recommendation
    ├── Cooldown period between contradictory signals
    └── Human confirmation required for trading actions

Layer 4: Audit & Monitoring
    ├── Every agent action logged to audit trail
    ├── Agent performance metrics tracked
    ├── Anomaly detection on agent output patterns
    └── Manual override and kill switch
```

### 6.5 Agent Orchestration

```
Orchestrator
├── Scheduler
│   ├── Cron-based: "every weekday at 15:30 CST"
│   ├── Event-triggered: "on market close", "on earnings release"
│   ├── Conditional: "if VIX > 30", "if portfolio drawdown > 10%"
│   └── Manual: user-invoked via workspace or API
│
├── Dispatcher
│   ├── Agent lifecycle: start, monitor, timeout, retry, terminate
│   ├── Resource allocation: max concurrent agents, priority queue
│   └── Dependency resolution: Agent B runs only after Agent A completes
│
├── Conflict Resolver
│   ├── Detect: two agents recommend contradictory actions
│   ├── Escalate: surface conflict to user with context
│   └── Resolve: apply confidence-weighted voting if auto-resolution enabled
│
└── Performance Tracker
    ├── Per-agent accuracy metrics (thesis hit rate, signal quality)
    ├── Agent comparison (which agent produces best recommendations?)
    └── Adaptive weighting (upweight historically accurate agents)
```

### 6.6 Python Module Structure

```
src/lxl_quantaxis/agents/
├── __init__.py
├── base.py                    # BaseAgent ABC, AgentContext, AgentResult
├── orchestrator.py            # AgentOrchestrator: schedule, dispatch, monitor
├── scheduler.py               # Cron, event, conditional scheduling
├── registry.py                # Agent type registry + discovery
├── tools/
│   ├── __init__.py
│   ├── base.py                # AgentTool base class
│   ├── market_data.py         # get_price, get_volume, get_index
│   ├── factor_tools.py        # compute_factor, screen_factors, factor_ranking
│   ├── fundamental_tools.py   # get_financials, get_metrics, peer_compare
│   ├── backtest_tools.py      # quick_backtest, strategy_validate
│   ├── portfolio_tools.py     # get_positions, get_pnl, risk_decompose
│   ├── journal_tools.py       # search_memory, log_observation, find_lessons
│   ├── news_tools.py          # search_news, sentiment_analysis, event_detect
│   └── report_tools.py        # generate_report, format_output
├── agents/
│   ├── __init__.py
│   ├── alpha_agent.py         # Idea generation & screening
│   ├── risk_agent.py          # Portfolio surveillance
│   ├── fundamental_agent.py   # Deep fundamental analysis
│   ├── sentiment_agent.py     # Market sentiment monitoring
│   └── custom_agent.py        # User-defined agent runtime
├── safety/
│   ├── __init__.py
│   ├── tool_acl.py            # Tool access control lists
│   ├── output_validator.py    # Schema + sanity validation
│   ├── guardrails.py          # Execution guardrails
│   └── conflict_detector.py   # Cross-agent conflict detection
├── memory/
│   ├── __init__.py
│   ├── agent_memory.py        # Per-agent memory scope
│   └── shared_memory.py       # Cross-agent shared context
└── specs/
    ├── __init__.py
    └── templates/             # Pre-built agent specification templates
        ├── growth_scanner.yaml
        ├── value_hunter.yaml
        ├── momentum_chaser.yaml
        └── risk_monitor.yaml
```

---

## 7. Backtesting Engine V3

### 7.1 Purpose

V2's backtesting engine is single-asset, single-frequency, single-currency. V3 upgrades to a **production-grade, multi-asset, multi-frequency backtesting engine** with point-in-time data awareness, realistic cost modeling, and institutional-grade analytics.

### 7.2 Capability Comparison

| Feature | V2 Engine | V3 Engine |
|---------|-----------|-----------|
| **Assets** | Single stock | Multi-asset portfolio (stocks, ETFs, indices) |
| **Frequency** | Daily only | Tick, minute, hourly, daily, weekly |
| **Data** | Adjusted close | Point-in-time (no look-ahead bias) |
| **Cost Model** | Simple (commission + stamp) | Full: commission, stamp, slippage, market impact, funding |
| **Execution** | Next-bar fill | Configurable fill models (limit, market, VWAP, Almgren-Chriss) |
| **Corporate Actions** | None | Dividends, splits, rights issues, delistings |
| **Benchmarks** | Single (CSI 300) | Multiple + custom composite |
| **Risk Model** | Basic (VaR only) | Multi-factor risk decomposition |
| **Stress Testing** | None | Historical scenarios + custom shocks |
| **Portfolio Constraints** | None | Position limits, sector limits, leverage, turnover |
| **Optimization** | Grid + Walk-forward | + Bayesian, genetic algorithm, CVaR optimization |
| **Persistence** | SQLite only | SQLite + PostgreSQL, result versioning |

### 7.3 Architecture

```
Backtesting Engine V3
├── Data Portal (Point-in-Time)
│   ├── PITDataPortal: ensures no look-ahead bias
│   ├── AdjustmentService: handles corporate actions correctly
│   ├── BenchmarkPortal: multi-benchmark data access
│   └── FundamentalPortal: PIT fundamental data
│
├── Execution Simulator
│   ├── FillModel ABC
│   │   ├── NextBarFill (T+1 close)
│   │   ├── LimitOrderFill (price must cross limit)
│   │   ├── VWAPFill (volume-weighted average price)
│   │   ├── MarketImpactFill (Almgren-Chriss model)
│   │   └── CustomFill (user-defined)
│   ├── SlippageModel: fixed, proportional, volatility-scaled
│   ├── CostModel: commission, stamp duty, transfer fee, financing
│   └── LiquidityModel: max position = f(ADV, market cap, float)
│
├── Portfolio Manager
│   ├── MultiAccountPortfolio: sub-accounts, currencies
│   ├── ConstraintChecker: position limits, sector caps, leverage
│   ├── RebalanceEngine: calendar-based, threshold-based, signal-based
│   └── CorporateActionHandler: dividends, splits, mergers, delistings
│
├── Risk Engine
│   ├── FactorModel: Barra-style multi-factor risk decomposition
│   ├── VaR: parametric, historical, Monte Carlo
│   ├── StressTester: 2008, 2015, 2020, COVID scenarios + custom
│   ├── GreeksCalculator: delta, gamma, theta (for options)
│   └── LiquidityRisk: time-to-liquidate, market impact estimation
│
├── Analytics Engine
│   ├── PerformanceMetrics: 40+ metrics (Sharpe, Sortino, Calmar, Omega, etc.)
│   ├── AttributionAnalysis: Brinson, factor-based, sector-based
│   ├── RegimeAnalysis: performance by market regime
│   ├── TurnoverAnalysis: cost of trading, tax efficiency
│   └── PeerComparison: strategy vs universe of strategies
│
├── Optimization Engine
│   ├── ParameterOptimizer: Grid, Random, Bayesian (GP), Genetic
│   ├── WalkForwardOptimizer: anchored vs rolling, Purged K-Fold
│   ├── PortfolioOptimizer: Mean-Variance, CVaR, Risk Parity, HRP
│   └── MultiObjectiveOptimizer: Sharpe + max drawdown + turnover
│
└── Result Store
    ├── ResultRepository: versioned backtest results
    ├── ComparisonEngine: side-by-side strategy comparison
    ├── Serializer: JSON, Parquet, Protocol Buffers
    └── CacheLayer: avoid redundant computation
```

### 7.4 Point-in-Time Data Model

The critical innovation for V3: eliminating look-ahead bias through proper PIT data management.

```
Traditional (V2):
  data = get_data("2020-01-01", "2024-12-31")  # adjusted close prices
  backtest(data)                                  # Uses future-adjusted prices!

PIT (V3):
  data_portal = PITDataPortal(
      symbols=["000858"],
      start="2020-01-01", end="2024-12-31",
  )
  # On bar date 2021-03-15:
  # - Price: closing price AS KNOWN on 2021-03-15 (not adjusted later)
  # - Fundamentals: latest quarterly report FILED by 2021-03-15
  # - Corporate actions: only events ANNOUNCED by 2021-03-15
  # - Index membership: constituents AS OF 2021-03-15
  backtest(data_portal)  # No look-ahead bias
```

**Implementation:**

```python
# src/lxl_quantaxis/backtest/pit_portal.py

class PITDataPortal:
    """Ensures no look-ahead bias in backtesting."""

    def get_price(self, symbol, date):
        """Return price as known on `date` (unadjusted close for that day)."""
        ...

    def get_fundamentals(self, symbol, date):
        """Return latest fundamentals filed by `date`, accounting for reporting lag."""
        ...

    def get_index_members(self, index, date):
        """Return index constituents as of `date`."""
        ...

    def get_corporate_actions(self, symbol, start, end):
        """Return all corporate actions in range for correct adjustment."""
        ...

    def adjust_for_split(self, price_series, actions):
        """Forward-adjust only for splits known at each point."""
        ...
```

### 7.5 Event Loop V3

```
┌──────────────────────────────────────────────────────────┐
│                   Event Loop V3                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  for each bar_date in trading_calendar:                   │
│    │                                                     │
│    ├── 1. Update Universe                                │
│    │      Apply survivorship filter (PIT)                │
│    │      Remove delisted/ST stocks                       │
│    │                                                     │
│    ├── 2. Process Corporate Actions                       │
│    │      Dividends → adjust cash                        │
│    │      Splits → adjust position size                  │
│    │      Mergers → replace or liquidate                 │
│    │                                                     │
│    ├── 3. Mark-to-Market                                 │
│    │      Price all positions at PIT prices              │
│    │      Update portfolio NAV                            │
│    │                                                     │
│    ├── 4. Check Risk Limits                              │
│    │      VaR, leverage, concentration                   │
│    │      Generate alerts on breach                      │
│    │                                                     │
│    ├── 5. Run Strategy                                   │
│    │      strategy.on_bar(i, pit_data, portfolio)        │
│    │      Generate list of Orders                        │
│    │                                                     │
│    ├── 6. Validate Orders                                │
│    │      Check against constraints                      │
│    │      Apply position limits, sector caps             │
│    │                                                     │
│    ├── 7. Execute Orders                                 │
│    │      Apply fill model                               │
│    │      Apply slippage + cost model                    │
│    │      Update portfolio cash + positions              │
│    │                                                     │
│    ├── 8. Record State                                   │
│    │      Save daily snapshot: positions, NAV, metrics   │
│    │      Emit events: fill, signal, risk alert          │
│    │                                                     │
│    └── 9. Advance Clock                                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 7.6 Python Module Structure

```
src/lxl_quantaxis/backtest/
├── __init__.py
├── pit_portal.py              # Point-in-time data portal
├── event_loop.py              # V3 event loop (enhanced from V2)
├── engine/
│   ├── __init__.py
│   ├── event_loop.py          # (V2, kept for compatibility)
│   └── v3_loop.py             # V3 multi-asset loop
├── execution/
│   ├── __init__.py
│   ├── fill_models.py         # (V2, kept)
│   ├── v3_fills.py            # V3: limit, VWAP, impact, custom
│   ├── slippage.py            # SlippageModel hierarchy
│   └── costs.py               # Full cost model (commission, stamp, funding)
├── portfolio_v3/
│   ├── __init__.py
│   ├── multi_account.py       # Multi-account, multi-currency portfolio
│   ├── constraints.py         # Position, sector, leverage constraints
│   ├── rebalance.py           # Rebalancing strategies
│   └── corporate_actions.py   # Handle dividends, splits, mergers
├── risk/
│   ├── __init__.py
│   ├── factor_model.py        # Barra-style multi-factor risk
│   ├── var.py                 # Parametric, historical, Monte Carlo VaR
│   ├── stress.py              # Scenario-based stress testing
│   └── greeks.py              # Options Greeks (Phase 2)
├── analytics/
│   ├── __init__.py
│   ├── metrics.py             # 40+ performance metrics
│   ├── attribution.py         # Brinson + factor-based attribution
│   ├── regime.py              # Regime-conditional analysis
│   └── turnover.py            # Trading cost analysis
├── optimization/
│   ├── __init__.py
│   ├── bayesian.py            # Bayesian optimization (GP)
│   ├── genetic.py             # Genetic algorithm
│   ├── walkforward.py         # Enhanced walk-forward (Purged K-Fold)
│   └── portfolio_opt.py       # Portfolio-level optimization
└── results/
    ├── __init__.py
    ├── repository.py          # Versioned result storage
    ├── comparison.py          # Multi-strategy comparison
    └── serialization.py       # JSON, Parquet, protobuf
```

---

## 8. Report Generation System

### 8.1 Purpose

V2 generates Markdown and HTML reports from a single template. V3 introduces a **multi-format, multi-audience, multi-channel report generation system** — from one-page executive briefs to 50+ page institutional research reports.

### 8.2 Report Architecture

```
Report Generation System
├── Data Aggregation Layer
│   ├── Gatherer: collects data from all sources
│   ├── Normalizer: standardizes to common schema
│   └── Enricher: adds computed metrics, context, benchmarks
│
├── Template Engine
│   ├── TemplateRegistry: Jinja2 templates by report type
│   ├── ComponentLibrary: reusable report components (tables, charts, callouts)
│   └── StyleSystem: consistent typography, colors, branding
│
├── Rendering Pipeline
│   ├── MarkdownRenderer: GitHub-flavored Markdown
│   ├── HTMLRenderer: responsive, print-friendly, dark mode
│   ├── PDFRenderer: WeasyPrint/Puppeteer-based
│   ├── JSONRenderer: structured data for API consumers
│   └── ExcelRenderer: data tables for further analysis
│
├── Report Types
│   ├── ExecutiveBrief: 1-page summary for quick decisions
│   ├── InvestmentMemo: 3-5 page investment case
│   ├── ResearchReport: 25+ pages, institutional format
│   ├── DailyBrief: automated daily market + portfolio summary
│   ├── WeeklyStrategy: weekly review + outlook
│   ├── BacktestReport: comprehensive strategy analysis
│   ├── RiskReport: portfolio risk decomposition
│   └── CustomReport: user-defined template + data sources
│
└── Distribution
    ├── Web: embedded in workspace UI
    ├── Email: scheduled delivery (Phase 2)
    ├── Export: PDF, HTML, Markdown download
    └── API: programmatic access to report data
```

### 8.3 Report Type Specifications

#### 8.3.1 Executive Brief (1 page)

```yaml
audience: Portfolio Manager, quick decision support
sections:
  - header: "Stock | Recommendation | Target Price | Confidence"
  - investment_thesis: "3-bullet summary"
  - catalysts: "Upcoming events (earnings, policy, product)"
  - risks: "Top 3 risks with mitigation"
  - valuation_snapshot: "PE vs history, vs peers, DCF range"
  - technical_snapshot: "Trend, momentum, support/resistance"
  - action: "Buy/Sell/Hold | Position size | Entry zone | Stop loss"
template: brief_1p.jinja2
```

#### 8.3.2 Investment Memo (3-5 pages)

```yaml
audience: Investment Committee, detailed case
sections:
  - executive_summary
  - company_overview: "Business model, competitive position, management"
  - industry_analysis: "Market structure, growth drivers, competitive dynamics"
  - investment_thesis: "Detailed bull case with evidence"
  - financial_analysis: "Key metrics, trends, quality assessment"
  - valuation: "DCF summary, comps table, scenario analysis"
  - risk_assessment: "Risk matrix with probability and impact"
  - recommendation: "Position sizing, entry strategy, exit plan"
template: memo_5p.jinja2
```

#### 8.3.3 Institutional Research Report (25+ pages)

```yaml
audience: Research distribution, comprehensive analysis
sections:
  - cover_page
  - table_of_contents
  - executive_summary: "2-page standalone summary"
  - investment_case:
      - bull_case: "Detailed scenario with catalysts and timeline"
      - base_case: "Most likely scenario with probability weighting"
      - bear_case: "What could go wrong and how to monitor"
  - industry_analysis:
      - value_chain: "Supply chain map with company positioning"
      - competitive_landscape: "Porter's Five Forces, market share data"
      - growth_drivers: "Secular trends, cyclical factors, policy tailwinds"
  - company_analysis:
      - business_model: "Revenue streams, unit economics, moat assessment"
      - management: "Track record, incentives, capital allocation"
      - strategy: "Growth strategy, M&A history, R&D pipeline"
  - financial_analysis:
      - three_statement_model: "Historical + 3-year forecast"
      - dupont_decomposition: "ROE drivers and trends"
      - quality_check: "Accruals, cash conversion, earnings quality"
      - capital_structure: "Leverage, liquidity, refinancing risk"
  - valuation:
      - dcf_model: "Detailed assumptions, WACC, terminal value"
      - comparable_companies: "Peer group, valuation multiples table"
      - precedent_transactions: "Relevant M&A comps"
      - scenario_analysis: "Bull/Base/Bear with probability weights"
      - sensitivity_tables: "Revenue growth × Margin, WACC × Terminal growth"
  - technical_analysis:
      - price_structure: "Long-term trend, key levels, pattern analysis"
      - factor_profile: "28-factor radar chart with historical context"
      - volume_analysis: "Accumulation/distribution, institutional flow"
  - risk_analysis:
      - risk_matrix: "Probability × Impact for top 10 risks"
      - tail_risks: "Black swan scenarios, stress test results"
      - monitoring_framework: "Key indicators to watch, tripwires"
  - recommendation:
      - rating: "Buy/Hold/Sell with conviction level"
      - target_price: "12-month with upside/downside scenarios"
      - position_sizing: "Kelly, risk parity, or fixed-fraction"
      - execution_plan: "Entry zones, scaling, stop-loss levels"
  - appendix:
      - data_sources: "All data provenance"
      - methodology: "Valuation methodology detail"
      - disclaimer: "Standard research disclaimer"
template: institutional_25p.jinja2
```

#### 8.3.4 Daily Brief (automated)

```yaml
audience: Self, daily review
schedule: Generated automatically at 16:00 CST each trading day
sections:
  - market_summary: "Major indices, breadth, volume, sector performance"
  - portfolio_snapshot: "P&L, positions, risk metrics vs limits"
  - signal_summary: "Today's generated signals, ranked by conviction"
  - agent_activity: "What agents ran today, key outputs"
  - news_highlights: "Top 5 market-moving headlines for your watchlist"
  - upcoming: "Tomorrow's events: earnings, economic data, expirations"
  - journal_prompt: "Empty journal template for end-of-day reflection"
template: daily_brief.jinja2
```

### 8.4 Template System

```
templates/
├── base/
│   ├── base.html.jinja2          # HTML base with nav, footer, styles
│   ├── base.md.jinja2            # Markdown base with frontmatter
│   └── base.pdf.css              # Print CSS for PDF generation
│
├── components/
│   ├── metric_tile.jinja2        # KPI display tile
│   ├── comparison_table.jinja2   # Peer comparison table
│   ├── factor_radar.jinja2       # Factor radar chart (Plotly)
│   ├── price_chart.jinja2        # Price + volume + indicators chart
│   ├── risk_matrix.jinja2        # Risk heatmap
│   ├── scenario_table.jinja2     # Bull/Base/Bear scenario table
│   ├── water_fall.jinja2         # Return attribution waterfall
│   ├── timeline.jinja2           # Event/catalyst timeline
│   └── callout.jinja2            # Emphasis box (key insight, warning, etc.)
│
├── reports/
│   ├── brief_1p.jinja2           # Executive brief
│   ├── memo_5p.jinja2            # Investment memo
│   ├── institutional_25p.jinja2  # Full research report
│   ├── daily_brief.jinja2        # Daily automated brief
│   ├── weekly_strategy.jinja2    # Weekly review
│   ├── backtest.jinja2           # Backtest analysis report
│   ├── risk_report.jinja2        # Portfolio risk report
│   └── custom.jinja2             # User-customizable template
│
└── styles/
    ├── lxl_theme.css             # LXL brand styles
    ├── dark_mode.css             # Dark mode overrides
    ├── print.css                 # Print-optimized styles
    └── email.css                 # Email-safe inline styles
```

### 8.5 Python Module Structure

```
src/lxl_quantaxis/report/
├── __init__.py
├── generator.py                # ReportGenerator: main entry point
├── gatherer.py                 # DataGatherer: aggregate from all sources
├── normalizer.py               # DataNormalizer: standardize to common schema
├── enricher.py                 # DataEnricher: add computed metrics
├── engine/
│   ├── __init__.py
│   ├── jinja2_engine.py        # Jinja2 template rendering
│   ├── plotly_engine.py        # Chart/image generation
│   └── pdf_engine.py           # PDF conversion (WeasyPrint/Puppeteer)
├── types/
│   ├── __init__.py
│   ├── base.py                 # BaseReport ABC
│   ├── brief.py                # ExecutiveBrief
│   ├── memo.py                 # InvestmentMemo
│   ├── institutional.py        # InstitutionalReport
│   ├── daily.py                # DailyBrief
│   ├── weekly.py               # WeeklyStrategy
│   ├── backtest.py             # BacktestReport
│   └── risk.py                 # RiskReport
├── components/
│   ├── __init__.py
│   ├── tables.py               # Comparison tables, financial tables
│   ├── charts.py               # Plotly chart components
│   ├── metrics.py              # KPI tile generation
│   └── formatting.py           # Number/date/currency formatting
├── distribution/
│   ├── __init__.py
│   ├── web.py                  # Embed in workspace
│   ├── email_sender.py         # Email delivery (Phase 2)
│   └── export.py               # File download (PDF, HTML, MD, JSON)
└── scheduler/
    ├── __init__.py
    └── report_jobs.py          # Scheduled report generation
```

---

## 9. Data Architecture

### 9.1 Data Fabric Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Catalog                              │
│  Registry of all available datasets with metadata, lineage,      │
│  freshness, quality scores, and access patterns                   │
├──────────┬──────────┬──────────┬──────────┬──────────────────────┤
│ Market   │ Fundam.  │ Macro    │ Alt Data │ Derived Data          │
│ Data     │ Data     │ Data     │          │ Factors, Signals,     │
│ Providers│ Providers│ Providers│ Providers│ Analytics              │
├──────────┴──────────┴──────────┴──────────┴──────────────────────┤
│                     Quality Gate Layer                            │
│  Validation · Reconciliation · Completeness · Timeliness ·        │
│  Outlier Detection · Staleness Monitoring                         │
├──────────────────────────────────────────────────────────────────┤
│                     Storage Layer                                 │
│  Hot: Redis (real-time) · Warm: SQLite/PostgreSQL (structured)    │
│  Cold: Parquet files (historical) · Archive: compressed CSV       │
├──────────────────────────────────────────────────────────────────┤
│                     Provider Abstraction                          │
│  Uniform interface: get_market_data(), get_fundamentals(),         │
│  get_macro(), get_news() → each with fallback chain               │
└──────────────────────────────────────────────────────────────────┘
```

### 9.2 Database Inventory (V3)

| Database | Engine | Contents | New/Existing |
|----------|--------|----------|--------------|
| `trades.db` | SQLite | Trade journal (buy/sell records) | Existing (V1) |
| `backtest_results.db` | SQLite | Backtest results, rankings | Existing (V1) |
| `research_notes.db` | SQLite | Research notes, theses | Existing (V2) |
| `strategy_catalog.db` | SQLite | Strategy definitions, specs | Existing (V2) |
| `factor_analysis.db` | SQLite | Factor IC, decay, correlation | Existing (V2) |
| `portfolio_analytics.db` | SQLite | Portfolio performance, allocation | Existing (V2) |
| `data_catalog.db` | SQLite | Data source registry, lineage | Existing (V2) |
| `quality_metrics.db` | SQLite | Data quality scores, incidents | Existing (V2) |
| `financial_series.db` | SQLite | Time series of financial metrics | Existing (V2) |
| `market_metadata.db` | SQLite | Symbol metadata, calendars | Existing (V2) |
| `investment_memory.db` | SQLite | Research memory, journal, context | **New (V3)** |
| `fundamental.db` | SQLite | Financial statements, peer data | **New (V3)** |
| `macro_series.db` | SQLite | Macro indicators, policy data | **New (V3)** |
| `agent_state.db` | SQLite | Agent configurations, run history | **New (V3)** |
| `audit_trail.db` | SQLite | System audit log | **New (V3)** |
| `scheduled_jobs.db` | SQLite | Cron jobs, triggers, schedules | **New (V3)** |
| `report_archive.db` | SQLite | Generated reports, templates | **New (V3)** |
| `pit_data.db` | SQLite/Parquet | Point-in-time market data | **New (V3)** |

### 9.3 Data Quality Framework

Every dataset entering the system passes through quality gates:

```python
@dataclass(frozen=True, slots=True)
class DataQualityReport:
    dataset_id: str
    checked_at: str

    completeness: float        # 0–1: expected rows / actual rows
    freshness: float           # 0–1: 1.0 if within staleness threshold
    accuracy: float            # 0–1: cross-source reconciliation score
    consistency: float         # 0–1: internal consistency checks passed
    outlier_count: int         # number of statistical outliers detected
    gap_count: int             # number of missing periods
    is_stale: bool             # exceeds freshness threshold
    quality_score: float       # composite 0–100

    issues: list[DataQualityIssue]
```

**Quality Actions:**

| Quality Score | Action |
|---------------|--------|
| 90–100 | Accept, cache |
| 70–89 | Accept with warning, attempt repair |
| 50–69 | Accept with error flag, notify user |
| 0–49 | Reject, fall back to alternative source |

---

## 10. API & Integration Layer

### 10.1 API Gateway

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                      │
│                                                              │
│  /api/v3/                                                    │
│  ├── /agents/          Agent management & invocation         │
│  ├── /backtest/        Backtest execution & results          │
│  ├── /fundamental/     Fundamental data access               │
│  ├── /journal/         Journal entries & memory              │
│  ├── /portfolio/       Portfolio analytics                   │
│  ├── /report/          Report generation & download          │
│  ├── /research/        Research pipeline (V2 compat)         │
│  ├── /workspace/       Project management                    │
│  ├── /admin/           System administration                 │
│  └── /events/          WebSocket event stream                │
│                                                              │
│  Middleware:                                                 │
│  ├── Authentication (JWT, API keys)                          │
│  ├── Authorization (RBAC)                                    │
│  ├── Rate Limiting (token bucket per user)                   │
│  ├── Request Validation (Pydantic)                           │
│  ├── Audit Logging (every mutation logged)                   │
│  ├── Telemetry (Prometheus metrics)                          │
│  └── CORS (configurable origins)                             │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 API Versioning Strategy

```
/api/v1/  → Legacy endpoints (src/api/legacy.py) — deprecated, read-only
/api/v2/  → V2 stable endpoints (src/lxl_quantaxis/api/) — maintained
/api/v3/  → V3 new endpoints — primary development target
```

### 10.3 Key API Endpoints (V3)

#### Agents

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v3/agents` | List available agent types |
| `POST` | `/api/v3/agents/{type}/run` | Trigger agent run |
| `GET` | `/api/v3/agents/runs` | List agent run history |
| `GET` | `/api/v3/agents/runs/{id}` | Get run details + output |
| `POST` | `/api/v3/agents/custom` | Create custom agent spec |
| `PUT` | `/api/v3/agents/custom/{id}` | Update custom agent |
| `DELETE` | `/api/v3/agents/custom/{id}` | Delete custom agent |

#### Backtest

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v3/backtest/run` | Run backtest (V3 engine) |
| `GET` | `/api/v3/backtest/results/{id}` | Get backtest result |
| `POST` | `/api/v3/backtest/compare` | Compare multiple backtests |
| `POST` | `/api/v3/backtest/optimize` | Run parameter optimization |
| `GET` | `/api/v3/backtest/metrics/{id}` | Get detailed metrics |

#### Fundamental

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v3/fundamental/{symbol}` | Latest fundamental snapshot |
| `GET` | `/api/v3/fundamental/{symbol}/series` | Historical series |
| `GET` | `/api/v3/fundamental/{symbol}/peers` | Industry peer comparison |
| `GET` | `/api/v3/fundamental/{symbol}/valuation` | DCF + comps valuation |
| `GET` | `/api/v3/macro/{indicator}` | Macro indicator series |

#### Journal & Memory

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v3/journal` | List journal entries (filtered) |
| `POST` | `/api/v3/journal` | Create journal entry |
| `GET` | `/api/v3/journal/{id}` | Get entry detail |
| `PUT` | `/api/v3/journal/{id}` | Update entry |
| `DELETE` | `/api/v3/journal/{id}` | Delete entry |
| `GET` | `/api/v3/memory/search` | Full-text search memory |
| `GET` | `/api/v3/memory/analytics` | Memory analytics dashboard |
| `GET` | `/api/v3/memory/{thesis_id}` | Thesis lifecycle memory |

#### Report

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v3/report/generate` | Generate report |
| `GET` | `/api/v3/report/{id}` | Get report metadata |
| `GET` | `/api/v3/report/{id}/download.{fmt}` | Download report file |
| `GET` | `/api/v3/report/templates` | List available templates |

---

## 11. Web Workspace V3

### 11.1 Design Principles

1. **Unified Shell**: Every page is part of a single application with consistent navigation
2. **Project Context**: All work happens within a Research Project context
3. **Real-time**: WebSocket events for live updates (agent status, signals, market data)
4. **Responsive**: Works on desktop (primary) and tablet (review)
5. **Dark Mode**: Full dark mode support with system preference detection
6. **Keyboard Driven**: Power users can navigate and execute via keyboard shortcuts

### 11.2 Page Architecture

```
Web Workspace V3
├── Shell
│   ├── Global Nav: Projects · Agents · Pipeline · Portfolio · Journal · Reports
│   ├── Project Switcher: dropdown to switch active project
│   ├── User Menu: settings, logout, help
│   └── Notification Center: agent alerts, signal notifications, system messages
│
├── Pages
│   ├── /                    Landing / Dashboard (project overview)
│   ├── /projects            Project list + create
│   ├── /project/:id         Project workspace (Kanban + resources)
│   ├── /agents              Agent management (status, history, create custom)
│   ├── /pipeline            AI Research Pipeline (V2 compatible)
│   ├── /portfolio           Portfolio analytics dashboard
│   ├── /journal             Investment journal (calendar + entries)
│   ├── /fundamental         Fundamental data explorer
│   ├── /backtest            Backtest configuration + results
│   ├── /reports             Report list + generate
│   ├── /memory              Memory analytics dashboard
│   └── /admin              System admin (users, schedules, audit)
│
└── Modals / Panels
    ├── Quick Thesis: write and submit a thesis from anywhere
    ├── Quick Backtest: configure + run without leaving current page
    ├── Journal Entry: log an observation/decision from anywhere
    └── Agent Output: view agent results inline
```

### 11.3 Technology Options

| Approach | Pros | Cons |
|----------|------|------|
| **HTMX + Jinja2** (continue V2 pattern) | Minimal JS, server-rendered, fast dev | Less interactive, no offline |
| **React SPA + FastAPI** | Rich interactivity, component library, real-time | More complex, separate build |
| **Hybrid: HTMX base + Alpine.js islands** | Progressive enhancement, low JS, fast | Limited for very interactive pages |

**Recommendation**: HTMX + Alpine.js for V3.0 MVP. The primary user is a single quant researcher. Rich interactivity via Plotly charts, real-time via WebSocket. Save React migration for when multi-user is needed.

---

## 12. Safety & Compliance

### 12.1 Safety Architecture (Enhanced from V2)

```
Layer 1: Input Safety
    ├── All user inputs sanitized (HTML escaping, SQL parameterization)
    ├── File uploads: type validation, size limits, virus scanning
    └── API requests: rate limiting, payload size limits, schema validation

Layer 2: AI Safety (Enhanced)
    ├── Agent output: schema-validated, value-range checked
    ├── DSL compilation: AST allowlist (NO imports, exec, eval)
    ├── Agent tools: per-agent ACL, parameter constraints
    ├── Cross-agent: conflict detection, contradictory signal suppression
    └── Human confirmation: required for any trading action

Layer 3: Data Safety
    ├── Parameterized queries: 100% (enforced by ruff rules)
    ├── Encryption at rest: SQLite with SQLCipher (optional)
    ├── PII handling: no PII stored by default
    └── Backup enforcement: automated daily backup with retention policy

Layer 4: Operational Safety
    ├── Kill switch: immediately halt all agents and scheduled jobs
    ├── Circuit breaker: auto-pause if error rate exceeds threshold
    ├── Rollback: all DB migrations are reversible
    └── Health checks: /health endpoint with dependency status

Layer 5: Audit Trail
    ├── Every mutation logged: who, what, when, from_where
    ├── Immutable log: append-only, no deletes
    ├── Retention: 7 years (configurable)
    └── Export: CSV/JSON for compliance review
```

### 12.2 Authentication & Authorization

```
Roles (RBAC):
├── admin:     Full system access, user management, system config
├── researcher: Create/edit theses, run pipelines, manage projects
├── analyst:   Read research, run backtests, view reports
└── viewer:    Read-only access to shared projects and reports

Auth Methods:
├── Password:  bcrypt hashed, minimum complexity enforced
├── JWT:       Access + refresh tokens, configurable expiry
├── API Key:   For programmatic access, scoped permissions
└── (Phase 2): OAuth2 (GitHub, Google), SSO
```

---

## 13. V2 Compatibility Guarantee

### 13.1 Non-Breaking Guarantees

| Contract | Detail |
|----------|--------|
| **V2 Python API** | All public classes/functions in `src/lxl_quantaxis/` keep same signatures |
| **V2 REST API** | `/api/v2/*` endpoints unchanged — deprecated gradually over 12 months |
| **V2 CLI** | `demo/demo_ai_research.py` produces identical output |
| **V2 Database** | All existing SQLite DBs untouched, new DBs are additive |
| **V2 Pipeline** | 7-stage pipeline runs identically, extended not replaced |
| **V2 DSL** | Strategy DSL syntax unchanged, compiler backward-compatible |
| **V2 Factors** | All 28 factors compute identically, new factors are additive |
| **V2 Config** | `config.yaml` format extended, old keys still valid |

### 13.2 Migration Path

```
V2.0.0 ────────────────► V3.0.0
  │                          │
  │  Existing V2 code        │  All V2 code still works
  │  runs unchanged          │  V3 modules are additive
  │                          │  New features opt-in
  │                          │
  └──────────────────────────┘
         Zero migration required

Deprecation timeline:
  V2 API endpoints:  deprecated 2027-Q1, removed 2027-Q3
  Legacy src/ modules: deprecated 2027-Q2, removed 2027-Q4
```

### 13.3 Testing Strategy

```
Test Categories:
├── V2 Regression: 400+ existing tests must pass (CI gate)
├── V2 Characterization: snapshot tests for V2 behavior
├── V3 Unit: per-module tests for all new code
├── V3 Integration: cross-module tests (agent + backtest + report)
├── V3 Contract: API contract tests (V2 + V3 endpoints)
├── V3 Security: auth, RBAC, rate limiting, AI safety
└── Compatibility: V2-on-V3 tests (run V2 pipeline on V3 codebase)
```

---

## 14. Development Roadmap

### 14.1 Phase Structure

```
Phase 0: Foundation (Week 1-2)
├── FastAPI migration (parallel to Flask, /api/v3)
├── Event bus infrastructure (Redis)
├── Audit trail database + logging
├── V3 database schema migrations
└── CI/CD pipeline updates

Phase 1: Fundamental Intelligence (Week 3-5)
├── Financial statement fetchers (akshare integration)
├── Fundamental series database
├── Macro data pipeline
├── Fundamental factor bridge (15+ new factors)
├── Industry classification + peer comparison
└── Tests: 80+ test cases

Phase 2: Investment Journal Memory (Week 6-8)
├── Research memory data model + repository
├── Journal entry CRUD + full-text search
├── Market context snapshots
├── Memory analytics (hit rate, calibration, mood)
├── Outcome tracker (thesis validation)
└── Tests: 60+ test cases

Phase 3: Research Agent Framework (Week 9-12)
├── Agent base class + orchestrator
├── Alpha Agent (screening + idea generation)
├── Risk Agent (portfolio surveillance)
├── Fundamental Agent (deep dive)
├── Sentiment Agent (market pulse)
├── Tool library (15+ agent tools)
├── Safety framework (ACL, validation, guardrails)
├── Agent scheduler (cron, event, conditional)
├── Custom agent spec system
└── Tests: 100+ test cases

Phase 4: Backtesting Engine V3 (Week 13-16)
├── Point-in-time data portal
├── Multi-asset event loop
├── Fill model hierarchy (limit, VWAP, impact)
├── Full cost model
├── Corporate action handler
├── Portfolio constraint checker
├── Risk engine (factor model, VaR, stress tests)
├── Enhanced analytics (40+ metrics, attribution)
├── Bayesian + genetic optimization
├── Result versioning + comparison
└── Tests: 120+ test cases

Phase 5: Report Generation System (Week 17-19)
├── Report generator framework
├── Component library (tables, charts, callouts)
├── Template engine (Jinja2) + all report types
├── PDF rendering pipeline
├── Report scheduler
└── Tests: 50+ test cases

Phase 6: Web Workspace V3 (Week 20-23)
├── HTMX + Alpine.js workspace shell
├── Project management pages
├── Agent management + monitoring UI
├── Journal calendar + editor
├── Fundamental data explorer
├── Backtest configuration wizard
├── Report viewer + download
├── Memory analytics dashboard
├── Real-time event feed (WebSocket)
├── Dark mode + responsive design
└── Tests: 40+ test cases

Phase 7: Integration & Hardening (Week 24-26)
├── End-to-end integration tests
├── Performance profiling + optimization
├── Security audit + penetration testing
├── Documentation: API docs, user guide, developer guide
├── Migration guide: V2 → V3
├── Release notes + changelog
└── Showcase deployment
```

### 14.2 Milestones

```
M0 (Week 2):  Foundation — API v3 skeleton, event bus, audit trail
M1 (Week 5):  Fundamental Intelligence — 15+ new factors, macro pipeline
M2 (Week 8):  Journal Memory — full memory + journal + analytics
M3 (Week 12): Agent Framework — 4 standard agents, custom agent system
M4 (Week 16): Backtest V3 — PIT data, multi-asset, institutional analytics
M5 (Week 19): Report System — multi-format, multi-audience reports
M6 (Week 23): Web Workspace — unified UI, project-based workflow
M7 (Week 26): V3.0.0 Release — hardened, documented, production-ready
```

### 14.3 Commit Strategy

Approximately 120–150 commits across 7 phases, following Conventional Commits:

```
feat(fundamental): ...
feat(journal): ...
feat(agents): ...
feat(backtest-v3): ...
feat(report): ...
feat(web-v3): ...
test(...): ...
docs(...): ...
fix(...): ...
```

---

## 15. Key Design Decisions

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Event-driven OS paradigm** over linear pipeline | Enables scheduling, multi-agent, persistent state, real-time reactivity | Stay with pipeline + add cron (too limited) |
| 2 | **FastAPI** for V3 API, Flask maintained for V2 | FastAPI: native async, automatic OpenAPI, WebSocket, Pydantic integration | Keep Flask (no async, manual docs), Django (too heavy) |
| 3 | **SQLite** as primary DB, PostgreSQL optional | Zero-config for single-user, sufficient for personal research, easy backup | PostgreSQL only (ops burden), DuckDB (not mature enough) |
| 4 | **HTMX + Alpine.js** for V3 web UI | Progressive enhancement, server-rendered, minimal JS build step | React SPA (premature for single-user), full SSR (less interactive) |
| 5 | **Agent-based AI** over single-pass pipeline | Multi-agent enables specialization, competition, persistent learning, scheduling | Single LLM call with bigger prompt (no persistence, no specialization) |
| 6 | **Point-in-time data portal** for backtesting | Eliminates look-ahead bias, critical for realistic strategy validation | Continue with adjusted data (known bias, but simpler) |
| 7 | **DSL-first strategy safety** (keep from V2) | Proven safe, no code execution risk, AST-validated | Allow Python strategy code (flexibility at cost of safety) |
| 8 | **Separate DB per domain** (16 databases) | Independent evolution, no migration conflicts, easy backup per domain | Monolithic DB (migration hell), schema-per-domain in one DB (medium) |
| 9 | **Fundamental as horizontal layer**, not pipeline stage | Fundamentals inform all stages (screening, factor mapping, valuation, risk), not just one step | Add as pipeline stage 2.5 (limited integration) |
| 10 | **Human-in-the-loop** for all trading actions | AI recommends, human decides. Required for safety and regulatory alignment | Fully autonomous (too risky for personal finance) |
| 11 | **Immutable audit trail** (append-only) | Complete operational transparency, regulatory readiness, debugging | Mutable logs (can't prove what happened) |
| 12 | **V2 API maintained 12 months** | Smooth migration, no forced upgrades, builds trust with existing users | Immediate deprecation (disruptive, loses users) |

---

## Appendix A: Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Language | Python 3.12+ | Existing codebase, quant ecosystem (pandas, numpy) |
| Web Framework | FastAPI (V3) + Flask (V2 compat) | Async, auto-docs, WebSocket |
| Database | SQLite (primary) + PostgreSQL (optional) | Zero-config for single user |
| Cache | Redis (optional) | Event bus, real-time data, rate limiting |
| ORM | SQLAlchemy 2.0 | Existing, mature, async support |
| Data | pandas, numpy, akshare, yfinance | Existing, comprehensive China market support |
| Charts | Plotly | Interactive, Python-native, existing |
| Templates | Jinja2 | Existing, flexible, Python-native |
| PDF | WeasyPrint | Python-native, CSS-based layout |
| Auth | PyJWT + bcrypt | Existing, proven |
| Validation | Pydantic v2 | FastAPI native, performant |
| Testing | pytest + pytest-asyncio | Existing, 400+ tests |
| Linting | ruff + mypy | Existing, fast, strict mode |
| CI/CD | GitHub Actions | Standard, free for public repos |
| Container | Docker + docker-compose | Optional deployment |

---

## Appendix B: Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep (too many features) | High | Schedule delay | Strict phase gating, MVP per phase |
| V2 regression (new code breaks old) | Medium | Trust loss, user churn | CI gate: 400+ tests must pass, characterization tests |
| Data quality (garbage fundamental data) | Medium | Wrong investment decisions | Quality gates, cross-source reconciliation, staleness alerts |
| AI agent errors (bad recommendations) | Medium | Financial loss | Safety framework, human-in-the-loop, conviction tracking |
| Performance (slow PIT backtests) | Medium | Poor UX | Caching, incremental computation, parallel execution |
| Solo developer bottleneck | High | Slow progress | Modular phases, clear interfaces, leverage existing code |
| Dependency breakage (akshare API changes) | Medium | Data pipeline failure | Provider abstraction, fallback chains, monitoring |

---

## Appendix C: Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| V2 test suite passes | 100% | CI pipeline |
| V3 test coverage | > 85% | pytest-cov |
| Backtest accuracy (vs known benchmarks) | < 1% error | Zipline/PyAlgoTrade comparison |
| API response time (p95) | < 500ms | Prometheus histogram |
| Agent recommendation quality | > 55% hit rate (6-month) | Memory analytics |
| Journal adoption | > 3 entries/week for active user | Journal analytics |
| Report generation time | < 10s for full institutional report | Telemetry |
| Zero V2 API breakages | 0 reported | Issue tracker |

---

> **Document Version**: 1.0  
> **Last Updated**: 2026-08-06  
> **Next Review**: After Phase 1 completion  
> **Author**: LXL·QuantAxis Architecture Team
