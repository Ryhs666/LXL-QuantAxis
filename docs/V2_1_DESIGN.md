# LXL·QuantAxis V2.1 — Design Document

**Role**: Buy-side Quant Research Lead × FinTech Product Architect × Python Architect  
**Status**: Planning | **Branch**: `fix/portfolio-metrics-v2` | **Base**: v2.0.0

---

## 1. Product Positioning

### From v2.0 → v2.1

| v2.0.0 | v2.1 |
|--------|------|
| AI Research Pipeline | **Research Memory Engine** — remembers what you researched |
| One-shot reports | **Investment Journal** — tracks ideas over time |
| Technical factors only | **Fundamental Intelligence** — financial statements, macro |
| Single pipeline | **Research Workspace** — multi-tab, project-based UI |

### Elevator Pitch

> LXL·QuantAxis v2.1 is a **personal investment research system** that remembers every thesis you've tested, tracks how they performed, connects technical factors with fundamental data, and provides a project-based workspace to organize your research workflow.

### Target User

A serious individual investor or quant researcher who:
- Generates 5-20 investment ideas per week
- Wants to track which ideas worked and why
- Needs both technical and fundamental context
- Builds research projects spanning multiple securities

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Research Workspace (Web UI)               │
│  Projects · Notebook · Journal · Pipeline · Reports          │
├─────────────────────────────────────────────────────────────┤
│                     Application Services                     │
│  WorkspaceService · PipelineService · JournalService         │
├───────────────┬───────────────┬─────────────────────────────┤
│ Research      │ Fundamental   │ Quant Engine (v2.0)          │
│ Memory Engine │ Intelligence  │ Factors · Strategies         │
│ (New)         │ (New)         │ Backtest · Portfolio         │
├───────────────┴───────────────┴─────────────────────────────┤
│                    Data Layer (v2.0)                         │
│  SQLite ×12 · akshare · yfinance · CSV Cache                │
└─────────────────────────────────────────────────────────────┘
```

**Key principle**: v2.0 quant engine is **untouched**. V2.1 adds three new horizontal modules and a workspace layer on top.

---

## 3. Module Design

### 3.1 Research Memory Engine (`src/lxl_quantaxis/memory/`)

**Purpose**: Track the lifecycle of every investment thesis — from creation through validation to outcome.

**Data model**:

```python
@dataclass(frozen=True, slots=True)
class ResearchMemory:
    memory_id: str          # UUID
    thesis_id: int          # FK → research_notes
    thesis_text: str        # original natural language
    parsed_thesis: dict     # JSON blob from ai_parser
    factor_model: dict      # JSON blob from factor_mapper
    strategy_spec: dict     # JSON blob from strategy_builder
    backtest_result: dict   # JSON blob from backtest
    ai_assessment: dict     # JSON blob from backtest_analyzer
    report_path: str        # path to generated report
    
    # Outcome tracking (filled later)
    conviction_correct: bool | None   # was the thesis directionally right?
    realized_return: float | None     # actual return if tracked
    reviewed_at: str | None           # when the researcher reviewed
    review_notes: str                 # researcher's retrospective
    
    created_at: str
    updated_at: str
```

**Key capabilities**:
- `MemoryRepository`: CRUD with full search across thesis text, factor names, tags
- `ThesisOutcomeTracker`: Match old theses against current market data to compute hit rate
- `MemoryAnalytics`: Which factor styles worked? What's your conviction-accuracy calibration?
- `MemorySearch`: "Show me all growth theses on consumer stocks from Q1 2026"

**Database**: `research_memory.db` (new SQLite)

### 3.2 Investment Journal (`src/lxl_quantaxis/journal/`)

**Purpose**: A chronological, searchable log of investment decisions, observations, and lessons. Different from the Research Notebook (which stores theses) — the Journal stores the *process*.

**Data model**:

```python
@dataclass(frozen=True, slots=True)
class JournalEntry:
    entry_id: int
    date: str
    entry_type: str         # "observation" | "decision" | "lesson" | "review" | "note"
    title: str
    content: str
    symbols: str            # comma-separated
    tags: str
    related_thesis_id: int | None  # FK → research_notes
    mood: str | None        # "bullish" | "bearish" | "neutral" | "uncertain"
    market_context: str     # brief market summary at time of writing
    
    created_at: str
