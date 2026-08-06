# V3 Investment Memory System — Showcase

> **LXL·QuantAxis V3.0** — AI-Powered Personal Investment Research Operating System  
> Phase 1: Investment Memory System · First Demo Release

---

## Problem

### The Investment Research Amnesia Problem

Every serious investor has experienced this:

- You research a stock thoroughly, write notes, form a thesis
- Months later, you can't remember *why* you bought it
- You don't know which of your past predictions were right or wrong
- Your investment lessons are scattered across notebooks, spreadsheets, and chat logs
- You have no systematic way to track if your judgment is improving

**Without memory, every investment decision is a first decision.**

---

## Solution

### LXL·QuantAxis V3 Investment Memory System

A **personal investment cognitive database** that records your entire research process and tracks your judgment quality over time.

Four memory types in one unified system:

| Type | Icon | Purpose | Example |
|------|------|---------|---------|
| **Research Note** | 📝 | Market/industry research | "AI GPU market analysis" |
| **Investment Thesis** | 💡 | Structured prediction with confidence | "NVIDIA: AI infra beneficiary, target $1200" |
| **Decision Record** | 📊 | Trade entry/exit with rationale | "Buy NVDA @ $955, 10% position" |
| **Reflection** | 🧠 | Post-mortem analysis and lessons | "Cycle timing mistake: entered too early" |

---

## Workflow

### The Complete Research Loop

```
                  ┌──────────────────┐
                  │   DISCOVER       │
                  │   Research Note  │  ← Market observation, industry research
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │   FORM           │
                  │   Thesis         │  ← Structured prediction + confidence
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │   ACT            │
                  │   Decision       │  ← Trade entry with rationale + mood
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │   TRACK          │
                  │   Outcome        │  ← Mark correct/wrong, record return
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │   LEARN          │
                  │   Reflection     │  ← Pattern recognition, rule evolution
                  └──────────────────┘
```

### Real Example: NVIDIA AI Infrastructure

```
📝 Note (Day -90):    "AI GPU Market Analysis — NVIDIA has 85% share"
        ↓
💡 Thesis (Day -85):  "NVIDIA: AI Infra Core Beneficiary"
                      Conviction: 0.80 | Target: $1200
        ↓
📊 Decision (Day -80): "Buy NVDA @ $955"
                       Position: 10% | Mood: Confident
        ↓
        ... 3 months pass ...
        ↓
🧠 Reflection (Day -20): "NVIDIA Retrospective"
                         Outcome: CORRECT ✓  | Return: +41%
                         Pattern: Supply chain verification + earnings confirmation
                         → encode as investment principle
```

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Web Interface                        │
│  /journal  ·  Bloomberg Terminal Dark Theme           │
│  HTMX + Alpine.js  ·  Zero Page Reload               │
├──────────────────────────────────────────────────────┤
│                  API Layer                            │
│  REST + HTMX Partials  ·  JWT Auth                   │
├──────────────────────────────────────────────────────┤
│              Intelligence Layer                       │
│  MemorySearch  ·  MemoryAnalytics                     │
│  Multi-filter ·  FTS5 Full-Text ·  Calibration       │
├──────────────────────────────────────────────────────┤
│              Persistence Layer                        │
│  SQLite + WAL  ·  FTS5 Triggers  ·  CJK Tokenization │
├──────────────────────────────────────────────────────┤
│              Domain Model                             │
│  MemoryEntry (frozen dataclass)                       │
│  4 types: note | thesis | decision | reflection       │
└──────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Web | Flask + Jinja2 |
| Interactivity | HTMX + Alpine.js |
| Database | SQLite 3 (WAL mode) |
| Search | FTS5 with unicode61 tokenizer |
| Charts | Plotly (future) |
| Design | terminal.css dark theme |

### Zero New Dependencies

V3 adds no new pip packages. Everything built on existing Flask + SQLite stack.

---

## Demo Data: Three Investment Cases

### Case 1: NVIDIA AI Infrastructure ✓

| Stage | Entry |
|------|-------|
| Note | AI GPU market analysis — NVIDIA 85% share, CUDA moat, supply chain verified |
| Thesis | Core AI infra beneficiary. Target $1200. Conviction: 0.80 |
| Decision | Buy @ $955, 50 shares, 10% position. Mood: confident |
| Outcome | **CORRECT** · Return +41% · Thesis validated |
| Reflection | Supply chain verification + earnings confirmation = success pattern |

### Case 2: ZTE AI Server ✓

| Stage | Entry |
|------|-------|
| Note | China AI server market — domestic substitution accelerating |
| Thesis | AI server as second growth curve. Target CNY 36. Conviction: 0.70 |
| Decision | Buy @ CNY 28.30, 5000 shares, 8% position |
| Outcome | **CORRECT** · Return +28% · Carrier procurement surged |
| Reflection | Policy direction + industry research = A-share success pattern |

### Case 3: Micron Semiconductor Cycle ✗

| Stage | Entry |
|------|-------|
| Note | Semiconductor cycle research — has memory bottomed? |
| Thesis | Memory cycle bottom opportunity. Target $110. Conviction: 0.65 |
| Decision | Buy @ $86, 200 shares, 6% position |
| Outcome | **WRONG** · Return -12% · Called bottom too early |
| Reflection | **Key lesson**: Don't do left-side entry on cycles. Wait for confirmation. |

---

## Key Analytics

### Confidence Calibration

The system automatically analyzes your self-assessed confidence against actual outcomes:

```
Confidence Level    |  Theses  |  Hit Rate
────────────────────┼──────────┼───────────
High (> 0.7)        |    2     |   100%     ← Well calibrated
Medium (0.5-0.7)    |    1     |    0%      ← Overconfident
Low (< 0.5)         |    0     |    N/A
```

**Insight**: High-confidence theses outperform — you know when you know. Medium-confidence thesis failed — consider raising the bar for what counts as conviction.

### Tag Performance

```
Tag              |  Hit Rate
─────────────────┼───────────
AI               |   100%     ← Your edge
美股             |    67%
semiconductor    |    50%
A股              |   100%
cycle            |     0%     ← Weak area
```

**Insight**: AI and A-share investments are your strong suit. Cyclical timing needs improvement.

---

## Screenshots

> Screenshots will be captured from the running application and placed in `docs/assets/v3_memory/`.

Planned views:
1. **Dashboard** — `/workspace` with stat cards + analytics sidebar
2. **Timeline** — `/journal` showing research timeline with type-coded entries
3. **Search** — FTS5 search with Chinese/English query + filters
4. **Review** — Thesis review modal with outcome marking
5. **Detail** — Entry detail view with related memories

---

## How to Run

```bash
# 1. Seed demo data
python scripts/seed_v3_memory.py --reset

# 2. Start web server
python web_modern.py

# 3. Open browser
# http://127.0.0.1:5000/journal

# 4. Explore
# - Search "NVIDIA" or "白酒" in the search bar
# - Click timeline items to see details
# - Check analytics sidebar for calibration data
# - Create new entries via the + buttons
```

---

## V2 → V3 Evolution

| V2.0 | V3.0 (Phase 1) |
|------|----------------|
| Stateless pipeline | Persistent memory |
| One-shot reports | Lifecycle tracking |
| No outcome tracking | Hit rate + calibration |
| 9 disconnected pages | Unified journal page |
| Technical factors only | Research process metadata |

**V2 code unchanged.** All V3 features are additive — `src/v3/` is a clean layer on top.

---

> **Next Phase**: Company Intelligence Engine — fundamental data + industry comparison.
