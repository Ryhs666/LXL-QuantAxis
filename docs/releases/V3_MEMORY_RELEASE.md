# LXL·QuantAxis V3.0 — Memory Showcase Edition

> **Release**: v3.0-memory-showcase  
> **Date**: 2026-08-06  
> **Type**: Portfolio Showcase Release  
> **Phase**: 1 of 4 — Investment Memory System

---

## Executive Summary

LXL·QuantAxis V3 transforms the platform from an AI research showcase into a **personal investment research operating system**. The Phase 1 release — Investment Memory System — introduces a cognitive database that records every investment thesis, decision, and lesson, then automatically analyzes judgment quality through confidence calibration and outcome tracking.

**Core insight**: LXL·QuantAxis is not a prediction engine. It does not tell you what to buy. It is a **learning system** that helps you understand your own investment mind — what you're good at, where you're overconfident, and how to improve.

**V2 code**: Zero lines modified. All 155 V2 files untouched. V3 is a pure additive layer.

---

## Architecture

```
LXL·QuantAxis V3.0
├── src/v3/memory/           Investment Memory System (Phase 1)
│   ├── models.py            MemoryEntry — frozen dataclass, 4 types
│   ├── database.py          SQLite + WAL mode connection management
│   ├── schema.sql           DDL + FTS5 virtual table + 3 sync triggers
│   ├── repository.py        CRUD with parameterized queries
│   ├── search.py            Multi-filter query engine + related memory
│   └── analytics.py         Stats engine + confidence calibration
│
├── src/v3/web/              Web Interface
│   ├── __init__.py           Flask Blueprint (registered in web_modern.py)
│   ├── journal_page.py      /journal page route
│   └── journal_api.py       11 REST endpoints, HTMX + JSON dual mode
│
├── templates/v3/            Jinja2 Templates
│   ├── journal.html         Bloomberg dark theme, HTMX + Alpine.js
│   └── partials/            HTMX fragments (timeline, stats, sidebar)
│
├── scripts/
│   ├── seed_v3_memory.py     Demo data: 4 cases, 16 entries
│   └── demo_v3_memory.py    Interactive showcase demo
│
└── lxl_v3.db                SQLite database (auto-created)
```

### Layer Diagram

```
┌────────────────────────────────────────────┐
│  Browser — /journal                         │
│  HTMX (no reload) · Alpine.js · Dark Theme  │
├────────────────────────────────────────────┤
│  Flask Blueprint — src/v3/web/              │
│  11 REST + HTMX partial endpoints           │
├────────────────────────────────────────────┤
│  Intelligence — src/v3/memory/              │
│  Search · Analytics · Calibration           │
├────────────────────────────────────────────┤
│  Persistence — SQLite + WAL + FTS5          │
│  CJK regex tokenizer for Chinese search     │
├────────────────────────────────────────────┤
│  V2 Core — src/lxl_quantaxis/ (unchanged)   │
│  155 files · 400+ tests · 0 modifications   │
└────────────────────────────────────────────┘
```

---

## Key Features

### 1. Four-Type Memory Model

A single unified table with a `type` discriminator:

| Type | Purpose | Structured Fields |
|------|---------|-------------------|
| `note` | Market research, industry analysis | ticker, tags |
| `thesis` | Structured prediction | thesis {catalysts, risks, timeline, target_price}, confidence, outcome |
| `decision` | Trade entry/exit record | decision {type, price, quantity, reason, mood}, outcome |
| `reflection` | Post-mortem, lessons learned | tags (for lesson categorization) |

### 2. FTS5 Full-Text Search

- Chinese + English search with zero-dependency CJK tokenization
- Combined filters: type, ticker, date range, confidence range, status
- <5ms query latency on 16-entry dataset; scales linearly to ~100K entries
- HTMX live search with 300ms debounce — results appear as you type

### 3. Confidence Calibration Engine

Automatically analyzes self-assessed conviction against actual outcomes:

```
Confidence Level     │ Theses │ Hit Rate │ Interpretation
─────────────────────┼────────┼──────────┼────────────────
High (> 0.70)        │   2    │   100%   │ Well calibrated
Medium (0.50–0.70)   │   1    │     0%   │ Overconfident
Low (< 0.50)         │   0    │    N/A   │ No data
```

Surfaces actionable rules: *"Only trade conviction > 0.70"*

### 4. Tag-Based Performance Analysis

Hit rate automatically computed per investment theme:

| Tag | Hit Rate | Verdict |
|-----|----------|---------|
| AI | 100% | Core edge |
| A股 | 100% | Strong |
| growth | 100% | Growth edge |
| semiconductor | 50% | Mixed |
| cycle | 0% | Weakness |
| value | 0% | Weakness |

Enables precise identification of the investor's circle of competence.

### 5. Related Memory Discovery

- `find_related(ticker="000858")` — all memories for a stock
- `find_similar(entry_id)` — scored tag + ticker overlap matching
- Automatic seed entry ticker extraction