```

**Key capabilities**:
- `JournalRepository`: CRUD with date-range, symbol, tag, mood filters
- `DailyJournal`: Structured template for end-of-day review
- `DecisionLog`: Specific format for buy/sell/hold decisions with rationale
- `LessonLibrary`: Tagged, searchable collection of lessons learned
- `JournalAnalytics`: Decision frequency, mood trends, conviction tracking over time

**Database**: `journal.db` (new SQLite)

### 3.3 Fundamental Intelligence (`src/lxl_quantaxis/data/fundamental/`)

**Purpose**: Connect real company financial data to the research pipeline. Technical factors tell you *what* is happening. Fundamentals tell you *why*.

**Data sources** (akshare):
- Financial statements: balance sheet, income statement, cash flow (quarterly)
- Key metrics: PE, PB, ROE, ROA, revenue growth, profit margin (historical series)
- Industry classification: Shenwan (申万) industry codes
- Macro indicators: CPI, PPI, PMI, LPR, M2, social financing

**Data model**:

```python
@dataclass(frozen=True, slots=True)
class FundamentalSnapshot:
    symbol: str
    report_date: str        # quarter end date
    pe_ttm: float | None
    pb: float | None
    roe_ttm: float | None
    roa: float | None
    revenue_yoy: float | None
    profit_yoy: float | None
    gross_margin: float | None
    net_margin: float | None
    debt_to_equity: float | None
    current_ratio: float | None
    free_cash_flow: float | None
    industry: str
    market_cap: float | None

@dataclass(frozen=True, slots=True)
class FundamentalSeries:
    symbol: str
    indicator: str          # "pe_ttm", "roe", "revenue_yoy", etc.
    dates: list[str]
    values: list[float]
```

**Key capabilities**:
- `FundamentalFetcher`: Download and cache financial data via akshare
- `FundamentalSeriesDB`: SQLite persistence with incremental updates
- `FundamentalFactorBridge`: Register fundamental-derived factors into FACTOR_REGISTRY
  - `pe_percentile`: PE relative to 5-year history
  - `roe_trend`: ROE direction over last 4 quarters
  - `revenue_acceleration`: 2nd derivative of revenue growth
  - `profit_margin_change`: Quarter-over-quarter margin delta
- `IndustryContext`: Sector-relative comparisons (stock vs industry median)

**Database**: `fundamental.db` (new SQLite), extends existing `financial_series.db`

### 3.4 Research Workspace (`src/lxl_quantaxis/workspace/`)

**Purpose**: Replace the single-pipeline model with a project-based workspace where researchers organize ideas, theses, analyses, and reports.

**Data model**:

```python
@dataclass(frozen=True, slots=True)
class ResearchProject:
    project_id: str         # UUID
    name: str
    description: str
    theme: str              # "AI Infrastructure", "Consumer Recovery", etc.
    status: str             # "active" | "archived" | "completed"
    
    # Linked resources (FKs)
    thesis_ids: list[int]
    memory_ids: list[str]
    journal_ids: list[int]
    report_paths: list[str]
    
    created_at: str
    updated_at: str
```

**Key capabilities**:
- `WorkspaceService`: Create, list, archive projects
- `ProjectDashboard`: Per-project view showing all linked resources
- `ProjectPipeline`: Run the 7-stage pipeline within a project context
- `ProjectExport`: Bundle all project artifacts into a zip

**Database**: `workspace.db` (new SQLite)

---

## 4. Data Flow

```
Researcher opens Workspace
        │
        ├── Creates/opens a Research Project
        │       │
        │       ├── Writes Investment Thesis (Natural Language)
        │       │       │
        │       │       ▼
        │       │   [ai_parser] → Structured Thesis
        │       │       │
        │       │       ├── Saved to Research Notebook
        │       │       ├── Registered in Research Memory
        │       │       └── Linked to Project
        │       │
        │       ├── Adds Fundamental Context
        │       │       │
        │       │       ▼
        │       │   [FundamentalFetcher] → PE/PB/ROE history
        │       │       │
        │       │       └── FundamentalFactorBridge → extends FactorModel
        │       │
        │       ├── Runs AI Pipeline
        │       │       │
        │       │       ▼
        │       │   [factor_mapper → strategy_builder → backtest]
        │       │       │
        │       │       └── Results stored in Research Memory
        │       │
        │       ├── Reviews in Journal
        │       │       │
        │       │       ▼
        │       │   [JournalEntry] → Decision/Observation/Lesson
        │       │
        │       └── Generates Report
        │               │
        │               ▼
        │           [report_generator] → Markdown + HTML
        │
        └── Memory Analytics
                │
                ▼
            [MemoryAnalytics] → Hit rate, conviction calibration,
                                factor style performance, journal insights
