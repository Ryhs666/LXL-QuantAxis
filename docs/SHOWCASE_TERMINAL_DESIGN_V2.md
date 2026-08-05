# LXL·QuantAxis Terminal — Design Specification V2

> Bloomberg Terminal × BlackRock Aladdin × AI Research Lab

---

## 0. Product Identity

**LXL·QuantAxis** is an **AI-native investment research operating system**. It does not predict stocks. It structures, validates, and documents the investment research process.

### Positioning Statement

> *"Bloomberg tells you what happened. Aladdin tells you what you own. QuantAxis tells you whether your investment thesis holds up — before you commit capital."*

### Brand Voice

- **Confident, not arrogant**: "Validated." Not "Revolutionary."
- **Precise, not vague**: "Sharpe 1.25 (252d, 0% risk-free)." Not "Good returns."
- **Institutional, not consumer**: "Research Thesis #42." Not "Your cool stock idea 💡"

---

## 1. Research Snapshot Module

### Purpose

The homepage must show a **live research snapshot** — a dense, data-rich summary of the most recent pipeline run. This is the first thing a researcher sees. It must convey competence.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  RESEARCH SNAPSHOT                          Updated: 14:32 UTC   │
├────────────────────────────┬─────────────────────────────────────┤
│                            │                                     │
│  FEATURED CASE             │  INVESTMENT SCORE                   │
│                            │                                     │
│  AI Infrastructure         │  ┌─────────────────────────────┐   │
│  Supply Chain              │  │ ████████████████░░░░ 78/100 │   │
│                            │  │ Technical Score              │   │
│  Thesis: Cloud CAPEX       │  │ ░░░░░░░░░░░░░░░░░░░░░░░░░░  │   │
│  growth drives structural  │  │                              │   │
│  demand for AI servers     │  │ Factor Quality:    ████ 82   │   │
│                            │  │ Strategy Fit:      ████ 85   │   │
│  Conviction: HIGH          │  │ Risk Profile:      ███░ 65   │   │
│  Horizon: 6-12 months      │  │ Backtest Robust:   ███░ 72   │   │
│                            │  └─────────────────────────────┘   │
│  [▸ Open Full Case]        │                                     │
│                            │                                     │
├────────────────────────────┼─────────────────────────────────────┤
│                            │                                     │
│  FACTOR EXPOSURE           │  BACKTEST METRICS                   │
│                            │                                     │
│  Momentum   ████████ 40%   │  Sharpe Ratio        1.25          │
│  Trend      ██████   30%   │  Annual Return      +18.5%         │
│  Volume     ████     20%   │  Max Drawdown        -9.8%         │
│  Volatility ██       10%   │  Win Rate            58.3%         │
│                            │  Trades                 24         │
│                            │                                     │
├────────────────────────────┴─────────────────────────────────────┤
│  RISK PROFILE                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Market Risk    ████ Moderate  │ Factor Risk   ██ Low       │ │
│  │ Concentration  ██   Low       │ Model Risk    ███ Moderate  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Data Sources

| Element | Source | Refresh |
|---------|--------|---------|
| Featured Case | `examples/research_cases/case_ai_infrastructure.md` | Static |
| Investment Score | `/api/research/pipeline/all` | Per run |
| Factor Exposure | Portfolio intelligence module | Per run |
| Backtest Metrics | Backtest engine output | Per run |
| Risk Profile | Risk gate + portfolio analytics | Per run |

---

## 2. Terminal Experience (`/terminal`)

### Purpose

A Bloomberg-style **live research terminal** where the user types an investment idea and watches the AI pipeline execute in real time. This is the hero interaction of the product.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Research │ Workspace │ Pipeline │ TERMINAL │ Portfolio │ Cases │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ $ _                                                        │  │
│  │ Type your investment thesis...                              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─── [EXAMPLES] ───────────────────────────────────────────┐   │
│  │ 1. AI servers benefiting from cloud CAPEX growth           │   │
│  │ 2. Consumer sector undervalued at 18x PE, recovery ahead   │   │
│  │ 3. Semiconductor cycle bottom with AI-driven demand        │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ── PIPELINE EXECUTION ───────────────────────────────────────   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ STAGE                  STATUS    ELAPSED    OUTPUT        │    │
│  │ ───────────────────────────────────────────────────────── │    │
│  │ 01 Thesis Extraction   DONE      0.3s       Investment-   │    │
│  │                                             Thesis obj    │    │
│  │ 02 Fundamental Check   DONE      0.5s       PE: 32.5      │    │
│  │ 03 Factor Mapping      RUNNING   1.2s       ...           │    │
│  │ 04 Strategy Gen.       PENDING    —          —             │    │
│  │ 05 Backtest            PENDING    —          —             │    │
│  │ 06 AI Analysis         PENDING    —          —             │    │
│  │ 07 Report Gen.         PENDING    —          —             │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ── LIVE OUTPUT ──────────────────────────────────────────────   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ 02 FUNDAMENTAL CHECK                          [EXPAND]    │    │
│  │ ───────────────────────────────────────────────────────── │    │
│  │ Symbol: 600519  │ PE(TTM): 32.5  │ PB: 8.2               │    │
│  │ ROE: 25.3%      │ Rev YoY: 15.2% │ Industry: 白酒       │    │
│  │ Market Cap: ¥2.1T │ Sector Rank: 1/18                    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Interaction Flow