### 6. Bloomberg Terminal-Style UI

- Dark theme (`terminal.css`): #05070A root, monospace data fonts
- HTMX: zero full-page reloads — search, filter, create all via AJAX
- Alpine.js: modal state, dynamic form fields based on entry type
- 5-card stat bar, color-coded timeline, analytics sidebar

---

## Demo Cases

Seeded via `python scripts/seed_v3_memory.py --reset`:

### Case 1: NVIDIA AI Infrastructure ✅

```
📝 Note    → AI GPU market: NVIDIA 85% share, CUDA moat
💡 Thesis  → AI infra beneficiary. Conviction 0.80. Target $1200
📊 Decision → Buy @ $955, 50 shares, 10% position
🧠 Reflect → CORRECT. +41%. Pattern: supply chain verification
```

### Case 2: ZTE AI Server ✅

```
📝 Note    → China AI server: domestic substitution accelerating
💡 Thesis  → Second growth curve. Conviction 0.70. Target ¥36
📊 Decision → Buy @ ¥28.30, 5000 shares, 8% position
🧠 Reflect → CORRECT. +28%. Pattern: policy + industry research
```

### Case 3: Micron Semiconductor Cycle ❌

```
📝 Note    → Memory cycle: 18-month down-cycle, prices stabilizing
💡 Thesis  → Cycle bottom. Conviction 0.65. Target $110
📊 Decision → Buy @ $86, 200 shares, 6% position
🧠 Reflect → WRONG. -12%. Lesson: don't do left-side entry on cycles
```

### Case 4: SMIC Semiconductor Manufacturing ⏳

```
📝 Note    → (included in H2 themes overview)
💡 Thesis  → Domestic chip core asset. Conviction 0.55. Target ¥65
📊 Decision → Not yet executed (confidence below 0.70 threshold)
⏳ Status  → PENDING — awaiting outcome review
```

### Key Insight from Failures

> The Micron case — a "failed" thesis — generated the most valuable output: a concrete cycle-timing checklist that prevents repeating the same mistake. **This is the system working as designed.** Learning from losses is the core value proposition.

---

## Investor Profile (Auto-Generated)

When the demo runs, `MemoryAnalytics` produces:

```
═══ Investor Profile ═══

Thesis Accuracy:     67% (2/3 resolved, 1 pending)
Decision Win Rate:   67% (2/3)
Average Conviction:  67.5%

Confidence Calibration:
  High (>0.70):      100% hit rate  ← well calibrated
  Medium (0.50-0.70):   0% hit rate ← overconfident here

Sector Edge:
  AI/A-share/Growth: 100% accuracy — your circle of competence
  Cycles/Value:        0% accuracy — avoid or develop

Investment Principles (derived from reflections):
  1. Only trade conviction > 0.70
  2. Right-side entry, not left-side timing
  3. Supply chain verification > macro judgment
  4. Position size matches conviction (10-15% for high, 0% for low)
  5. Quarterly review of all theses
```

---

## V2 Compatibility

| Guarantee | Status |
|-----------|--------|
| V2 155 files unchanged | ✅ 0 modifications |
| V2 400+ tests pass | ✅ 100% |
| Zero new pip dependencies | ✅ Flask + SQLite only |
| `demo_ai_research.py` identical output | ✅ Verified |
| Existing web pages untouched | ✅ Blueprint registration only (+4 lines) |

---

## Technical Specifications

| Metric | Value |
|--------|-------|
| New Python code | ~1,900 lines (12 files) |
| New HTML/CSS | ~550 lines (5 files) |
| Tests | 25 (search + analytics) |
| Database | 1 new SQLite file (`lxl_v3.db`), 2 tables + FTS5 |
| API endpoints | 11 REST routes |
| Browser JS | HTMX (14KB) + Alpine.js (15KB) via CDN |
| Search latency | <5ms (16 entries), <100ms projected at 100K |
| Dependencies added | **0** |

---

## Future Roadmap

| Phase | Module | Description |
|-------|--------|-------------|
| ✅ Phase 1 | Investment Memory System | This release |
| 🔜 Phase 2 | Company Intelligence Engine | Financial data + industry comparison |
| 🔜 Phase 3 | Research Workspace | Project-based organization + reports |
| 🔜 Phase 4 | Quant Validation Engine | Thesis validation scoring |
| 📋 V4 | Research Agent Framework | Autonomous research agents |

---

## Quick Start

```bash
# Install (if not already done)
pip install -r requirements.txt

# Run the interactive demo
python scripts/demo_v3_memory.py

# Or seed data and launch the web UI
python scripts/seed_v3_memory.py --reset
python web_modern.py
# → http://127.0.0.1:5000/journal
```

---

> **LXL·QuantAxis V3.0 — Memory Showcase Edition**  
> Not a prediction tool. Not a trading bot.  
> A personal investment research operating system that gets smarter with every decision.