```

---

## 5. Database Design

### New Databases (3)

```sql
-- research_memory.db
CREATE TABLE research_memory (
    memory_id TEXT PRIMARY KEY,
    thesis_id INTEGER NOT NULL REFERENCES research_notes(id),
    thesis_text TEXT NOT NULL,
    parsed_thesis TEXT,        -- JSON
    factor_model TEXT,         -- JSON
    strategy_spec TEXT,        -- JSON
    backtest_result TEXT,      -- JSON
    ai_assessment TEXT,        -- JSON
    report_path TEXT,
    conviction_correct INTEGER, -- 0/1/NULL
    realized_return REAL,
    reviewed_at TEXT,
    review_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX idx_memory_thesis ON research_memory(thesis_id);
CREATE INDEX idx_memory_created ON research_memory(created_at);

-- journal.db
CREATE TABLE journal_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    symbols TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    related_thesis_id INTEGER,
    mood TEXT,
    market_context TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX idx_journal_date ON journal_entries(date);
CREATE INDEX idx_journal_type ON journal_entries(entry_type);
CREATE INDEX idx_journal_thesis ON journal_entries(related_thesis_id);

-- workspace.db
CREATE TABLE research_projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    theme TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    thesis_ids TEXT DEFAULT '[]',   -- JSON array
    memory_ids TEXT DEFAULT '[]',   -- JSON array
    journal_ids TEXT DEFAULT '[]',  -- JSON array
    report_paths TEXT DEFAULT '[]', -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX idx_project_status ON research_projects(status);
```

### Extended Existing (1)

```sql
-- fundamental.db (new, alongside existing financial_series.db)
CREATE TABLE fundamental_snapshots (
    symbol TEXT NOT NULL,
    report_date TEXT NOT NULL,
    pe_ttm REAL, pb REAL, roe_ttm REAL, roa REAL,
    revenue_yoy REAL, profit_yoy REAL,
    gross_margin REAL, net_margin REAL,
    debt_to_equity REAL, current_ratio REAL,
    free_cash_flow REAL, industry TEXT,
    market_cap REAL,
    PRIMARY KEY (symbol, report_date)
);

CREATE TABLE fundamental_series (
    symbol TEXT NOT NULL,
    indicator TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL NOT NULL,
    PRIMARY KEY (symbol, indicator, date)
);
```

**Total databases after v2.1**: 14 (10 existing + 4 new/extended)

---

## 6. Python Directory Structure

```
src/lxl_quantaxis/
├── memory/                          # NEW: Research Memory Engine
│   ├── __init__.py
│   ├── models.py                    # ResearchMemory dataclass
│   ├── repository.py                # MemoryRepository (SQLite CRUD)
│   ├── outcome_tracker.py           # ThesisOutcomeTracker
│   ├── analytics.py                 # MemoryAnalytics (hit rate, calibration)
│   └── search.py                    # MemorySearch (full-text)
│
├── journal/                         # NEW: Investment Journal
│   ├── __init__.py
│   ├── models.py                    # JournalEntry dataclass
│   ├── repository.py                # JournalRepository
│   ├── daily.py                     # DailyJournal template
│   ├── decision_log.py             # DecisionLog
│   └── analytics.py                 # JournalAnalytics
│
├── data/
│   ├── fundamental/                 # NEW: Fundamental Intelligence
│   │   ├── __init__.py
│   │   ├── fetcher.py               # FundamentalFetcher (akshare)
│   │   ├── series_db.py             # FundamentalSeriesDB
│   │   ├── factor_bridge.py         # FundamentalFactorBridge
│   │   └── industry.py              # IndustryContext
│   └── ...                          # (existing v2.0 modules unchanged)
│
├── workspace/                       # NEW: Research Workspace
│   ├── __init__.py
│   ├── models.py                    # ResearchProject dataclass
│   ├── service.py                   # WorkspaceService
│   ├── dashboard.py                 # ProjectDashboard data
│   └── export.py                    # ProjectExport
│
├── research/                        # (existing v2.0, enhanced)
│   ├── ai_parser.py                 # Enhanced: accepts fundamental context
│   ├── factor_mapper.py             # Enhanced: fundamental factors in registry
│   └── ...
│
├── api/
│   └── routes/                      # (existing, extended)
│       ├── memory.py                # NEW: /api/v2/memory/*
│       ├── journal.py               # NEW: /api/v2/journal/*
│       ├── fundamental.py           # NEW: /api/v2/fundamental/*
│       └── workspace.py             # NEW: /api/v2/workspace/*
│
└── ...                              # (all existing v2.0 modules unchanged)
```

---

## 7. API Design

### Memory API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v2/memory/list` | User | List all research memories |
| GET | `/api/v2/memory/<id>` | User | Get memory detail |
| GET | `/api/v2/memory/analytics` | User | Hit rate, calibration stats |
| GET | `/api/v2/memory/search?q=` | User | Full-text search |

### Journal API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v2/journal/list` | User | List journal entries |
| POST | `/api/v2/journal/create` | User | Create entry |
| GET | `/api/v2/journal/<id>` | User | Get entry detail |
| DELETE | `/api/v2/journal/<id>` | User | Delete entry |
| GET | `/api/v2/journal/analytics` | User | Journal stats |

### Fundamental API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v2/fundamental/<symbol>` | User | Get fundamental snapshot |
| GET | `/api/v2/fundamental/<symbol>/series` | User | Get historical series |
| GET | `/api/v2/fundamental/industry/<code>` | User | Industry peers |

### Workspace API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v2/workspace/list` | User | List projects |
| POST | `/api/v2/workspace/create` | User | Create project |
| GET | `/api/v2/workspace/<id>` | User | Project dashboard |
| POST | `/api/v2/workspace/<id>/link` | User | Link resource to project |

---

## 8. Development Phases

### Phase 1: Fundamental Intelligence (Week 1-2)
- `data/fundamental/fetcher.py` — akshare financial data download
- `data/fundamental/series_db.py` — SQLite persistence
- `data/fundamental/factor_bridge.py` — register fundamental factors
- Tests: `tests/test_fundamental.py`
- **Impact**: All existing pipeline stages can now use PE, ROE, revenue growth factors

### Phase 2: Research Memory Engine (Week 2-3)
- `memory/models.py` + `memory/repository.py` — data layer
- `memory/outcome_tracker.py` — thesis performance tracking
- `memory/analytics.py` — aggregate statistics
- Tests: `tests/test_memory.py`
- **Impact**: Every pipeline run now creates a permanent, trackable memory record

### Phase 3: Investment Journal (Week 3-4)
- `journal/models.py` + `journal/repository.py` — data layer
- `journal/daily.py` — structured templates
- `journal/analytics.py` — decision tracking
- Tests: `tests/test_journal.py`
- **Impact**: Researchers can now log decisions, observations, and lessons

### Phase 4: Research Workspace (Week 4-5)
- `workspace/models.py` + `workspace/service.py` — project management
- `workspace/dashboard.py` — per-project data aggregation
- Web UI: workspace page (`/workspace`)
- Tests: `tests/test_workspace.py`
- **Impact**: All research now organized into projects

### Phase 5: Integration & Polish (Week 5-6)
- Wire memory registration into existing pipeline stages
- Wire journal into existing web UI
- Wire fundamental factors into factor mapper
- End-to-end integration tests
- Documentation updates

---

## 9. Commit Plan

```
Phase 1 (5 commits):
  feat(fundamental): add financial statement fetcher
  feat(fundamental): add fundamental series database
  feat(fundamental): add PE/ROE/revenue growth factors to registry
  feat(fundamental): add industry context and peer comparison
  test(fundamental): add fundamental data tests

Phase 2 (4 commits):
  feat(memory): add research memory data model and repository
  feat(memory): add thesis outcome tracker
  feat(memory): add memory analytics
  test(memory): add memory engine tests

Phase 3 (4 commits):
  feat(journal): add journal entry model and repository
  feat(journal): add daily journal and decision log
  feat(journal): add journal analytics
  test(journal): add journal tests

Phase 4 (4 commits):
  feat(workspace): add research project model and service
  feat(workspace): add project dashboard
  feat(web): add workspace page to web UI
  test(workspace): add workspace tests

Phase 5 (3 commits):
  feat(integration): wire memory into research pipeline
  feat(integration): wire fundamental factors into mapper
  docs: v2.1 release notes and documentation
```

**Total**: ~20 commits across 5 phases

---

## 10. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate databases per module | Independent development, no migration risk |
| JSON blobs for pipeline outputs in memory | Flexibility — schema evolves with pipeline stages |
| Fundamental as new data module, not new pipeline stage | Fundamentals inform factor selection, they don't replace it |
| Workspace as an organization layer, not a new engine | Minimal code change, maximum UX improvement |
| Journal as separate from Notebook | Notebook = thesis storage; Journal = process logging. Different use cases. |