```
User types thesis → Press Enter
    │
    ▼
Stage 1: "Thesis Extraction" → progress bar → "DONE ✓"
    │
    ▼
Stage 2: "Fundamental Check" → fetches PE/PB/ROE → displays snapshot
    │
    ▼
Stages 3-7: Each auto-advances, output accumulates in right panel
    │
    ▼
Final: "Report Generated → reports/AI_infra_20260805.md"
```

### Key Design Decisions

- **Monospace command line**: `$ _` cursor, green text on dark bg
- **Stage table**: DENSE. 7 rows, each with status indicator, elapsed ms, output summary
- **Live output panel**: Expandable. Each stage produces structured output preview.
- **Terminal aesthetic**: No rounded corners, no shadows, no gradients. Flat panels with 1px borders.

---

## 3. Enhanced Pipeline Visualization

### Each Stage Now Shows: Input → Processing → Output

```
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 03: FACTOR MAPPING                      [◂ 02] [04 ▸]    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT                                                           │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ InvestmentThesis {                                        │    │
│  │   symbol: "AI_server",                                    │    │
│  │   core_argument: "Cloud CAPEX drives structural demand",  │    │
│  │   style: "growth",                                        │    │
│  │   conviction: "high"                                      │    │
│  │ }                                                         │    │
│  └──────────────────────────────────────────────────────────┘    │
│                          │                                       │
│                          ▼                                       │
│  PROCESSING                                                      │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ Rule-based style template: "growth" → momentum + trend    │    │
│  │ Query FACTOR_REGISTRY: 28 factors available               │    │
│  │ Apply weights: momentum(0.30), trend(0.25), roc(0.25)...  │    │
│  │ Validate: all factor names in registry ✓                  │    │
│  │ Mode: rule-based (LLM available but off for demo)         │    │
│  └──────────────────────────────────────────────────────────┘    │
│                          │                                       │
│                          ▼                                       │
│  OUTPUT                                                          │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ FactorModel {                                             │    │
│  │   theme: "AI Infrastructure",                             │    │
│  │   factors: [                                              │    │
│  │     {name: "momentum_score", weight: 0.30, category: ...},│    │
│  │     {name: "trend_strength", weight: 0.25, category: ...},│    │
│  │     {name: "roc_10",         weight: 0.25, category: ...},│    │
│  │     {name: "volume_trend",   weight: 0.20, category: ...} │    │
│  │   ],                                                      │    │
│  │   confidence: 0.35,                                       │    │
│  │   source: "rule"                                          │    │
│  │ }                                                         │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Institutional Design Specification

### 4.1 Information Density

**Rule**: Every panel must justify its pixel footprint.

| Panel Size | Minimum Data Points | Example |
|------------|-------------------|---------|
| Full width (1200px) | 8-12 metrics or 1 table (6+ rows) | Research Snapshot |
| Half width (580px) | 4-6 metrics or 1 chart | Factor Exposure |
| Third width (380px) | 2-4 metrics or 1 KPI | Investment Score |
| Quarter width (280px) | 1-2 KPIs | Status indicator |

**Anti-pattern**: A full-width panel with one number and a lot of whitespace.

### 4.2 Data Hierarchy

```
Level 1: Page Title (24px, --text-primary, 600 weight)
  └── Level 2: Section Header (14px, --text-muted, uppercase, tracking 0.5px)
       └── Level 3: Metric Label (11px, --text-secondary, 400 weight)
            └── Level 4: Metric Value (16px, --text-primary or --accent-finance, 500 weight, monospace)
                 └── Level 5: Change/Diff (12px, --accent-success/--accent-danger, 400 weight)
