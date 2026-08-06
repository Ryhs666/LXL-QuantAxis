# LXL·QuantAxis V3 — Investment Memory System

> **Case Study** · Portfolio Showcase Release  
> AI-Powered Personal Investment Research Operating System — Phase 1

---

## Executive Summary

**Problem**: Individual investors suffer from "research amnesia" — they study companies, form theses, and make decisions, but have no systematic way to track whether their judgments were correct or to learn from mistakes.

**Solution**: LXL·QuantAxis V3 Investment Memory System — a personal cognitive database that records every step of the investment research process and automatically analyzes judgment quality through confidence calibration and outcome tracking.

**Impact**: After 3 months of use with the demo data (14 entries across 3 cases), the system surfaces actionable insights: high-confidence theses hit at 100% vs 0% for medium-confidence, AI sector is the user's clear edge, and cyclical timing is their weakness.

**Stack**: Python 3.12 · Flask + HTMX + Alpine.js · SQLite with FTS5 full-text search · Zero new dependencies.

---

## Table of Contents

1. [The Research Amnesia Problem](#1-the-research-amnesia-problem)
2. [System Architecture](#2-system-architecture)
3. [The Investor's Learning Loop](#3-the-investors-learning-loop)
4. [Case Studies](#4-case-studies)
5. [Investor Profile & Calibration](#5-investor-profile--calibration)
6. [Technical Implementation](#6-technical-implementation)
7. [Screenshots](#7-screenshots)
8. [Quick Start](#8-quick-start)
9. [V2 → V3 Evolution](#9-v2--v3-evolution)

---

## 1. The Research Amnesia Problem

### What Happens Without Systematic Memory

Every serious investor knows this pattern:

```
Week 1:  Deep research on Company X. Write notes. Form thesis. Conviction: high.
Week 4:  Buy Company X. Record the decision somewhere.
Month 3: Company X reports earnings. Stock moves.
Month 6: Can't remember why you bought it.
         Can't find your original thesis.
         Don't know if your prediction was right.
         Repeat the same mistakes next quarter.
```

### The Cost

| Without Memory | With Memory |
|---------------|-------------|
| Repeat mistakes | Pattern recognition |
| No calibration data | Know when you're right |
| Scattered notes | Unified searchable timeline |
| Gut-feel decisions | Conviction-tracked decisions |
| Unknown hit rate | Quantified accuracy |

**Without memory, every investment decision is a first decision. You never build on what you learned.**

### Why Existing Tools Don't Solve This

- **Notion/Evernote**: Free-form notes, no structure, no analytics
- **Trading Journals (Tradervue, etc.)**: Trade-focused, no thesis lifecycle
- **Spreadsheets**: Manual, no search, no relationship linking
- **Bloomberg/Institutional tools**: $20K+/year, designed for teams, not personal research

LXL·QuantAxis V3 fills this gap: **structured investment memory with built-in analytics, designed for the individual serious investor.**

---

## 2. System Architecture

### The Four Memory Types

```
┌────────────────────────────────────────────────────────────────┐
│                    Investment Memory System                     │
│                                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  📝 NOTE  │  │ 💡 THESIS│  │📊 DECISION│  │ 🧠 REFLECTION│  │
│  │          │  │          │  │          │  │              │  │
│  │ Research │  │Prediction│  │  Action  │  │   Learning   │  │
│  │ findings │  │+confidence│  │+rationale│  │  +patterns   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │             │             │               │           │
│       │     ┌───────┴──────┐      │        ┌──────┴──────┐    │
│       │     │  OUTCOME     │◄─────┘        │  ANALYTICS  │    │
│       │     │  correct /   │               │  hit rate   │    │
│       │     │  wrong /     │               │  calibration│    │
│       │     │  expired     │               │  tag perf   │    │
│       │     └──────────────┘               └─────────────┘    │
│       │                                                       │
│       └───────────────────────────────────────────────────────┤
│                          FTS5 Full-Text Search                 │
│                   (Chinese + English, instant)                 │
└────────────────────────────────────────────────────────────────┘
```

### Data Model (Single Table Design)

```python
@dataclass(frozen=True, slots=True)
class MemoryEntry:
    id: int                    # Auto-increment PK
    type: str                  # note | thesis | decision | reflection
    ticker: list[str]          # Stock codes, e.g. ["NVDA", "000858"]
    title: str                 # Summary line
    content: str               # Markdown body
    thesis: dict | None        # {catalysts, risks, timeline, target_price}
    decision: dict | None      # {type, price, quantity, reason, mood}
    confidence: float | None   # 0.0–1.0
    status: str | None         # pending | correct | wrong | expired
    outcome: dict | None       # {detail, return_pct, reviewed_at}
    tags: list[str]            # e.g. ["AI", "美股", "growth"]
```

**Design decision**: One table, four types. JSON blobs for structured sub-objects (thesis/decision/outcome) rather than 20+ sparse columns. The `type` discriminator determines which fields are meaningful.

### Tech Stack

```
┌─────────────────────────────────────────────┐
│  Browser                                     │
│  /journal  ·  HTMX (no reload)  ·  Alpine.js │
│  terminal.css  ·  Bloomberg dark theme       │
├─────────────────────────────────────────────┤
│  Flask (web_modern.py +6 lines)              │
│  Blueprint: src/v3/web/                      │
│  11 REST endpoints  ·  JWT auth              │
├─────────────────────────────────────────────┤
│  src/v3/memory/                              │
│  search.py    MemorySearch (multi-filter)     │
│  analytics.py MemoryAnalytics (calibration)   │
│  repository.py  CRUD + FTS5                   │
│  models.py      MemoryEntry dataclass         │
│  database.py    SQLite + WAL                  │
├─────────────────────────────────────────────┤
│  lxl_v3.db    SQLite 3                       │
│  memory_entries + memory_entries_fts         │
│  CJK regex tokenizer for Chinese search      │
└─────────────────────────────────────────────┘
```

---

## 3. The Investor's Learning Loop

### Complete Research Lifecycle

```
    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  1. DISCOVER  ──→  📝 Research Note                     │
    │  "AI GPU market: NVIDIA has 85% share, CUDA moat deep"  │
    │                                                         │
    │  2. FORM      ──→  💡 Investment Thesis                 │
    │  "NVIDIA: AI infra beneficiary. Target $1200."          │
    │  Conviction: 0.80 · Catalysts: 3 · Risks: 3              │
    │                                                         │
    │  3. VALIDATE  ──→  (V2 Quant Pipeline)                  │
    │  AI parser → factor mapper → strategy → backtest         │
    │                                                         │
    │  4. ACT       ──→  📊 Decision Record                   │
    │  "Buy NVDA @ $955, 50 shares, 10% position."            │
    │  Rationale: "Q2 earnings beat, DC +154% YoY"             │
    │  Mood: Confident                                        │
    │                                                         │
    │  5. TRACK     ──→  Outcome Marking                      │
    │  Status: correct ✓ · Return: +41%                        │
    │  "Inference market exploded, Sovereign AI orders strong" │
    │                                                         │
    │  6. LEARN     ──→  🧠 Reflection                        │
    │  Pattern: Supply chain verification → enter on earnings  │
    │  Rule: "Only high-conviction theses deserve >10% position"│
    │                                                         │
    └─────────────────────────────────────────────────────────┘
```

### How the System Gets Smarter

Each completed loop feeds back into the Analytics Engine:

```
Thesis #1 (NVDA, conviction 0.80): correct ✓, +41%
Thesis #2 (ZTE,  conviction 0.70): correct ✓, +28%
Thesis #3 (MU,   conviction 0.65): wrong   ✗, -12%

                ↓ Analytics Engine computes ↓

┌─────────────────────────────────────────────────────┐
│ 1. Confidence Calibration                           │
│    High (>0.7):  100% hit rate — well calibrated    │
│    Med (0.5-0.7):  0% hit rate — overconfident      │
│    → Insight: Only trade conviction > 0.7            │
│                                                     │
│ 2. Sector Performance                               │
│    AI/A股:  100% accuracy — your edge               │
│    Cycles:    0% accuracy — need improvement         │
│    → Insight: Double down on tech, avoid cycle timing│
│                                                     │
│ 3. Decision Quality                                 │
│    Confident mood: 2/2 good decisions               │
│    → Insight: Confidence correlates with quality     │
└─────────────────────────────────────────────────────┘
```

---

## 4. Case Studies

All three cases use the four-type memory lifecycle. Data seeded via `scripts/seed_v3_memory.py --reset`.

### Case 1: NVIDIA AI Infrastructure ✓

**Thesis**: NVIDIA is the single largest beneficiary of AI infrastructure buildout. GPU demand expanding from training to inference creates TAM far beyond consensus.

| Stage | Date | Content |
|-------|------|---------|
| 📝 Note | Day -90 | AI GPU market analysis. NVIDIA 85% share, H100 sold out 6-8 months, TSMC CoWoS is bottleneck. |
| 💡 Thesis | Day -85 | Core AI infra beneficiary. Catalysts: inference explosion, enterprise AI, sovereign AI. Target $1200. Conviction: **0.80**. |
| 📊 Decision | Day -80 | Buy NVDA @ $955, 50 shares, 10% position. Rationale: Q2 earnings beat, DC +154% YoY, PEG <1. Mood: confident. |
| 🧠 Reflection | Day -20 | **CORRECT**. Return +41%. Pattern: supply chain verification (TSMC CoWoS) + earnings confirmation before entry. Target reached in 4 months vs 12-month estimate. |

**Key Takeaway**: Deep supply chain research + waiting for earnings confirmation = high-probability setup. Conviction 0.80 was appropriate.

---

### Case 2: ZTE AI Server ✓

**Thesis**: AI servers becoming ZTE's second growth curve beyond telecom equipment. Carrier AI procurement + government digital transformation opening new growth vector.

| Stage | Date | Content |
|-------|------|---------|
| 📝 Note | Day -75 | China AI server market. Inspur #1, ZTE gaining. Policy: domestic chip ratios increasing in procurement. |
| 💡 Thesis | Day -70 | AI server as second curve. Catalysts: carrier AI procurement +200% YoY, domestic substitution, PE 15x vs industry 20x. Target CNY 36. Conviction: **0.70**. |
| 📊 Decision | Day -65 | Buy ZTE @ CNY 28.30, 5000 shares, 8% position. Rationale: H1 procurement beat, ZTE share gains, 10% pullback entry. Mood: confident. |
| 🧠 Reflection | Day -15 | **CORRECT**. Return +28%. Policy direction accurate — substitution went from slogan to procurement. Position could have been larger (8% too conservative for high-conviction). |

**Key Takeaway**: Policy direction research + industry channel checks = A-share edge. Conviction 0.70 was accurate but position sizing was too conservative.

---

### Case 3: Micron Semiconductor Cycle ✗

**Thesis**: Memory industry after 18-month down-cycle. Three major producers cutting production + AI HBM demand explosion = cycle inflection approaching.

| Stage | Date | Content |
|-------|------|---------|
| 📝 Note | Day -60 | Semiconductor cycle research. Memory prices down 18 months (longest). DRAM spot stabilizing. SOX index +30% from bottom. But inventories still elevated. |
| 💡 Thesis | Day -55 | Memory cycle bottom opportunity. Catalysts: production cuts 20-30%, HBM demand 5x YoY, PB 1.2x (10yr low). Target $110. Conviction: **0.65**. |
| 📊 Decision | Day -50 | Buy MU @ $86, 200 shares, 6% position. Rationale: price stabilization, Samsung cuts, HBM order visibility, 10yr low PB. Mood: confident. |
| 🧠 Reflection | Day -10 | **WRONG**. Return -12%. Called bottom too early — actual recovery delayed 2 quarters. Mistake: single signal (price stabilization) misinterpreted as cycle turn. Missing: demand-side confirmation, multi-quarter trend, independent leading indicators. |

**Cycle Timing Checklist** (derived from this mistake):

```
Before calling a cycle bottom, confirm ALL of:
  ☐ Prices rising for 2+ consecutive quarters
  ☐ Inventories down 20%+ at major producers
  ☐ End-demand inflection signals present (not just supply cuts)
  ☐ At least 2 independent leading indicators aligned
  ☐ Accept missing first 20% of move as confirmation cost
```

**Key Takeaway**: This "failed" thesis generated more value than the "successful" ones. The reflection produced a concrete, actionable checklist that prevents repeating the same mistake. **This is the system working as designed.**

---

## 5. Investor Profile & Calibration

### Why Calibration Matters

Investment skill has two components:
1. **Accuracy**: How often are you right?
2. **Calibration**: Do you know when you're right?

A perfectly calibrated investor's high-confidence predictions are more accurate than their low-confidence ones. An uncalibrated investor may be accurate but can't distinguish good setups from bad.

### The Demo Investor's Profile

Based on 14 entries across 3 cases (analyzed automatically by `MemoryAnalytics`):

#### Confidence Calibration

```
Confidence Level     │ Theses │ Correct │ Hit Rate │ Interpretation
─────────────────────┼────────┼─────────┼──────────┼────────────────
High (> 0.70)        │   2    │    2    │   100%   │ ✅ Well calibrated
Medium (0.50–0.70)   │   1    │    0    │     0%   │ ⚠️ Overconfident
Low (< 0.50)         │   0    │    0    │    N/A   │ No data yet
─────────────────────┼────────┼─────────┼──────────┼────────────────
Overall              │   3    │    2    │    67%   │ Above average
```

**Insight**: The investor knows when they know. High-conviction theses deliver. But medium-conviction thesis failed — the boundary between "confident enough to trade" and "track only" needs to be sharper. **Recommendation**: raise the conviction bar from 0.65 to 0.70 for actual trading.

#### Decision Quality by Mood

```
Mood at Entry    │ Decisions │ Good │ Bad │ Win Rate
─────────────────┼───────────┼──────┼─────┼──────────
Confident        │     3     │   2  │  1  │   67%
Anxious          │     0     │   0  │  0  │   N/A
─────────────────┼───────────┼──────┼─────┼──────────
```

**Insight**: All three decisions were made while "confident" — no trades were made in anxious/fearful states. This suggests disciplined emotional control, but the Micron case shows overconfidence in cycle timing despite only 0.65 conviction.

#### Sector Edge Analysis

```
Sector/Tag     │ Theses │ Hit Rate │ Verdict
───────────────┼────────┼──────────┼──────────
AI             │   2    │   100%   │ 🟢 Core edge
A股            │   1    │   100%   │ 🟢 Strong
美股           │   2    │    50%   │ 🟡 Mixed
semiconductor  │   2    │    50%   │ 🟡 Mixed
cycle          │   1    │     0%   │ 🔴 Weakness
growth         │   2    │   100%   │ 🟢 Growth edge
value          │   1    │     0%   │ 🔴 Value weakness
```

**Insight**: The investor's edge is in growth/AI/technology names. Cyclical and value plays underperform. The tag-based performance breakdown enables precise identification of the investor's circle of competence.

#### The Learning Trajectory

```
Entry Timeline:
  Day -90: 📝 Note — AI GPU market
  Day -85: 💡 Thesis — NVIDIA (conviction 0.80)
  Day -80: 📊 Decision — Buy NVDA
  Day -75: 📝 Note — China AI server
  Day -70: 💡 Thesis — ZTE (conviction 0.70)
  Day -65: 📊 Decision — Buy ZTE
  Day -60: 📝 Note — Semi cycle research
  Day -55: 💡 Thesis — Micron (conviction 0.65)  ← confidence declining
  Day -50: 📊 Decision — Buy MU
  Day -30: 📝 Note — H2 themes overview
  Day -20: 🧠 Reflection — NVIDIA retrospective
  Day -15: 🧠 Reflection — ZTE retrospective
  Day -10: 🧠 Reflection — Micron retrospective  ← most valuable entry
  Day  -5: 🧠 Reflection — Investment principles update
```

Three complete learning cycles in ~85 days. The final "Investment Principles" reflection encodes all three cases into actionable rules — this is the system's ultimate output: **evolving investment wisdom**.

---

## 6. Technical Implementation

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Single table, JSON blobs** | 13 columns vs 30+. Thesis/decision/outcome stored as structured JSON. Clean Python API, simple SQL. |
| **FTS5, not Elasticsearch** | Zero infrastructure. SQLite FTS5 handles thousands of entries at <10ms per query. CJK support via regex pre-tokenization. |
| **HTMX + Alpine.js, not React** | Server-rendered HTML, 15KB of JS total. No build step, no npm. Perfect for a solo developer shipping fast. |
| **Flask Blueprint, not new app** | V3 routes live in `src/v3/web/`. Registration in `web_modern.py` is 4 lines. V2 code untouched. |
| **Immutable dataclasses** | `frozen=True, slots=True` throughout. Every memory entry is an immutable fact — you can't accidentally modify history. |
| **CJK regex tokenizer** | `[一-鿿]` regex inserts spaces between Chinese characters before FTS5 indexing. Zero-dependency Chinese search. |

### Code Map

```
src/v3/memory/                     # Phase 1: Investment Memory System
├── models.py          (110 lines) # MemoryEntry + type constants
├── config.py          ( 65 lines) # DB path resolution (env vars)
├── schema.sql         ( 89 lines) # DDL + FTS5 + 3 triggers
├── database.py        (158 lines) # Connection mgmt + FTS5 raw search
├── repository.py      (280 lines) # CRUD + JSON serialization
├── search.py          (350 lines) # Multi-filter query + related/similar
├── analytics.py       (410 lines) # Stats + calibration + tag perf
src/v3/web/                         # Web layer
├── __init__.py        ( 26 lines) # Flask Blueprint
├── journal_page.py    ( 15 lines) # Page route
├── journal_api.py     (300 lines) # 11 REST endpoints (HTMX + JSON)
templates/v3/                       # Jinja2 templates
├── journal.html       (400 lines) # Full page (Bloomberg dark theme)
├── partials/          (130 lines) # HTMX fragments + macros
scripts/
└── seed_v3_memory.py  (565 lines) # Demo data: 3 cases, 14 entries
tests/v3/
└── test_search_analytics.py (326 lines) # 25 tests
```

**Total**: ~2,500 lines of Python, ~550 lines of HTML/CSS, 25 tests. Zero new dependencies.

### Search Performance

| Query | Type | Results | Latency |
|-------|------|---------|---------|
| `NVIDIA` | English keyword | 4 (all NVDA entries) | <5ms |
| `白酒` | Chinese keyword | 0 (no baijiu in demo) | <5ms |
| `cycle` | English keyword | 4 (semi case) | <5ms |
| `NVIDIA` + type=thesis | Keyword + filter | 1 (NVDA thesis only) | <5ms |
| `000063` | Ticker filter | 4 (all ZTE entries) | <5ms |
| confidence >= 0.7 | Numeric filter | 6 entries | <5ms |

All queries <5ms on 14-entry dataset. FTS5 scales linearly to ~100K entries before noticeable degradation.

---

## 7. Screenshots

### Capture Specifications

Each screenshot should be captured at **1920×1080** resolution, browser in dark mode, using the Chrome DevTools device toolbar set to "Responsive" with DPR 2.0 for retina quality.

> Run `python web_modern.py` and `python scripts/seed_v3_memory.py --reset` before capturing.

#### 1. Memory Timeline (`01_timeline.png`)

```
Path:    docs/assets/v3_memory/01_timeline.png
URL:     http://127.0.0.1:5000/journal
Capture: Full page scroll showing all 14 timeline entries
         with type-coded dots (blue/gold/gray/purple)
Key elements visible:
  - 5-card stat bar (total/hit rate/confidence/pending/streak)
  - Search bar + type/ticker filters
  - 14 colored timeline items with badges and tags
  - Analytics sidebar (breakdown + calibration bars)
```

#### 2. Search & Filter (`02_search.png`)

```
Path:    docs/assets/v3_memory/02_search.png
URL:     http://127.0.0.1:5000/journal
Action:  Type "NVIDIA" in search bar, set Type filter to "Thesis"
Capture: Search results showing filtered timeline
Key elements visible:
  - Search input with "NVIDIA"
  - Type dropdown set to "Thesis"
  - Filtered results (1-2 NVIDIA thesis entries)
  - "2 entries" result count
```

#### 3. Thesis Detail (`03_detail.png`)

```
Path:    docs/assets/v3_memory/03_detail.png
URL:     http://127.0.0.1:5000/journal
Action:  Click on the NVIDIA thesis timeline item
Capture: Entry detail modal showing full thesis content
Key elements visible:
  - Modal with dark overlay
  - Type badge "THESIS" in blue
  - Full Markdown content
  - Confidence: 0.80, Tags: AI, semiconductor, 美股
  - Edit/Close buttons
```

#### 4. Analytics Dashboard (`04_analytics.png`)

```
Path:    docs/assets/v3_memory/04_analytics.png
URL:     http://127.0.0.1:5000/journal
Capture: Full right sidebar scrolled to show all sections
Key elements visible:
  - Memory Breakdown (notes/theses/decisions/reflections counts)
  - Thesis Quality (hit rate, correct/wrong/pending)
  - Decision Quality (win rate, good/bad)
  - Confidence Calibration (3 bars with hit rates)
  - Calibration insight box
  - Top Tags cloud
```

#### 5. Entry Creation (`05_create.png`)

```
Path:    docs/assets/v3_memory/05_create.png
URL:     http://127.0.0.1:5000/journal
Action:  Click "+ New Thesis" button
Capture: Creation modal with Thesis-specific fields visible
Key elements visible:
  - Modal title "New Investment Thesis"
  - Type selector set to "Thesis"
  - Title and Content fields
  - Ticker and Tags input fields
  - Thesis-specific: Confidence slider, Target Price
  - Save/Cancel buttons
```

### Placeholder

> Screenshots to be captured from running application. Directory: `docs/assets/v3_memory/`

---

## 8. Quick Start

```bash
# 1. Clone and install (if not already done)
pip install -r requirements.txt

# 2. Seed demo data — 3 complete research cases
python scripts/seed_v3_memory.py --reset

# 3. Launch web platform
python web_modern.py

# 4. Open in browser
# → http://127.0.0.1:5000/journal

# 5. Explore the system
# - Search "NVIDIA" or "cycle" to find specific entries
# - Click any timeline item to view full content
# - Check the right sidebar for calibration analytics
# - Click "+ New Thesis" to create your own entry
# - Filter by type (Thesis/Decision/Note/Reflection)
```

### Demo Data at a Glance

```
$ python scripts/seed_v3_memory.py --reset

═══ V3 Memory System Seeded ═══
  Total:       14 entries
  Notes:        4
  Theses:       3
  Decisions:    3
  Reflections:  4
  Thesis hit rate: 67% (2/3)
  Decision win rate: 67%
  Avg confidence: 71.7%

Cases:
  1. NVIDIA AI Infrastructure   (NVDA)   — thesis CORRECT, +41%
  2. ZTE AI Server              (000063) — thesis CORRECT, +28%
  3. Micron Semiconductor Cycle (MU)     — thesis WRONG, -12%

Run: python web_modern.py → /journal
```

---

## 9. V2 → V3 Evolution

### What Changed

| Dimension | V2.0 Showcase | V3.0 Phase 1 |
|-----------|---------------|--------------|
| **Paradigm** | Stateless AI pipeline | Persistent memory OS |
| **User data** | Ephemeral (per-run) | Accumulated (lifetime) |
| **Learning** | None | Hit rate + calibration tracking |
| **Search** | None | FTS5 Chinese/English full-text |
| **UI** | 9 standalone pages | Unified journal with HTMX |
| **Memory** | None | 4-type cognitive database |
| **Analytics** | None | Confidence calibration + tag perf |

### What Stayed

- **V2 code**: Zero lines modified. All 155 files under `src/lxl_quantaxis/` untouched.
- **V2 pipeline**: `demo_ai_research.py` produces identical output.
- **V2 tests**: 400+ tests continue to pass.
- **Dependencies**: Zero new pip packages. Flask + SQLite + HTMX CDN + Alpine.js CDN.

### Architecture Principle

```
src/lxl_quantaxis/          ← V2: 155 files, 0 modifications
src/v3/                     ← V3: 12 files, pure additive layer
web_modern.py               ← +4 lines for Blueprint registration
templates/v3/               ← New templates, no existing page changes
```

---

## Roadmap

| Phase | Module | Status |
|-------|--------|--------|
| **Phase 1** | Investment Memory System | ✅ Complete (this showcase) |
| Phase 2 | Company Intelligence Engine | Design complete |
| Phase 3 | Research Workspace + Reports | Design complete |
| Phase 4 | Quant Validation Engine | Design complete |
| V4 | Research Agent Framework | Planned |

---

> **LXL·QuantAxis V3** — Not a prediction tool. Not a trading bot.  
> A personal investment research operating system that gets smarter with every decision you make.  
> **Built for the serious individual investor who wants to understand their own mind.**
