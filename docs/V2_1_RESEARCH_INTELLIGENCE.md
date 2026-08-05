# LXL·QuantAxis V2.1 — Research Intelligence Upgrade

> **Design Document v2.1.0**  
> Buy-side Quant Research Lead × FinTech Architect × Python Architect

---

## 0. Vision

**V2.0 answers**: "Can this thesis be systematically validated?"

**V2.1 answers**: "Which of my past theses were right? Why? What have I learned?"

The core insight: every investment thesis is a **prediction about the future**. The system should:

1. **Record** the prediction at the moment of conviction
2. **Track** whether it materialized
3. **Verify** whether the factor model captured it
4. **Learn** from the pattern of correct and incorrect calls

This transforms the platform from a "research pipeline" into a **personal research intelligence system** — one that improves with every prediction you make.

---

## 1. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Research Web UI (enhanced)                  │
│  Memory Dashboard · Journal · Pipeline · Workspace · Reports  │
├──────────────────────────────────────────────────────────────┤
│                      Application Services                     │
│  MemoryService · JournalService · PipelineService            │
├─────────────┬────────────────────┬────────────────────────────┤
│             │                    │                            │
│  RESEARCH   │  JOURNAL ENGINE    │  QUANT ENGINE (v2.0)       │
│  MEMORY     │  (New)             │  UNCHANGED                 │
│  ENGINE     │                    │                            │
│  (New)      │  · Daily Log       │  · 28 Factors              │
│             │  · Decision Record │  · 16 Strategies           │
│  · Thesis   │  · Lesson Library  │  · Backtest Engine         │
│    Registry │  · Mood Tracking   │  · Portfolio Analytics     │
│  · Outcome  │                    │  · AI Pipeline             │
│    Tracker  ├────────────────────┤                            │
│  · Accuracy │  FUNDAMENTAL       │                            │
│    Analytics│  INTELLIGENCE (New)│                            │
│  · Behavior │                    │                            │
│    Learning │  · Financial Data  │                            │
│             │  · PE/PB/ROE Hist  │                            │
│             │  · Industry Context│                            │
│             │  · Macro Indicators│                            │
├─────────────┴────────────────────┴────────────────────────────┤
│                     Data Layer                                │
│  SQLite ×15 · akshare · yfinance · CSV Cache                 │
└──────────────────────────────────────────────────────────────┘
```

### Dependency Rules

```
workspace → {memory, journal, fundamental, existing pipeline}
memory   → {existing pipeline, fundamental}
journal  → {existing notebook}
fundamental → {existing data layer}

// NO module depends upward
// NO existing v2.0 module is modified
// v2.0 quant engine is a dependency, never a dependant
```

---

## 2. Research Memory Engine — The Core

### 2.1 Data Model

The memory engine tracks the **full lifecycle** of every investment prediction.

```python
@dataclass(frozen=True, slots=True)
class ThesisRecord:
    """Immutable record of an investment prediction at the moment it was made."""
    
    # Identity
    record_id: str             # UUID, created at prediction time
    thesis_id: int             # FK → research_notes
    
    # The prediction
    symbol: str                # target security
    thesis_text: str           # original natural language
    thesis_direction: str      # "bullish" | "bearish" | "neutral"
    conviction: str            # "low" | "medium" | "high"
    time_horizon: str          # "short" (<1M) | "medium" (1-3M) | "long" (>3M)
    
    # The factor context (snapshot at prediction time)
    factor_model: str          # JSON blob — which factors, what weights
    factor_values: str         # JSON blob — actual factor values at prediction
    
    # The quantitative model
    strategy_spec: str         # JSON blob — the DSL strategy
    backtest_metrics: str      # JSON blob — historical performance
    
    # The outcome (filled later by outcome tracker)
    predicted_return: float | None    # what the model expected
    actual_return: float | None      # what actually happened
    outcome: str | None              # "correct" | "incorrect" | "partial" | "untracked"
    outcome_date: str | None         # when the outcome was determined
    outcome_note: str                # researcher's retrospective
    
    # Behavioral metadata
    created_at: str
    created_in_regime: str | None   # market regime at prediction time
    created_in_project: str | None  # FK → research_project
