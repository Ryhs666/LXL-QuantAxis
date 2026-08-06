# LXL·QuantAxis V3 — Investment Decision Operating System

> **最终架构冻结文档**  
> Personal Investment Decision OS  
> 管理投资者的完整决策生命周期

**Status**: FROZEN — 实施前最终评审  
**Date**: 2026-08-06  
**Supersedes**: ALL previous V3 docs. This is the authoritative source.

---

## 目录

1. [Executive Summary](#1-executive-summary)
2. [Product Philosophy](#2-product-philosophy)
3. [V2 → V3 Evolution](#3-v2--v3-evolution)
4. [User Daily Workflow](#4-user-daily-workflow)
5. [System Architecture](#5-system-architecture)
6. [Core Domain Model](#6-core-domain-model)
7. [Memory Mapping](#7-memory-mapping)
8. [Thesis & Hypothesis Model](#8-thesis--hypothesis-model)
9. [Evidence Architecture](#9-evidence-architecture)
10. [Decision Engine](#10-decision-engine)
11. [Priority Action Engine](#11-priority-action-engine)
12. [Portfolio Intelligence](#12-portfolio-intelligence)
13. [Investor Learning](#13-investor-learning)
14. [Decision Timeline](#14-decision-timeline)
15. [Information Architecture](#15-information-architecture)
16. [Page Structure](#16-page-structure)
17. [API Design](#17-api-design)
18. [Data Schema](#18-data-schema)
19. [Error and Edge Cases](#19-error-and-edge-cases)
20. [Development Phases](#20-development-phases)
21. [Git Commit Plan](#21-git-commit-plan)
22. [Acceptance Criteria](#22-acceptance-criteria)
23. [Explicit Non-goals](#23-explicit-non-goals)
24. [V3/V4 Boundary](#24-v3v4-boundary)

**Appendices**

A. [Current Foundation Audit](#appendix-a-current-foundation-audit)  
B. [Data Migration Risk Assessment](#appendix-b-data-migration-risk-assessment)  
C. [Minimum Viable Scope](#appendix-c-minimum-viable-scope)

---

## 1. Executive Summary

### 1.1 What We're Building

LXL·QuantAxis V3 is a **Personal Investment Decision Operating System**. It manages the complete lifecycle of an investment decision — from market observation through hypothesis formation, evidence collection, thesis validation, portfolio action, outcome tracking, and reflective learning.

### 1.2 The Gap We're Filling

| Tool | Manages |
|------|---------|
| Bloomberg | Market information |
| TradingView | Price and charts |
| Notion | Unstructured knowledge |
| Excel | Custom calculations |
| **LXL·QuantAxis** | **Your own decision process** |

No existing tool systematically tracks *how an investor thinks, decides, and learns*.

### 1.3 Core Capability

The system answers seven questions every time the user opens it:

1. What's happening in the market today?
2. What should I be paying attention to?
3. What do I currently believe?
4. What should I do next?
5. Where are the risks in my portfolio?
6. Am I becoming a better investor?
7. How did I arrive at this decision?

### 1.4 What It Is Not

- Not a prediction engine
- Not an automated trading system
- Not a Bloomberg terminal replacement
- Not a general-purpose note-taking app
- Not a demo or showcase

---

## 2. Product Philosophy

### 2.1 Core Principles

```
1. The system does not make investment decisions.
   It makes the investor's decision process visible, traceable, and improvable.

2. Every thesis must be falsifiable.
   "I think X will happen" is not enough.
   "I think X will happen, and I'll know I'm wrong if Y occurs by date Z."

3. Failed theses are learning assets, not mistakes to hide.
   Wrong predictions, properly analyzed, are more valuable than lucky wins.

4. Conviction without evidence is gambling.
   The system requires the investor to articulate WHY they believe something.

5. Process quality predicts long-term outcomes.
   The system measures process, not just P&L.
```

### 2.2 The Decision Lifecycle

```
                    ┌─────────────────────┐
                    │   MARKET CONTEXT     │
                    │   What's happening?  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   OBSERVATION        │
                    │   Something notable  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   HYPOTHESIS         │
                    │   If X, then Y       │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
          ┌──────────────┐      ┌──────────────┐
          │  EVIDENCE     │      │  COUNTER      │
          │  Supporting   │      │  Evidence     │
          └──────┬───────┘      └──────┬───────┘
                 │                     │
                 └──────────┬──────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │   THESIS             │
                  │   Structured belief  │
                  │   + conviction       │
                  │   + invalidation     │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   DECISION           │
                  │   Action + rationale │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   PORTFOLIO          │
                  │   Exposure tracking  │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   OUTCOME            │
                  │   Result vs forecast │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   REFLECTION         │
                  │   What did I learn?  │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   INVESTOR LEARNING  │
                  │   Am I improving?    │
                  └─────────────────────┘
```

---

## 3. V2 → V3 Evolution

### 3.1 What Changes

| Dimension | V2.0 Showcase | V3.0 Decision OS |
|-----------|---------------|------------------|
| **Paradigm** | Research pipeline | Decision operating system |
| **User model** | Stateless visitor | Persistent investor identity |
| **Core data** | Backtest results | Memory entries (4 types) |
| **Thesis** | Free text | Structured hypothesis tree + evidence + versioning |
| **Decision** | Trade log entry | Decision record with pre-flight checks |
| **Learning** | None | Calibration score + growth metrics |
| **UI** | 9 standalone pages | Unified Command Center shell |
| **AI role** | Pipeline processor | Evidence analyst + calibration coach |

### 3.2 What Stays

- All V2 code (155 files in `src/lxl_quantaxis/`) — **zero modifications**
- All V2 tests (400+) — **must continue to pass**
- All V2 web routes — **unchanged**
- `web_modern.py` — **only Blueprint registrations added**
- Zero new pip dependencies

---

## 4. User Daily Workflow

### 4.1 Morning Routine (5 minutes)

```
8:45 AM — Open /workspace

Step 1 (10s):  Scan Market Context
               → "CSI 300 +0.8%, tech leading, my watchlist mostly green"

Step 2 (30s):  Read Priority Actions
               → "🔴 SMIC thesis 45d stale — need to review"
               → "🟡 Maotai thesis 32d overdue for review"

Step 3 (20s):  Quick glance at Thesis Board
               → "2 forming, 1 validating, 1 waiting — pipeline is flowing"

Step 4 (20s):  Quick glance at Portfolio Intelligence
               → "NVDA at 35% — concentration warning is active"
               → "Wuliangye has position but no thesis — need to write one"

Step 5 (2-4min): Act on top priority item
               → Click the 🔴 action → update thesis → done
```

### 4.2 During Trading Day (as needed)

```
Quick Capture (30s):
  → Type idea in Quick Capture bar → Enter
  → Goes to Research Inbox for later triage

Record Decision (1min):
  → Navigate to thesis → "Record Decision"
  → Fill: action type, price, quantity, rationale
  → Pre-flight checklist runs automatically
  → System flags: "No counter evidence recorded" or "No invalidation set"

Update Thesis (2min):
  → Edit thesis → add new evidence → adjust confidence
  → Version history auto-records the change
```

### 4.3 Evening Review (5-10 minutes)

```
Step 1:  Process Research Inbox → triage items
Step 2:  Review Thesis Board → update any stale theses
Step 3:  Record any decisions made today
Step 4:  Quick glance at Investor Learning → calibration trend
Step 5:  Write Reflection if significant lesson learned
```

### 4.4 Weekly Ritual (20 minutes)

```
- Full Inbox triage (process all captured items)
- Review all WAITING theses
- Update Investment Universe (add/remove from watchlist)
- Check Portfolio Intelligence for coverage gaps
- Review calibration trend
- Write at least one Reflection
```

---

## 5. System Architecture

### 5.1 Layer Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                         │
│                                                               │
│  /workspace  /inbox  /thesis  /decision  /timeline           │
│  /portfolio  /learning  /journal                             │
│                                                               │
│  Unified Shell: HTMX + Alpine.js · terminal.css dark theme    │
├──────────────────────────────────────────────────────────────┤
│                    APPLICATION LAYER                          │
│                                                               │
│  Command Center  ·  Thesis Engine  ·  Decision Engine        │
│  Evidence Manager  ·  Priority Engine  ·  Learning Tracker   │
│  Portfolio Analyzer  ·  Inbox Manager  ·  Timeline Builder   │
├──────────────────────────────────────────────────────────────┤
│                    DOMAIN LAYER                                │
│                                                               │
│  MemoryRepository  ·  MemorySearch  ·  MemoryAnalytics       │
│  MemoryAdapter  ·  PortfolioAdapter                           │
├──────────────────────────────────────────────────────────────┤
│                    PERSISTENCE LAYER                           │
│                                                               │
│  lxl_v3.db (memory_entries)  ·  V2 trades.db (read-only)     │
│  SQLite + WAL · FTS5 · JSON blobs                             │
├──────────────────────────────────────────────────────────────┤
│                    V2 KERNEL (UNCHANGED)                      │
│                                                               │
│  Factors · Strategies · Backtest · Portfolio · AI Pipeline    │
│  src/lxl_quantaxis/ — 155 files, 0 modifications              │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Module Dependency Graph

```
src/v3/
├── memory/              ← Phase 1 (complete)
│   ├── models.py        MemoryEntry (frozen dataclass)
│   ├── database.py      SQLite + WAL connection
│   ├── repository.py    CRUD + JSON serialization
│   ├── search.py        FTS5 multi-filter query
│   └── analytics.py     Stats + calibration
│
├── web/                 ← Phase 1 (complete)
│   ├── journal_page.py  /journal route
│   └── journal_api.py   11 REST endpoints
│
├── workspace/           ← Phase 2 (in progress)
│   ├── repository.py    MemoryAdapter + PortfolioAdapter
│   ├── service.py       WorkspaceService
│   ├── routes.py        Command Center API
│   │
│   ├── intelligence.py  ★ Priority Engine (Commit 7)
│   ├── inbox.py         ★ Research Inbox (Commit 8)
│   ├── thesis_board.py  ★ Thesis Board builder (Commit 9)
│   ├── portfolio_intel.py ★ Portfolio analysis (Commit 10)
│   ├── learning.py      ★ Learning tracker (Commit 10)
│   │
│   ├── evidence.py      ★★ Evidence manager (Commit 12)
│   ├── versioning.py    ★★ Thesis versioning (Commit 13)
│   ├── timeline.py      ★★ Decision timeline (Commit 14)
│   ├── calibration.py   ★★ Calibration engine (Commit 15)
│   ├── growth.py        ★★ Growth metrics (Commit 16)
│   │
│   ├── hypothesis.py    ★★★ Hypothesis tree (Commit 17)
│   ├── decision.py      ★★★ Decision engine (Commit 18)
│   └── checklist.py     ★★★ Pre-decision checklist (Commit 19)
│
└── (future modules)
```

---

## 6. Core Domain Model

### 6.1 Entity Relationship

```
MarketContext ──→ Observation ──→ Hypothesis
                                      │
                                      ├──→ Evidence (supporting)
                                      ├──→ Evidence (counter)
                                      │
                                      ▼
                                    Thesis
                                      │
                            ┌─────────┼─────────┐
                            │         │         │
                            ▼         ▼         ▼
                        Decision  Portfolio  Outcome
                            │         │         │
                            └─────────┼─────────┘
                                      │
                                      ▼
                                  Reflection
                                      │
                                      ▼
                              Investor Learning
```

### 6.2 Entity Definitions

| Entity | Definition | Stored In |
|--------|-----------|-----------|
| **Observation** | Something noticed in the market, a company, or data | memory_entries (type='note') |
| **Hypothesis** | A falsifiable sub-claim within a thesis | thesis.hypotheses JSON array |
| **Evidence** | A piece of information that supports or counters a hypothesis | thesis.evidence JSON |
| **Thesis** | A structured investment belief with conviction, timeline, and invalidation conditions | memory_entries (type='thesis') |
| **Decision** | A deliberate action (watch, research, buy, sell, etc.) with rationale and pre-flight checks | memory_entries (type='decision') |
| **Outcome** | The result of a thesis or decision, compared against the original forecast | thesis.status + thesis.outcome JSON |
| **Reflection** | A lesson extracted from an outcome, encoded as reusable knowledge | memory_entries (type='reflection') |
| **Investor Profile** | Computed aggregate of the investor's judgment quality, process consistency, and growth trajectory | Pure computation (no storage) |

---

## 7. Memory Mapping

### 7.1 How Everything Maps to memory_entries

```
memory_entries (SINGLE TABLE)

  type = 'note'     → Observations, Research, Watchlist, Queue, Inbox
  type = 'thesis'   → Investment thesis with hypothesis tree, evidence, versioning
  type = 'decision' → Structured decisions with pre-flight checks
  type = 'reflection' → Lessons, principles, pattern recognition

Fields used by all types:
  id, type, ticker, title, content, tags, confidence, status
  created_at, updated_at

JSON extension fields (type-specific):
  thesis:   {hypotheses, evidence, version_history, catalysts, risks,
             target_price, timeline, pipeline_snapshot}
  decision: {action, price, quantity, reason, trigger, preflight_checks,
             market_context, mood, invalidation_condition, review_date}
  outcome:  {detail, return_pct, reviewed_at, lesson_tags, principle_updates}
```

### 7.2 Tag Conventions

```
System tags (interpreted by Workspace modules):
  watchlist     → Appears in Investment Universe
  queue         → Appears in Research Queue
  inbox         → Appears in Research Inbox
  priority:high/med/low → Priority level

User tags (free-form, used for analytics):
  Industry:     消费, 科技, 金融, 医疗, 能源, 制造
  Theme:        AI, 新能源, 国产替代, 消费升级, 老龄化
  Strategy:     价值, 成长, 周期, 红利, 事件驱动
  Market:       A股, 港股, 美股
  Outcome:      盈利, 亏损, 持平
  Lesson:       教训, 模式, 原则, 规则更新
```

### 7.3 Design Decision: Why One Table

```
Pros:
  - Zero schema migrations for new features
  - FTS5 search works across all types
  - Relationships via ticker + tags + related_ids
  - Simple backup (one .db file)
  - All analytics query one table

Cons:
  - JSON blobs not queryable via SQL (mitigated by FTS5 + Python filtering)
  - No referential integrity between entries (mitigated by application logic)
  - Schema less self-documenting than separate tables

Decision: One table is correct for a personal tool with <10K entries.
If the system ever needs multi-user or >100K entries, reconsider.
```

---

## 8. Thesis & Hypothesis Model

### 8.1 Thesis Lifecycle

```
FORMING ──→ VALIDATING ──→ ACTIVE ──→ WAITING ──→ COMPLETED
                │                                     │
                │ (pipeline validates                 │ (outcome recorded)
                │  or user confirms)                  │
                │                                     │
                └─────────────────────────────────────┘

Any stage can transition to:
  INVALIDATED — thesis proven wrong or expired
  (never deleted — preserved as learning asset)
```

### 8.2 Hypothesis Tree

A Thesis is a tree of falsifiable sub-claims:

```
Thesis: AI Infrastructure Growth Will Drive NVIDIA Revenue
│
├── H1: Cloud CAPEX continues rising through 2026
│   ├── Evidence: Gartner forecast (+23% YoY)
│   ├── Evidence: AWS/Azure/GCP Q2 earnings calls
│   └── Invalidation: Cloud CAPEX growth drops below 10% for 2 quarters
│
├── H2: GPU demand remains supply-constrained
│   ├── Evidence: TSMC CoWoS fully booked
│   ├── Evidence: H100 lead times still 6-8 months
│   └── Invalidation: Lead times drop below 2 months
│
├── H3: NVIDIA data center revenue continues >50% growth
│   ├── Evidence: Q2 DC revenue +154% YoY
│   └── Invalidation: Two consecutive quarters <30% DC growth
│
└── H4: CUDA ecosystem strengthens monetization
    ├── Evidence: Enterprise AI adoption surveys
    └── Invalidation: Major customer announces CUDA migration
```

### 8.3 Hypothesis Node Model

```python
# Stored in thesis.hypotheses JSON array

{
  "id": "hyp-001",
  "parent_id": None,              # None = root hypothesis
  "description": "Cloud CAPEX continues rising through 2026",
  "confidence": 0.85,             # Independent confidence in this sub-claim
  "status": "active",             # active | invalidated | confirmed
  "supporting_evidence": ["ev-001", "ev-002"],
  "counter_evidence": [],
  "invalidation_condition": "Cloud CAPEX growth <10% for 2 consecutive quarters",
  "last_reviewed": "2026-07-15",
  "created_at": "2026-06-10"
}
```

### 8.4 Thesis Field Specification

```python
# memory_entries row where type = 'thesis'

{
  "type": "thesis",
  "ticker": ["NVDA"],
  "title": "NVIDIA: Core AI Infrastructure Beneficiary",
  "content": "## Investment Logic\n\n...",

  "thesis": {
    "catalysts": ["Inference demand", "Enterprise AI", "Sovereign AI"],
    "risks": ["Valuation", "Competition", "Export controls"],
    "target_price": 1200.0,
    "timeline": "12 months",

    "hypotheses": [
      {  # Hypothesis tree — see 8.3
        "id": "hyp-001",
        "parent_id": None,
        "description": "...",
        "confidence": 0.85,
        "status": "active",
        "invalidation_condition": "...",
        "supporting_evidence": [...],
        "counter_evidence": [...]
      }
    ],

    "evidence": {
      "supporting": [
        {  # See Section 9
          "id": "ev-001",
          "type": "earnings",
          "description": "...",
          "source": "...",
          "reliability": "high",
          "confidence_impact": 0.10
        }
      ],
      "counter": [...]
    },

    "version_history": [
      {  # See Section 8.5
        "version": 1,
        "date": "2026-06-15",
        "confidence": 0.60,
        "change_summary": "Initial thesis",
        "change_type": "creation"
      }
    ],

    "pipeline_snapshot": {...},
    "report_path": "reports/NVDA_20260615.md"
  },

  "confidence": 0.80,
  "status": "active",
  "tags": ["AI", "semiconductor", "美股", "growth"]
}
```

### 8.5 Thesis Version Control

```
Every substantive change to a thesis auto-creates a version record:

Substantive changes:
  - Confidence change > 0.05
  - Hypothesis added/removed/modified
  - Evidence added/removed
  - Catalyst/risk list changed
  - Target price change > 5%
  - Invalidation condition changed

Non-substantive (no version created):
  - Typo fixes
  - Content formatting
  - Tag changes

Version record stored in thesis.version_history:
  {
    "version": N,
    "date": "ISO datetime",
    "previous_confidence": 0.70,
    "new_confidence": 0.80,
    "change_summary": "Q2 earnings beat expectations. Raised conviction.",
    "change_type": "confidence_change",
    "evidence_added": ["ev-003"],
    "evidence_removed": [],
    "hypotheses_changed": ["hyp-002"]
  }

Capabilities:
  - View version history timeline
  - Diff any two versions
  - Restore to previous version (creates a NEW version, not a destructive rollback)
```

---

## 9. Evidence Architecture

### 9.1 Evidence Quality Model

Not all information is equally trustworthy. The system evaluates evidence on four axes:

```
Reliability (1-5):
  5 = Audited financial statement, official government data
  4 = Industry report from reputable source, company guidance
  3 = News from major outlet, sell-side analyst report
  2 = Social media, hearsay, unverified claim
  1 = Rumor, speculation

Timeliness (1-5):
  5 = < 1 week old
  4 = < 1 month old
  3 = < 1 quarter old
  2 = < 1 year old
  1 = > 1 year old

Relevance (1-5):
  5 = Directly proves/disproves a specific hypothesis
  4 = Strongly supports/weakens
  3 = Moderately related
  2 = Tangentially related
  1 = Barely relevant

Independence (1-5):
  5 = Completely independent source, no conflicts of interest
  4 = Independent but possible bias
  3 = Industry source, moderate independence
  2 = Company-provided data (inherent bias)
  1 = Self-referential (using thesis to prove thesis)

Evidence Quality Score = (Reliability × 0.35 + Timeliness × 0.20
                          + Relevance × 0.30 + Independence × 0.15) / 5

Interpretation:
  0.8-1.0: High quality
  0.6-0.8: Moderate quality
  0.4-0.6: Low quality — consider finding better sources
  <0.4:    Unreliable — should not be the sole basis for a decision
```

### 9.2 Evidence Model

```python
# Stored in thesis.evidence.supporting[] and thesis.evidence.counter[]

{
  "id": "ev-001",
  "title": "NVIDIA Q2 DC Revenue +154% YoY",
  "type": "earnings",              # earnings | industry_data | macro | news
                                    # | research | observation | quant_validation
  "source": "NVIDIA Q2 FY2025 Earnings Report",
  "source_date": "2026-07-10",
  "observation_date": "2026-07-10",
  "content": "Data center revenue reached $26.3B, +154% YoY...",
  "reliability": 5,
  "timeliness": 4,
  "relevance": 5,
  "independence": 2,               # Company-reported data has inherent bias
  "confidence_impact": 0.10,       # How this evidence affects thesis confidence
  "linked_ticker": "NVDA",
  "linked_hypothesis": "hyp-003",  # Which hypothesis this supports/counters
  "status": "active"               # active | outdated | superseded
}
```

### 9.3 Evidence-Types

```
Earnings/Financial Reports:
  季度财报、年报、业绩预告

Industry Data:
  行业报告、产业链调研、市场份额数据

Market Data:
  股价、成交量、估值指标、因子数据

Macro Data:
  GDP、CPI、PMI、利率、政策变化

News/Events:
  公司公告、行业新闻、监管变化

Research/Observation:
  自主研究结论、个人观察、专家访谈

Quant Validation:
  V2 pipeline 回测结果、因子分析、策略验证
```

---

## 10. Decision Engine

### 10.1 Decision ≠ Trade Record

A Decision is a **deliberate action with structured rationale and pre-flight checks**. A trade record just says what happened. A decision record says *why*.

### 10.2 Decision Actions

```
WATCH      → Add to active monitoring, no position
RESEARCH   → Begin deep research phase
INITIATE   → Open initial position
ADD        → Increase existing position
REDUCE     → Decrease existing position
EXIT       → Close position entirely
HOLD       → Active decision to maintain position
REJECT     → Active decision NOT to invest (with reasoning)
```

### 10.3 Decision Model

```python
# memory_entries row where type = 'decision'

{
  "type": "decision",
  "ticker": ["NVDA"],
  "title": "Initiate NVDA position",
  "content": "## Decision Rationale\n\n...",

  "decision": {
    "action": "INITIATE",
    "price": 955.0,
    "quantity": 50,
    "target_position_pct": 10.0,

    # Linkage
    "linked_thesis_id": 42,
    "linked_hypotheses": ["hyp-001", "hyp-003"],

    # Rationale
    "reason": "Q2 earnings confirmed DC revenue acceleration. Supply chain verified.",
    "trigger": "Q2 FY2025 Earnings Report beat",

    # Risk parameters
    "invalidation_condition": "DC revenue growth drops below 30% for 2 quarters",
    "stop_loss": 750.0,
    "time_horizon": "12 months",
    "review_date": "2026-10-15",

    # Pre-flight checklist results
    "preflight_checks": {
      "has_valid_thesis": true,
      "has_supporting_evidence": true,
      "has_counter_evidence": true,
      "has_invalidation_condition": true,
      "has_review_date": true,
      "position_matches_confidence": true,
      "no_concentration_breach": false,       # ⚠️ NVDA at 35%
      "concentration_detail": "NVDA would be 35% of portfolio, exceeding 25% limit"
    },

    # Context
    "market_context": "NASDAQ uptrend, AI sentiment elevated, VIX=15",
    "mood": "confident",
    "alternatives_considered": "Waited for pullback. Considered AMD as alternative."
  },

  "confidence": 0.80,
  "status": "active",
  "tags": ["美股", "AI", "INITIATE"]
}
```

### 10.4 Pre-Decision Checklist

```
Before any decision with financial exposure (INITIATE, ADD, REDUCE, EXIT):

  1. Has valid Thesis          → linked_thesis_id must reference active thesis
  2. Has Supporting Evidence   → at least 1 piece in thesis.evidence.supporting
  3. Has Counter Evidence      → at least 1 piece in thesis.evidence.counter
  4. Has Invalidation Condition → decision.invalidation_condition is not empty
  5. Has Review Date            → decision.review_date is set
  6. Position matches Confidence → weight% within bounds for confidence level
  7. No Concentration Breach    → post-decision weight <25% single, <40% sector

System does NOT block decisions that fail checks.
System WARNS and records which checks failed.
The investor decides. The system documents the decision quality.
```

---

## 11. Priority Action Engine

### 11.1 Scoring Formula

```
Priority Score = Urgency × Importance × Relevance × Overdue_Weight

Where:

  Urgency (1-10):
    Based on time sensitivity:
      10 = Event happening today (earnings, catalyst due)
      7  = Overdue > 30 days
      5  = Due within 7 days
      3  = Due within 30 days
      1  = No time pressure

  Importance (1-10):
    Based on financial significance:
      10 = Position > 20% of portfolio, high-conviction thesis
      7  = Position > 10% or thesis confidence > 0.7
      5  = Active thesis with moderate exposure
      3  = Watchlist item, no position
      1  = Informational only

  Relevance (1-10):
    Based on portfolio exposure:
      10 = Directly affects a current position
      5  = Affects a watchlist item with active thesis
      1  = General market context

  Overdue_Weight (1.0-3.0):
    3.0 = > 90 days overdue
    2.0 = > 45 days overdue
    1.5 = > 30 days overdue
    1.0 = Not overdue

Final Score = Urgency × Importance × Relevance × Overdue_Weight
Range: 1 to 3000
```

### 11.2 Action Rules (10 Rules)

```
Rule 1:  STALE THESIS (>45 days without update)
Rule 2:  OVERDUE REVIEW (>30 days without review)
Rule 3:  STALE HIGH-PRIORITY QUEUE ITEM (>5 days)
Rule 4:  UNCOVERED POSITION (position without thesis)
Rule 5:  CONCENTRATION BREACH (>25% single, >40% sector)
Rule 6:  HIGH CONVICTION IDLE (>0.7 conviction, >14 days, no decision)
Rule 7:  DORMANT WATCHLIST (>30 days no activity)
Rule 8:  INVALIDATED THESIS STILL HELD (thesis invalidated, position open)
Rule 9:  CONFLICTING EVIDENCE (new counter-evidence not addressed)
Rule 10: POSITION-CONVICTION MISMATCH (weight >> confidence)
```

### 11.3 Anti-Spam Mechanisms

```
- Max 5 actions displayed in L1 (rest in expandable list)
- Same ticker/thesis: max 1 action per day (merge similar)
- Dismiss: action hidden for N days (user-specified)
- Snooze: action hidden until tomorrow
- Cooldown: same rule won't fire again for 7 days after dismiss
- Completion: action resolved → removed from feed
```

---

## 12. Portfolio Intelligence

### 12.1 Design Principle

Portfolio Intelligence does not show P&L as its primary metric. It shows **why you hold what you hold, and whether those reasons still hold**.

### 12.2 Analysis Dimensions

#### Thesis Coverage
```
For each position:
  Has active thesis (status='active'|'waiting')     → ✅ Covered
  Has thesis but status='correct'|'wrong'           → ⚠️ Expired
  Has thesis but status='invalidated'               → 🔴 Invalidated — review urgently
  No thesis                                          → ❌ Uncovered

Coverage Score = covered / total positions
```

#### Concentration Risk
```
Single position > 35%     → 🔴 Critical
Single position 25-35%    → 🟡 Warning
Single sector > 40%       → 🟡 Warning
Single theme > 50%        → 🟡 Warning (e.g., all "AI" bets)
```

#### Exposure-Conviction Alignment
```
For each position with a thesis:
  confidence > 0.70 AND weight < 10%   → 💡 Underweight relative to conviction
  confidence < 0.50 AND weight > 15%   → ⚠️ Exposure exceeds conviction
  confidence < 0.50 AND weight > 25%   → 🔴 Severe mismatch
  Otherwise                             → ✅ Aligned
```

#### Thesis Freshness
```
For each position with a thesis:
  thesis last updated < 30 days ago   → ✅ Fresh
  thesis last updated 30-60 days ago  → ⚠️ Aging
  thesis last updated > 60 days ago   → 🔴 Stale
```

### 12.3 Data Source

```
V2 trades.db → open positions (read-only)
memory_entries → thesis linkage by ticker

No trade data copied. All analysis is live query.
```

---

## 13. Investor Learning

### 13.1 Design Principle

The system measures **process quality**, not just returns. A lucky win with no thesis is not a "good" outcome. A disciplined loss with clear reasoning IS a learning asset.

### 13.2 Learning Metrics

#### Judgment Quality
```
Thesis Hit Rate (trend over time)
Confidence Calibration Score (0-100, Brier-based)
Profit Factor (avg win / avg loss)
```

#### Decision Discipline
```
Thesis-Backed Decision Ratio (decisions with thesis / total decisions)
Pre-Flight Checklist Completion Rate
Stop-Loss Adherence Rate
Impulse Decision Ratio (decisions without thesis)
```

#### Learning Velocity
```
Lessons Logged per Month
Principles Updated per Quarter
Reflection-to-Thesis Ratio
Invalidated Theses Properly Reviewed
```

#### Process Consistency
```
Streak Days (consecutive days with at least one entry)
Weekly Review Completion Rate
Inbox Triage Regularity (days since last triage)
Thesis Review Rate (% of theses reviewed on schedule)
```

#### Emotional Awareness
```
Decision Quality by Mood
Overconfidence Detection Frequency
Anxious Trading Frequency
```

### 13.3 Investor Profile

Auto-generated from learning metrics. Updates weekly.

```
═══ Investor Profile ═══

Style:        Growth-at-reasonable-price, concentrated (3-5 positions)
Edge:         AI/Technology sector research, supply chain analysis
Weakness:     Cyclical timing, value traps

Calibration:  🟢 Well-calibrated at high confidence (100% hit rate)
              🟡 Overconfident at medium confidence (0% hit rate)
Trend:        ▲ Improving (hit rate: 50% Q1 → 67% Q2 → 75% Q3)

Top Principle: "Only trade conviction > 0.70"
Top Lesson:    "Don't call cycle bottoms — wait for confirmation"
```

---

## 14. Decision Timeline

### 14.1 Design

For any ticker, reconstruct the complete investment journey from memory_entries.

```
Timeline for NVDA:

Jun 10  📰 Market Event
        NVIDIA Q1 earnings highlight AI demand surge

Jun 12  📝 Research Started
        AI GPU Market Analysis note created

Jun 15  💡 Thesis v1 (conf: 0.60)
        NVIDIA: Core AI Infra Beneficiary
        └─ H1: Cloud CAPEX rising
        └─ H2: GPU supply constrained
        └─ H3: DC revenue >50% growth

Jul 10  💡 Thesis v2 (conf: 0.75) 🔺
        Q2 earnings beat. Added evidence from earnings report.
        └─ Evidence added: Q2 DC +154% YoY

Jul 15  📊 Decision: INITIATE
        Buy @ $955 · 50 shares · 10% position
        Pre-flight: 6/7 checks passed (concentration warning)

Aug 01  💡 Thesis v3 (conf: 0.70)
        Added counter-evidence: AMD MI300 hyperscaler adoption

Sep 20  ✅ Outcome: CORRECT (+41%)
        Target reached at $1200

Sep 22  🧠 Reflection
        Pattern: supply chain + earnings confirmation = high-probability setup
        Principle: Verify before entry, don't predict
```

### 14.2 Implementation

```
Timeline is a READ-ONLY aggregated view.
Data: SELECT * FROM memory_entries WHERE ticker LIKE '%{symbol}%' ORDER BY created_at
Thesis version_history entries expand inline.
No new tables. Pure view layer.
```

---

## 15. Information Architecture

### 15.1 Page Hierarchy

```
/workspace             Command Center (default home)
├── L1: Priority Actions (max 5)
├── L2: Thesis Board (4-column kanban) + Portfolio Intelligence
├── L3: Investment Universe + Recent Activity
└── Quick Capture bar (always visible)

/inbox                 Research Inbox
├── Captured items list
├── Triage controls (→Queue, →Thesis, →Archive)
└── Quick Capture bar

/thesis                Thesis Board (full view)
/thesis/<id>           Thesis Detail
├── Thesis content + metadata
├── Hypothesis Tree (collapsible)
├── Evidence Board (supporting + counter)
├── Version History Timeline
└── Linked Decisions

/decision/<id>         Decision Record
├── Decision details + pre-flight results
├── Linked Thesis
└── Outcome (if resolved)

/timeline/<ticker>     Decision Timeline
├── Full journey: Event → Research → Thesis → Decision → Outcome → Reflection
└── Version history inline

/portfolio             Portfolio Intelligence
├── Coverage analysis
├── Concentration check
├── Conviction-Exposure alignment
└── Thesis freshness

/learning              Investor Learning
├── Calibration Dashboard
├── Growth Metrics
├── Investor Profile
└── Principle Library

/journal               Memory Archive (Phase 1)
├── Full timeline search
├── FTS5 query
└── Entry CRUD
```

### 15.2 Global Shell

```
┌──────────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis V3]  Cmd  Inbox  Thesis  Portfolio  Learn  J│
│                                                               │
│  [Global Search: search all memories, theses, tickers...    ] │
│                                                               │
│  ┌─ Notification center (collapsed) ───────────────────────┐ │
│  │  🔴 2 critical  🟡 3 warnings  🟢 5 info               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ═══════════════════ Page Content ═══════════════════════════ │
│                                                               │
│  ...                                                          │
│                                                               │
│  ════════════════════════════════════════════════════════════ │
│                                                               │
│  💡 [Quick Capture: type any idea, ticker, or question...  ] │
│                                                               │
└──────────────────────────────────────────────────────────────┘

Keyboard Shortcuts:
  Ctrl+K  → Global Search
  Ctrl+N  → Quick Capture
  Ctrl+1  → Command Center
  Ctrl+2  → Inbox
  Ctrl+3  → Thesis Board
  Ctrl+4  → Portfolio
  Ctrl+5  → Learning
  Ctrl+J  → Journal
```

---

## 16. Page Structure

*Covered in Section 15. See page hierarchy for all routes.*

---

## 17. API Design

### 17.1 Route Summary

```
Page Routes (serve HTML):
  GET  /workspace              Command Center
  GET  /inbox                  Research Inbox
  GET  /thesis                 Thesis Board
  GET  /thesis/<id>            Thesis Detail
  GET  /decision/<id>          Decision Record
  GET  /timeline/<ticker>      Decision Timeline
  GET  /portfolio              Portfolio Intelligence
  GET  /learning               Investor Learning
  GET  /journal                Memory Archive (Phase 1)

Command Center API:
  GET  /api/workspace/command          Full dashboard data
  GET  /api/workspace/actions          Priority actions
  GET  /api/workspace/universe         Investment universe

Inbox API:
  GET  /api/inbox/list                 Inbox items
  POST /api/inbox/capture              Quick capture
  PUT  /api/inbox/<id>/triage          Triage action

Thesis API:
  GET  /api/thesis/list                All theses (board view)
  GET  /api/thesis/<id>                Thesis detail
  PUT  /api/thesis/<id>                Update thesis
  POST /api/thesis/<id>/evidence       Add evidence
  DELETE /api/thesis/<id>/evidence/<eid> Remove evidence
  GET  /api/thesis/<id>/versions       Version history
  GET  /api/thesis/<id>/timeline       Decision timeline for this ticker

Decision API:
  POST /api/decision/create            Record decision
  GET  /api/decision/<id>              Decision detail
  POST /api/decision/<id>/preflight    Run pre-flight checklist

Portfolio API:
  GET  /api/portfolio/intel            Portfolio intelligence data

Learning API:
  GET  /api/learning/profile           Investor profile
  GET  /api/learning/calibration       Calibration data
  GET  /api/learning/growth            Growth metrics

Journal API (Phase 1, existing):
  GET    /api/memory/list
  GET    /api/memory/search
  POST   /api/memory/create
  GET    /api/memory/<id>
  PUT    /api/memory/<id>
  DELETE /api/memory/<id>
  POST   /api/memory/<id>/review
  GET    /api/memory/analytics
```

### 17.2 Response Format

```
All API endpoints support dual response mode:
  - HTMX request (HX-Request header): returns HTML partial
  - Standard request: returns JSON

Auth: All routes use @token_required (V2 JWT auth)
```

---

## 18. Data Schema

### 18.1 lxl_v3.db (Phase 2 final state)

```sql
-- memory_entries: STILL THE ONLY TABLE
-- All new capabilities stored in JSON blob columns

CREATE TABLE memory_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT    NOT NULL CHECK (type IN (
                   'note', 'thesis', 'decision', 'reflection'
                )),
    ticker      TEXT    NOT NULL DEFAULT '[]',
    title       TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    search_text TEXT    NOT NULL DEFAULT '',

    -- JSON blobs (extended in Phase 2)
    thesis      TEXT,      -- {hypotheses, evidence, version_history, catalysts, risks, ...}
    decision    TEXT,      -- {action, preflight_checks, invalidation_condition, ...}
    outcome     TEXT,      -- {detail, return_pct, reviewed_at, lesson_tags, ...}

    -- Top-level query fields
    confidence  REAL,
    status      TEXT    DEFAULT 'pending',
    tags        TEXT    NOT NULL DEFAULT '[]',

    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT
);

-- FTS5 (unchanged)
CREATE VIRTUAL TABLE memory_entries_fts USING fts5(
    search_text, tags, ticker,
    content='memory_entries', content_rowid='id',
    tokenize='unicode61'
);

-- Triggers (unchanged)
-- INSERT/UPDATE/DELETE triggers keep FTS in sync
```

### 18.2 No New Tables

```
Phase 2 adds zero new database tables.
All new data structures (hypotheses, evidence, version history,
preflight checks, calibration) stored in:
  - thesis JSON blob
  - decision JSON blob
  - outcome JSON blob
  - Pure computation (no storage needed)
```

---

## 19. Error and Edge Cases

### 19.1 Empty States

```
No theses:         "You haven't created any investment theses yet.
                    Start by capturing an idea in the Quick Capture bar."

No decisions:      "No decisions recorded yet.
                    Decisions are created from active theses."

No evidence:       "This thesis has no evidence yet.
                    Add supporting or counter evidence to strengthen your analysis."

No portfolio:      "No open positions found in trades.db.
                    Portfolio Intelligence activates when you have holdings."

No learning data:  "Not enough data for investor learning analysis.
                    Create at least 3 theses with outcomes to see your profile."

All actions clear: "✅ Everything is up to date. No actions needed right now."
```

### 19.2 Error States

```
Database unavailable:
  → Show cached last-known state + "Database connection lost. Retrying..."

V2 trades.db missing:
  → Portfolio section shows "trades.db not found. Portfolio Intelligence unavailable."
  → Rest of Command Center functions normally.

Corrupted thesis JSON:
  → Show "Thesis data could not be parsed" with option to reset to last valid version.

Missing ticker:
  → Gracefully skip that row in Universe display.

Authentication expired:
  → Redirect to /login. Preserve intended destination URL.
```

### 19.3 Edge Cases

```
Multiple theses for same ticker:
  → Show all, ordered by status (active first) then created_at DESC

Thesis with no hypotheses:
  → Show "No hypothesis tree defined. Add sub-claims to structure your thesis."

Decision without linked thesis:
  → Flag as "impulse decision" in analytics. No pre-flight checks possible.

Very large evidence list (>20 items):
  → Paginate. Show top 5 most recent, rest behind "Show all".

Portfolio position with multiple tickers:
  → Match against all tickers in thesis.ticker[].

Version history with 50+ versions:
  → Collapse to version list. Expand individual versions on click.
```

---

## 20. Development Phases

```
Phase 1: ✅ COMPLETE — Investment Memory System
  MemoryEntry model, SQLite persistence, FTS5 search,
  MemoryAnalytics, Journal UI, Showcase Release

Phase 2A: Foundation (Commits 7-11, ~2 weeks)
  Market Context, Investment Universe, Action Center,
  Research Inbox, Thesis Board, Portfolio Intelligence,
  Investor Learning, Command Center UI

Phase 2B: Cognitive Layer (Commits 12-16, ~1.5 weeks)
  Evidence Architecture, Thesis Versioning,
  Decision Timeline, Calibration Engine, Growth Metrics

Phase 2C: Decision Engine (Commits 17-19, ~1 week)
  Hypothesis Tree, Decision Engine with Pre-flight Checks,
  Investment Checklist

Phase 2D: Integration (Commits 20-22, ~1 week)
  Global Shell, Keyboard Shortcuts, Notification Center,
  End-to-end Tests, Performance Optimization, Documentation

Duration: Phase 2 total ~5.5 weeks (can be parallelized to 3-4 weeks)
```

---

## 21. Git Commit Plan

```
Phase 2A: Foundation (7 commits)
  Commit  7: feat(workspace): add market context + investment universe
  Commit  8: feat(workspace): add action center + research inbox
  Commit  9: feat(workspace): add thesis board
  Commit 10: feat(workspace): add portfolio intelligence + investor learning
  Commit 11: feat(workspace): add command center UI shell

Phase 2B: Cognitive Layer (5 commits)
  Commit 12: feat(workspace): add evidence architecture
  Commit 13: feat(workspace): add thesis version system
  Commit 14: feat(workspace): add decision timeline model
  Commit 15: feat(workspace): add conviction calibration engine
  Commit 16: feat(workspace): add investor growth metrics

Phase 2C: Decision Engine (3 commits)
  Commit 17: feat(workspace): add hypothesis tree engine
  Commit 18: feat(workspace): add decision engine with pre-flight checks
  Commit 19: feat(workspace): add investment checklist

Phase 2D: Integration (3 commits)
  Commit 20: feat(workspace): add global shell + keyboard shortcuts
  Commit 21: feat(workspace): add notification center
  Commit 22: test(workspace): add end-to-end integration tests

Total: 22 commits (16 from Phase 2 + 6 from Phase 1)
```

---

## 22. Acceptance Criteria

### 22.1 Functional

```
F1:  /workspace loads as default home page
F2:  Priority Actions show ≤5 items, sorted by priority score
F3:  Action Center correctly applies all 10 rules
F4:  Quick Capture creates inbox entry with zero friction
F5:  Inbox triage correctly converts to queue/thesis/archive
F6:  Thesis Board shows 4 columns with correct classification
F7:  Hypothesis tree renders correctly with parent/child relationships
F8:  Evidence can be added to any hypothesis with quality scores
F9:  Evidence quality score computes correctly
F10: Thesis version auto-created on substantive change
F11: Version history shows diff between any two versions
F12: Decision pre-flight checklist runs all 7 checks
F13: Pre-flight warnings display without blocking decision creation
F14: Portfolio Intelligence shows coverage, concentration, alignment
F15: Investor Learning profile auto-generates from data
F16: Calibration score computes correctly (Brier-based)
F17: Decision Timeline reconstructs complete ticker journey
F18: All 10 sections of global shell render consistently
F19: Keyboard shortcuts work on all pages
F20: FTS5 search returns results across all memory types
```

### 22.2 Non-Functional

```
NF1: Zero new pip dependencies
NF2: V2 400+ tests continue to pass
NF3: No new database tables created
NF4: All SQL uses parameterized queries (no injection)
NF5: ruff clean (zero lint errors)
NF6: All new code has type hints
NF7: Page load < 2s (16-entry dataset)
NF8: Search response < 100ms
NF9: Works with existing lxl_v3.db (backward compatible)
```

---

## 23. Explicit Non-goals

```
V3 will NOT:

❌ Predict stock prices
❌ Execute trades automatically
❌ Provide real-time streaming market data
❌ Replace Bloomberg/TradingView/Notion
❌ Support multi-user or team collaboration
❌ Offer mobile apps (responsive web only)
❌ Include social features or sharing
❌ Support cryptocurrency or forex (equity-focused)
❌ Implement AI agents that make autonomous decisions
❌ Create new database tables beyond memory_entries
❌ Migrate from Flask to FastAPI
❌ Add Redis, Docker, or Kubernetes
❌ Implement OAuth/SSO (password auth only)
```

---

## 24. V3/V4 Boundary

### 24.1 V3 Scope (This Document)

```
✅ Command Center with Priority Actions
✅ Investment Memory (4 types + FTS5)
✅ Thesis Engine with Hypothesis Tree
✅ Evidence Architecture with Quality Scoring
✅ Thesis Version Control
✅ Decision Engine with Pre-Flight Checklist
✅ Portfolio Intelligence (read-only analysis)
✅ Investor Learning with Calibration
✅ Decision Timeline per Ticker
✅ Research Inbox with Triage
✅ Global Shell + Keyboard Shortcuts
✅ Quick Capture
```

### 24.2 V4 Scope (Future)

```
⏳ Multi-Agent Investment Committee
⏳ Autonomous Research Agents
⏳ Real-time News Integration + NLP
⏳ Advanced Risk Models (factor-based VaR)
⏳ Full Point-in-Time Data Portal
⏳ Knowledge Graph Database
⏳ Team Collaboration + RBAC
⏳ Mobile Applications
⏳ Broker API Integration (read-only execution)
⏳ Automated Portfolio Rebalancing
⏳ External Data Provider Plugins
```

---

## Appendix A: Current Foundation Audit

### A.1 What to Keep (from current Workspace Foundation)

```
✅ src/v3/workspace/repository.py
   MemoryAdapter — tag-convention queries over memory_entries
   PortfolioAdapter — read-only V2 trades.db access
   → KEEP. Core data access layer. Add new query methods as needed.

✅ src/v3/workspace/service.py
   WorkspaceService — data aggregation
   → KEEP. Extend with new methods for each module.

✅ src/v3/workspace/routes.py
   Existing API routes
   → KEEP all existing routes. Add new routes for new modules.

✅ src/v3/workspace/__init__.py
   Blueprint registration
   → KEEP. No changes needed.

✅ templates/v3/workspace.html
   Current dashboard layout
   → REWRITE. Replace flat layout with 3-row Command Center layout.

✅ templates/v3/partials/workspace_*.html
   Existing HTMX partials
   → KEEP as fallback. Add new partials for new modules.
```

### A.2 What to Modify

```
⚠️ workspace.html → Complete rewrite for Command Center layout
⚠️ service.py → Add 10+ new methods for new modules
⚠️ routes.py → Add ~25 new routes
⚠️ web_modern.py → Add blueprint registrations (+4 lines)
```

### A.3 What to Delete/Deprecate

```
❌ None. All existing code paths remain functional.
   New features are additive.
```

---

## Appendix B: Data Migration Risk Assessment

### B.1 Risk: JSON Schema Evolution

```
Risk:      thesis/decision/outcome JSON structure changes
Impact:    Old entries may not render correctly in new UI
Mitigation: All JSON readers use .get() with defaults.
            Missing keys → show "Not available" in UI.
            Never fail on missing JSON keys.

Severity:  LOW
```

### B.2 Risk: Tag Convention Collision

```
Risk:      User tags accidentally match system tags (watchlist, queue, inbox)
Impact:    User's note appears in Workspace modules unexpectedly
Mitigation: System tags are prefixed or reserved.
            User cannot create tags starting with "sys:".

Severity:  LOW
```

### B.3 Risk: V2 trades.db Schema Change

```
Risk:      V2 update changes trades table structure
Impact:    PortfolioAdapter queries fail
Mitigation: PortfolioAdapter uses defensive column access.
            Catches sqlite3.OperationalError and returns empty state.

Severity:  LOW
```

---

## Appendix C: Minimum Viable Scope

### C.1 If Time is Constrained

Priority order for implementation:

```
P0 (MUST HAVE — no Command Center without these):
  - Priority Action Engine (Commit 8)
  - Thesis Board (Commit 9)
  - Command Center UI Shell (Commit 11)

P1 (HIGH — core investor value):
  - Portfolio Intelligence (Commit 10)
  - Evidence Architecture (Commit 12)
  - Decision Engine (Commit 18)

P2 (MEDIUM — significant differentiation):
  - Hypothesis Tree (Commit 17)
  - Conviction Calibration (Commit 15)
  - Decision Timeline (Commit 14)
  - Investor Learning (Commit 16)

P3 (ENHANCEMENT — nice to have):
  - Thesis Versioning (Commit 13)
  - Investment Universe (Commit 7)
  - Market Context (Commit 7)
  - Research Inbox (Commit 8)

P4 (POLISH):
  - Global Shell + Keyboard Shortcuts (Commit 20)
  - Notification Center (Commit 21)
  - Growth Metrics (Commit 16)
```

---

> **ARCHITECTURE FROZEN.**
> **This document is the single authoritative source for V3 implementation.**
> **No further design changes without explicit review.**
> **Next: Architecture review → Approval → Begin Commit 7 implementation.**