```

### 4.3 Card Proportions

```
Standard Metric Card:     280px × 120px   (2.33:1)
Wide Metric Card:         580px × 120px   (4.83:1)
Table Card:               1200px × auto   (content-driven)
Chart Card:               580px × 340px   (1.71:1)
Full Panel:               1200px × auto   (content-driven)
```

### 4.4 Chart Specification

| Chart Type | Colors | Grid | Tooltip | Animation |
|------------|--------|------|---------|-----------|
| Bar (horizontal) | `--accent-tech` gradient | None | Value + label | None |
| Bar (vertical) | `--accent-finance` | Subtle horizontal | Value + date | None |
| Line (single) | `--accent-tech` | Horizontal grid only | Value + date | Draw on load (600ms) |
| Line (multi) | White → blue gradient | None | All series values | Draw on load (600ms) |
| Heatmap | `--bg-panel` → `--accent-tech` | None | Cell value | None |
| Sparkline | `--accent-finance` | None | None | None |

**Anti-patterns**: 3D charts, pie charts (use horizontal bar), animated pie charts, rainbow color schemes.

### 4.5 Motion Specification

| Element | Duration | Easing | Trigger |
|---------|----------|--------|---------|
| Page transition | 0ms | None | Immediate (no SPA) |
| Panel appear | 200ms | ease-out | On render |
| Data value update | 400ms | ease-out | On data change |
| Progress bar fill | 600ms | ease-in-out | Stage complete |
| Hover state | 150ms | ease | :hover |
| Loading skeleton | Pulse 1.5s | ease-in-out | While loading |
| Pipeline node connect | 800ms | ease-in-out | Stage complete |

**Rule**: No animation over 1 second. No bounce. No spring physics. Institutional, not playful.

### 4.6 Typography Specification

```
Page Title:     Inter 600 24px / 32px line-height
Section Label:  Inter 600 11px / 16px, uppercase, letter-spacing: 0.05em
Body Text:      Inter 400 14px / 22px
Metric Value:   JetBrains Mono 500 16px / 24px
Metric Label:   Inter 400 11px / 16px
Table Header:   Inter 600 11px / 16px, uppercase
Table Cell:     JetBrains Mono 400 13px / 20px
Code Block:     JetBrains Mono 400 12px / 18px
Status Badge:   Inter 600 10px / 14px, uppercase
```

### 4.7 Color Usage Rules

```
--accent-finance (#C9A227): ONLY for numeric financial data
  - Returns, PnL, position values, prices
  - NEVER for UI elements, buttons, or text labels

--accent-tech (#3B82F6): ONLY for interactive elements
  - Links, buttons, hover states, focus rings
  - NEVER for static data display

--accent-success (#22C55E): ONLY for positive outcomes
  - Positive returns, passed validations, completed stages
  - NEVER for decorative use

--accent-danger (#EF4444): ONLY for negative outcomes
  - Negative returns, drawdowns, failed validations

--accent-warning (#F59E0B): ONLY for attention states
  - Pending stages, risk warnings, unverified data
```

---

## 5. Responsive Breakpoints

| Breakpoint | Layout | Behavior |
|------------|--------|----------|
| ≥ 1440px | Full terminal | 3-column research workspace, all panels visible |
| 1024-1439px | Compact | 2-column, pipeline collapses to horizontal scroll |
| 768-1023px | Tablet | Single column, cards stack vertically |
| < 768px | Mobile | Simplified, data tables become cards |

**Note**: Showcase targets ≥ 1440px. Mobile is a future concern.

---

## 6. Implementation Priority

| Priority | Page | Impact | Effort |
|----------|------|--------|--------|
| P0 | `landing.html` with Research Snapshot | First impression | 4h |
| P0 | `terminal.css` (shared design system) | All pages consistent | 3h |
| P1 | `research.html` (3-column workspace) | Core interaction | 5h |
| P1 | `pipeline.html` (I→P→O detail) | Technical depth | 4h |
| P2 | `terminal.html` (live pipeline runner) | Hero demo | 6h |
| P2 | `portfolio.html` (dashboard) | Institutional feel | 4h |
| P3 | `cases.html` (case library) | Content showcase | 3h |

**Total**: ~29 hours for complete showcase.

---

## 7. Development Sequence (7 Commits)

```
1. feat(web): add institutional design system (terminal.css)
   → 1 file, ~400 lines CSS. No HTML changes. Foundation.

2. feat(web): add landing page with research snapshot
   → templates/landing.html + web_modern.py route change

3. feat(web): add 3-column research workspace
   → templates/research.html + /api/research/pipeline/all

4. feat(web): add pipeline visualization with I-P-O detail
   → templates/pipeline.html

5. feat(web): add live terminal experience
   → templates/terminal.html + web_modern.py routes

6. feat(web): add portfolio dashboard
   → templates/portfolio.html

7. feat(web): add case library and shared navigation
   → templates/cases.html + static/js/terminal.js
```