```

### 2.2 Outcome Tracker

The outcome tracker is a **background process** (or manually triggered) that:

1. Finds all `ThesisRecord`s with `outcome = None` and `outcome_date <= today`
2. Fetches current price data for each symbol
3. Computes the actual return since prediction date
4. Compares direction (bullish/bearish) with actual price movement
5. Updates `outcome`, `actual_return`, `outcome_date`

```python
class OutcomeTracker:
    def check_outcome(self, record: ThesisRecord) -> ThesisRecord:
        """Single record: fetch current price, compute return, determine outcome."""
        
    def check_all_pending(self) -> list[ThesisRecord]:
        """All records with null outcome and past outcome_date."""
        
    def check_by_project(self, project_id: str) -> list[ThesisRecord]:
        """All records in a specific project."""
```

### 2.3 Accuracy Analytics

The analytics engine aggregates prediction performance to reveal patterns.

```python
class MemoryAnalytics:
    def overall_accuracy(self) -> dict:
        """{total_predictions, correct, incorrect, untracked, hit_rate}"""
    
    def accuracy_by_style(self) -> dict:
        """Hit rate broken down by investment style (growth/value/momentum/macro)"""
    
    def accuracy_by_conviction(self) -> dict:
        """Hit rate by conviction level — are you calibrated?"""
    
    def accuracy_by_regime(self) -> dict:
        """Hit rate by market regime — when are you most accurate?"""
    
    def accuracy_by_factor(self) -> dict:
        """Which factors were present in correct vs incorrect predictions?"""
    
    def calibration_curve(self) -> dict:
        """High-conviction predictions should have higher hit rate.
        If not, you're overconfident."""
    
    def time_decay_analysis(self) -> dict:
        """Does accuracy improve with more predictions? Learning curve."""
    
    def factor_effectiveness(self) -> dict:
        """Which factors actually predicted outcomes vs which were noise?"""
```

### 2.4 Behavior Learning

The most advanced capability: the system learns which factors *you* use well.

```python
class BehaviorLearner:
    def researcher_strengths(self) -> dict:
        """In which styles/regimes/sectors do you have above-average accuracy?"""
    
    def researcher_blindspots(self) -> dict:
        """In which areas do you consistently underperform? Pattern of errors."""
    
    def conviction_calibration(self) -> dict:
        """When you say 'high conviction', what's your actual hit rate?"""
    
    def suggested_focus(self) -> list[str]:
        """Based on your track record, where should you focus next?"""
```

---

## 3. Module Design

### 3.1 Research Memory (`src/lxl_quantaxis/memory/`)

```
memory/
├── __init__.py
├── models.py              # ThesisRecord, OutcomeType, ConvictionLevel
├── registry.py            # ThesisRegistry — CRUD for thesis records
├── outcome_tracker.py     # OutcomeTracker — check and update outcomes
├── analytics.py           # MemoryAnalytics — aggregate statistics
├── behavior.py            # BehaviorLearner — pattern recognition
├── search.py              # MemorySearch — full-text search across all records
└── bridge.py              # PipelineBridge — auto-register after pipeline run
```

### 3.2 Investment Journal (`src/lxl_quantaxis/journal/`)

```
journal/
├── __init__.py
├── models.py              # JournalEntry, EntryType, Mood
├── repository.py          # JournalRepository
├── daily.py               # DailyJournal — structured end-of-day template
├── decision.py            # DecisionLog — buy/sell/hold decisions
└── analytics.py           # JournalAnalytics — mood trends, decision frequency
```

### 3.3 Fundamental Intelligence (`src/lxl_quantaxis/data/fundamental/`)

```
data/fundamental/
├── __init__.py
├── fetcher.py             # FundamentalFetcher — akshare financial data
├── series_db.py           # FundamentalSeriesDB — SQLite persistence
├── factor_bridge.py       # FundamentalFactorBridge — register to FACTOR_REGISTRY
└── industry.py            # IndustryContext — Shenwan classification + peers
```

### 3.4 Research Workspace (`src/lxl_quantaxis/workspace/`)

```
workspace/
├── __init__.py
├── models.py              # ResearchProject
├── service.py             # WorkspaceService — CRUD + resource linking
└── dashboard.py           # DashboardData — aggregate per-project view
```

---

## 4. Database Design

### memory.db

```sql
CREATE TABLE thesis_records (
    record_id TEXT PRIMARY KEY,
    thesis_id INTEGER NOT NULL,
    symbol TEXT NOT NULL DEFAULT '',
    thesis_text TEXT NOT NULL,
    thesis_direction TEXT NOT NULL DEFAULT 'neutral',
    conviction TEXT NOT NULL DEFAULT 'medium',
    time_horizon TEXT NOT NULL DEFAULT 'medium',
    factor_model TEXT DEFAULT '{}',
    factor_values TEXT DEFAULT '{}',
    strategy_spec TEXT DEFAULT '{}',
    backtest_metrics TEXT DEFAULT '{}',
    predicted_return REAL,
    actual_return REAL,
    outcome TEXT,
    outcome_date TEXT,
    outcome_note TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    created_in_regime TEXT,
    created_in_project TEXT
);

CREATE INDEX idx_memory_symbol ON thesis_records(symbol);
CREATE INDEX idx_memory_direction ON thesis_records(thesis_direction);
CREATE INDEX idx_memory_conviction ON thesis_records(conviction);
CREATE INDEX idx_memory_outcome ON thesis_records(outcome);
CREATE INDEX idx_memory_created ON thesis_records(created_at);
CREATE INDEX idx_memory_project ON thesis_records(created_in_project);
```

### journal.db

```sql
CREATE TABLE journal_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    entry_type TEXT NOT NULL,        -- observation|decision|lesson|review|daily
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    symbols TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    related_record_id TEXT,          -- FK → thesis_records
    related_thesis_id INTEGER,       -- FK → research_notes
    mood TEXT,                       -- bullish|bearish|neutral|uncertain
    market_context TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX idx_journal_date ON journal_entries(date);
CREATE INDEX idx_journal_type ON journal_entries(entry_type);
CREATE INDEX idx_journal_record ON journal_entries(related_record_id);
```

### fundamental.db

```sql
CREATE TABLE fundamental_snapshots (
    symbol TEXT NOT NULL,
    report_date TEXT NOT NULL,
    pe_ttm REAL, pb REAL, roe_ttm REAL, roa REAL,
    revenue_yoy REAL, profit_yoy REAL,
    gross_margin REAL, net_margin REAL,
    industry TEXT, market_cap REAL,
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

### workspace.db

```sql
CREATE TABLE research_projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    theme TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    record_ids TEXT DEFAULT '[]',
    thesis_ids TEXT DEFAULT '[]',
    journal_ids TEXT DEFAULT '[]',
    report_paths TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT
);
```

---

## 5. API Design

### Memory API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/memory/register` | Register thesis prediction record |
| GET | `/api/v2/memory/list` | List records (filter by symbol, direction, outcome) |
| GET | `/api/v2/memory/<id>` | Single record detail |
| POST | `/api/v2/memory/<id>/review` | Add retrospective review |
| GET | `/api/v2/memory/analytics` | Accuracy stats, calibration, factor effectiveness |
| GET | `/api/v2/memory/behavior` | Researcher strengths, blindspots, learning patterns |
| POST | `/api/v2/memory/check-outcomes` | Trigger outcome check for pending records |

### Journal API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/journal/create` | Create entry |
| GET | `/api/v2/journal/list` | List entries with filters |
| GET | `/api/v2/journal/<id>` | Single entry |
| GET | `/api/v2/journal/daily-template` | Get structured daily journal template |
| GET | `/api/v2/journal/analytics` | Mood trends, decision stats |

### Fundamental API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/fundamental/<symbol>` | Latest fundamental snapshot |
| GET | `/api/v2/fundamental/<symbol>/series` | Historical fundamental series |
| GET | `/api/v2/fundamental/<symbol>/peers` | Industry peers for comparison |

### Workspace API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/workspace/create` | Create research project |
| GET | `/api/v2/workspace/list` | List projects |
| GET | `/api/v2/workspace/<id>` | Project dashboard (all linked resources) |
| POST | `/api/v2/workspace/<id>/link` | Link a thesis/journal/record to project |

---

## 6. Web Page Design

### 6.1 Memory Dashboard (`/memory`)

The hero page of v2.1. Shows:

```
┌─────────────────────────────────────────────────────────┐
│  Research Memory Dashboard                              │
├───────────────────┬─────────────────────────────────────┤
│                   │                                     │
│  Accuracy Gauge   │  Accuracy by Style (bar chart)      │
│  (73% hit rate)   │  Growth: 78%  Value: 65%           │
│                   │  Momentum: 70%  Macro: 80%          │
│  28 predictions   │                                     │
│  20 correct       │  Calibration Curve                  │
│  5 incorrect      │  High: 80%  Med: 65%  Low: 55%     │
│  3 pending        │                                     │
│                   │  Learning Curve (line chart)        │
│  Calibration: OK  │  Hit rate over time →               │
│  (not overconf.)  │                                     │
├───────────────────┴─────────────────────────────────────┤
│  Recent Predictions (table)                             │
│  Date       Symbol  Direction  Conviction  Outcome       │
│  2026-08-01 600519  Bullish    High        Correct ✓    │
│  2026-07-28 000858  Bullish    Medium      Pending...   │
│  2026-07-20 300750  Bearish    Low         Incorrect ✗  │
│                                                        │
│  [View All] [Filter by Symbol] [Filter by Outcome]     │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Journal (`/journal`)

```
┌─────────────────────────────────────────────────────────┐
│  Investment Journal                                     │
├───────────────────┬─────────────────────────────────────┤
│  [New Entry]      │  Mood Trend (line chart)            │
│                   │                                     │
│  Quick Templates: │  Decision Frequency (bar chart)     │
│  · Daily Review   │                                     │
│  · Buy Decision   │  Recent Entries (timeline)          │
│  · Sell Decision  │  2026-08-04  Daily Review           │
│  · Lesson Learned │  2026-08-04  Buy: 600519 @ 2450     │
│  · Observation    │  2026-08-03  Lesson: value traps     │
│                   │  2026-08-03  Observation: vol spike  │
└───────────────────┴─────────────────────────────────────┘
```

### 6.3 Workspace (`/workspace`)

```
┌─────────────────────────────────────────────────────────┐
│  Research Workspace                                     │
├───────────────────┬─────────────────────────────────────┤
│  Projects         │  AI Infrastructure (active)          │
│                   │                                     │
│  · AI Infra       │  Theses: 3  │  Predictions: 2       │
│  · Consumer       │  Journal: 5 │  Reports: 1           │
│  · Semi Cycle     │                                     │
│                   │  Accuracy: 75% (3/4)                 │
│  [+ New Project]  │                                     │
│                   │  [Run Pipeline] [View Reports]       │
├───────────────────┴─────────────────────────────────────┤
│  Linked Resources (table)                               │
│  Type        Date       Title                Status      │
│  Thesis      2026-08-01 AI Server Bull Case  Correct ✓  │
│  Prediction  2026-08-02 GPU Demand Growth    Pending     │
│  Journal     2026-08-03 AI Capex Observation  —          │
│  Report      2026-08-04 AI_Infra_Report.md   —           │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Python Directory Structure

```
src/lxl_quantaxis/
│
├── memory/                          # Research Memory Engine (CORE)
│   ├── __init__.py                  # exports ThesisRecord, registry, analytics
│   ├── models.py                    # ThesisRecord (frozen dataclass)
│   ├── registry.py                  # ThesisRegistry (SQLite CRUD)
│   ├── outcome_tracker.py           # OutcomeTracker + OutcomeChecker
│   ├── analytics.py                 # MemoryAnalytics (6 analysis dimensions)
│   ├── behavior.py                  # BehaviorLearner (strengths, blindspots)
│   ├── search.py                    # MemorySearch (full-text + faceted)
│   └── bridge.py                    # PipelineBridge (auto-register on pipeline run)
│
├── journal/                         # Investment Journal
│   ├── __init__.py
│   ├── models.py                    # JournalEntry
│   ├── repository.py                # JournalRepository
│   ├── daily.py                     # DailyJournal (structured template)
│   ├── decision.py                  # DecisionLog (buy/sell/hold records)
│   └── analytics.py                 # JournalAnalytics (mood, frequency)
│
├── data/fundamental/                # Fundamental Intelligence
│   ├── __init__.py
│   ├── fetcher.py                   # FundamentalFetcher
│   ├── series_db.py                 # FundamentalSeriesDB
│   ├── factor_bridge.py             # FundamentalFactorBridge
│   └── industry.py                  # IndustryContext
│
├── workspace/                       # Research Workspace
│   ├── __init__.py
│   ├── models.py                    # ResearchProject
│   ├── service.py                   # WorkspaceService
│   └── dashboard.py                 # DashboardData
│
├── api/routes/                      # API extensions
│   ├── memory_api.py                # /api/v2/memory/*
│   ├── journal_api.py               # /api/v2/journal/*
│   ├── fundamental_api.py           # /api/v2/fundamental/*
│   └── workspace_api.py             # /api/v2/workspace/*
│
└── ...                              # (all existing v2.0 modules unchanged)
```

---

## 8. Commit Plan

### Phase 1: Fundamental Intelligence (8 files, ~800 lines)

```
feat(fundamental): add financial statement fetcher via akshare
feat(fundamental): add fundamental series SQLite database
feat(fundamental): add industry context with Shenwan classification
feat(fundamental): add fundamental-to-factor bridge (PE/ROE/revenue factors)
test(fundamental): add fundamental data tests (10 tests)
```

### Phase 2: Research Memory Engine (8 files, ~1200 lines)

```
feat(memory): add thesis record data model and SQLite registry
feat(memory): add outcome tracker with price-based verification
feat(memory): add memory analytics (accuracy, calibration, factor effectiveness)
feat(memory): add behavior learner (strengths, blindspots, learning curve)
feat(memory): add pipeline bridge for automatic record registration
test(memory): add memory engine tests (15 tests)
```

### Phase 3: Investment Journal (5 files, ~600 lines)

```
feat(journal): add journal entry model and SQLite repository
feat(journal): add daily journal template and decision log
feat(journal): add journal analytics (mood trends, decision frequency)
test(journal): add journal tests (8 tests)
```

### Phase 4: Research Workspace (3 files, ~400 lines)

```
feat(workspace): add research project model and service
feat(workspace): add project dashboard data aggregation
test(workspace): add workspace tests (6 tests)
```

### Phase 5: Web Integration (4 files API + 4 pages HTML, ~800 lines)

```
feat(api): add memory API endpoints (7 routes)
feat(api): add journal API endpoints (5 routes)
feat(api): add fundamental and workspace API endpoints (6 routes)
feat(web): add memory dashboard, journal, and workspace pages
test(web): add API integration tests (10 tests)
```

### Phase 6: Documentation & Release (3 files)

```
docs: add v2.1 user guide with memory analytics walkthrough
docs: add v2.1 release notes
release: v2.1.0 tag
```

**Total**: ~22 commits, ~3800 lines, 49 new tests, 6 phases

---

## 9. Key Design Decisions

| Decision | Why |
|----------|-----|
| Memory as central module, not add-on | Prediction tracking IS the product. Everything else feeds it. |
| Outcome tracker is pull-based, not push | Simpler. Price data is fetched when checked. No streaming needed. |
| JSON blobs for pipeline outputs in memory | Pipeline stages evolve. JSON is flexible. Analysts query by structured fields. |
| Separate memory.db from research_notes.db | Different access patterns. Memory is analytical (aggregates), notes are archival. |
| Behavior learner is read-only analytics | We analyze patterns, not auto-adjust strategies. Human in the loop. |
| Workspace is lightweight (FKs only) | Projects link resources, they don't own them. Minimal data model. |
