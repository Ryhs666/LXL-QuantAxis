# LXL·QuantAxis Terminal — Showcase Design Specification

**Design Authority**: Bloomberg Terminal × BlackRock Aladdin × Palantir Foundry  
**Target**: Institutional-grade AI-native investment research interface  
**Version**: Showcase Edition v2.0

---

## 0. Design Philosophy

> *"LXL·QuantAxis should feel like an early Bloomberg terminal crossed with an AI research lab — not a student project."*

### Anti-patterns (Forbidden)
- Purple AI gradients ("enterprise ChatGPT")
- Rainbow card grids ("SaaS template")
- Emoji as UI elements ("student dashboard")
- Excessive animations ("consumer app")
- "Revolutionary", "best-in-class" copy ("marketing hype")

### Patterns (Embraced)
- Dark institutional palette with amber/gold accents
- Dense data layouts with breathing room
- Subtle transitions (200ms ease, fade only)
- Monospace for data, sans-serif for labels
- Terminal-inspired status indicators
- Bloomberg-style function bar

---

## 1. Visual System

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-root` | `#05070A` | Page background (deepest) |
| `--bg-panel` | `#0B1220` | Cards, panels, sidebar |
| `--bg-elevated` | `#111D30` | Hover states, active panels |
| `--border-subtle` | `#1A2A44` | Panel borders, dividers |
| `--border-active` | `#2A4A74` | Active/focus borders |
| `--text-primary` | `#F8FAFC` | Headings, key data |
| `--text-secondary` | `#94A3B8` | Labels, descriptions |
| `--text-muted` | `#475569` | Disabled, placeholders |
| `--accent-tech` | `#3B82F6` | Interactive elements, links |
| `--accent-finance` | `#C9A227` | Numeric data, PnL, key metrics |
| `--accent-success` | `#22C55E` | Positive returns, passes |
| `--accent-danger` | `#EF4444` | Negative returns, drawdowns, warnings |
| `--accent-warning` | `#F59E0B` | Alerts, pending states |

### Typography

| Role | Font | Size | Weight |
|------|------|------|--------|
| Page Title | Inter | 24px | 600 |
| Section Header | Inter | 14px | 600, `--text-muted`, uppercase tracking |
| Body | Inter | 14px | 400 |
| Data Value | JetBrains Mono | 16px | 500 |
| Data Label | Inter | 11px | 400, `--text-secondary` |
| Code/ID | JetBrains Mono | 12px | 400 |

### Spacing
- Section padding: 24px
- Card padding: 16px
- Element gap: 12px
- Inline gap: 8px

---

## 2. Navigation System

### Top Bar (48px)

```
┌──────────────────────────────────────────────────────────────────┐
│ LXL·QuantAxis  │ Research  Workspace  Pipeline  Portfolio  Cases│
│                │                                    [status bar]│
└──────────────────────────────────────────────────────────────────┘
```

- Fixed position, full width
- Left: product name in `--accent-finance` (#C9A227)
- Center: tab-style navigation, active tab underlined in `--accent-tech`
- Right: system status (v2.0.0, server time, connection indicator)
- Background: `--bg-panel` with `--border-subtle` bottom border

### Navigation Items

| Tab | Icon | Description |
|-----|------|-------------|
| Research | 📊 | Research workspace (default) |
| Workspace | 💼 | Project-based research organization |
| Pipeline | ⚙️ | AI pipeline visualization and control |
| Portfolio | 📈 | Portfolio intelligence dashboard |
| Reports | 📄 | Generated research reports |
| Cases | 📋 | Research case library |

---

## 3. Page Designs

### 3.1 Landing Page (`/`)

**Purpose**: 5-second understanding. 30-second conviction.

```
┌──────────────────────────────────────────────────────────────────┐
│  LXL·QuantAxis  [Research] [Pipeline] [Cases]                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    LXL·QuantAxis                                 │
│          AI-Native Investment Research Infrastructure            │
│                                                                  │
│     Transform investment ideas into validated strategies         │
│     and institutional-grade research reports.                    │
│                                                                  │
│        [▸ Launch Research Terminal]  [Explore Pipeline]          │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RESEARCH INTELLIGENCE PIPELINE                                  │
│                                                                  │
│  ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐          │
│  │ Idea │ → │Thesis│ → │Factor│ → │Strat │ → │Report│          │
│  │      │   │Engine│   │Model │   │Builder│   │Gen.  │          │
│  └──────┘   └──────┘   └──────┘   └──────┘   └──────┘          │
│                                                                  │
│  Each node: hover → "Input: Natural language thesis"            │
│                       "Output: Structured investment thesis"     │
│                       "Tech: AI parser + rule-based fallback"    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PROVEN IN RESEARCH                                              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ 28 Factors  │  │ 16 Strategies│  │ 7-Stage AI  │              │
│  │ 5 categories│  │ V2 compiler  │  │ Pipeline    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌──────────────────────────────────────────────┐               │
│  │ Case: NVIDIA AI Infrastructure               │               │
│  │ Thesis → Growth Factor Model → Strategy DSL  │               │
│  │ → Backtest → Institutional Report            │               │
│  │                            [▸ View Case]     │               │
│  └──────────────────────────────────────────────┘               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Implementation**: `templates/landing.html` + `web_modern.py` route redirect

### 3.2 Research Workspace (`/research`)

**Purpose**: Bloomberg Terminal-style investment research environment.

```
┌──────────────────────────────────────────────────────────────────┐
│ Research  │  Workspace │ Pipeline │ Portfolio │ Reports         │
├────────────┬───────────────────────────┬────────────────────────┤
│            │                           │                        │
│  INPUT     │  PROCESS                  │  OUTPUT                │
│            │                           │                        │
│  ┌───────┐ │  ┌───────────────────┐    │  Investment Thesis     │
│  │Symbol │ │  │ 01 Thesis Extract │ ✓  │  ┌──────────────────┐ │
│  │600519 │ │  │ 02 Factor Map     │ ✓  │  │ Core: Cloud CAPEX │ │
│  └───────┘ │  │ 03 Strategy Build │ ✓  │  │ Bull: demand vis. │ │
│            │  │ 04 Backtest       │ …  │  │ Bear: oversupply  │ │
│  ┌───────┐ │  │ 05 AI Analysis    │    │  └──────────────────┘ │
│  │Thesis │ │  │ 06 Report Gen.    │    │                        │
│  │cloud...│ │  └───────────────────┘    │  Factor Model          │
│  └───────┘ │                           │  ┌──────────────────┐ │
│            │                           │  │ momentum: 0.30   │ │
│  ┌───────┐ │                           │  │ trend:    0.25   │ │
│  │Horizon│ │                           │  │ roc:      0.25   │ │
│  │Medium │ │                           │  │ volume:   0.20   │ │
│  └───────┘ │                           │  └──────────────────┘ │
│            │                           │                        │
│  [▸ Run Pipeline]                      │  Strategy              │
│            │                           │  Entry: momentum>0.6  │
│            │                           │  Exit:  drawdown>0.10 │
│            │                           │                        │
│            │                           │  [View Full Report →]  │
├────────────┴───────────────────────────┴────────────────────────┤
│  STATUS: 7/7 stages complete · Research notebook: 42 entries    │
└──────────────────────────────────────────────────────────────────┘
```

**Three-column layout**: Input | Process | Output
**Left**: Symbol entry, thesis text, horizon/conviction selectors
**Center**: 7-stage pipeline progress with checkmarks
**Right**: Accumulated output as pipeline runs

**Implementation**: `templates/research.html` + `/api/research/pipeline/all` route

### 3.3 Pipeline Visualization (`/pipeline`)

**Purpose**: Show the technology behind the platform.

```
┌──────────────────────────────────────────────────────────────────┐
│  Research │ Workspace │ PIPELINE │ Portfolio │ Reports          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AI Research Pipeline                                            │
│                                                                  │
│  ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐    │
│  │ 01  │──→│ 02  │──→│ 03  │──→│ 04  │──→│ 05  │──→│ 06  │    │
│  │Thesis│   │Fund.│   │Fact.│   │Strat│   │Back-│   │Report│    │
│  └──┬───┘   └──┬───┘   └──┬───┘   └──┬───┘   └──┬───┘   └──┬───┘    │
│     │          │          │          │          │          │       │
│  ┌──┴──────────┴──────────┴──────────┴──────────┴──────────┴──┐  │
│  │                   STAGE DETAIL                              │  │
│  │                                                             │  │
│  │  03 FACTOR MAPPING                                          │  │
│  │  ─────────────────                                          │  │
│  │  Purpose: Map investment thesis to 28-factor registry       │  │
│  │  Input:   Structured InvestmentThesis object                │  │
│  │  Output:  FactorModel {factors, weights, rationale}          │  │
│  │  Tech:    Rule-based style templates + LLM (opt-in)          │  │
│  │  Safety:  All factor names validated against registry        │  │
│  │                                                             │  │
│  │  Example:                                                   │  │
│  │  thesis "Cloud CAPEX growth" → growth style template        │  │
│  │  → momentum_score(0.30), trend_strength(0.25)...            │  │
│  │                                                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [◂ Previous Stage]                    [Next Stage ▸]           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Interactive**: Click any stage node to see detail panel below.
**Data**: Static content from module docstrings + example pipeline run.

**Implementation**: `templates/pipeline.html`

### 3.4 Portfolio Dashboard (`/portfolio`)

**Purpose**: Institutional portfolio intelligence view.

```
┌──────────────────────────────────────────────────────────────────┐
│  Research │ Workspace │ Pipeline │ PORTFOLIO │ Reports          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PORTFOLIO OVERVIEW                          Last: 2026-08-05    │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Ann.Ret  │ │ Sharpe   │ │ Max Draw │ │ Div.Score│           │
│  │          │ │          │ │          │ │          │           │
│  │ +12.4%   │ │   1.25   │ │  -9.8%   │ │   0.72   │           │
│  │  ↑ 2.1%  │ │  ▸ 1.25  │ │  ▾ -9.8% │ │  ◆ 0.72  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  ALLOCATION                         FACTOR EXPOSURE              │
│  ┌────────────────────┐             ┌────────────────────┐       │
│  │ Growth      ████ 40%│             │ Momentum    █████ 45%│    │
│  │ Value       ███  30%│             │ Trend       ████ 35%│    │
│  │ Momentum    ██   20%│             │ Volatility  ██   20%│    │
│  │ Macro       █    10%│             │ Volume      █    10%│    │
│  └────────────────────┘             └────────────────────┘       │
│                                                                  │
│  STRATEGIES                                                        │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ AI Growth     │  40%  │ Sharpe 1.25 │ Ann.Ret +15.3%     │    │
│  │ Consumer Val  │  30%  │ Sharpe 0.82 │ Ann.Ret +8.1%      │    │
│  │ Semi Cycle    │  20%  │ Sharpe 0.95 │ Ann.Ret +10.2%     │    │
│  │ Macro Hedge   │  10%  │ Sharpe 0.65 │ Ann.Ret +5.4%      │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Data source**: Existing `/api/v2/` routes + portfolio intelligence module.

**Implementation**: `templates/portfolio.html`

### 3.5 Research Cases (`/cases`)

**Purpose**: Curated research examples showing the full pipeline.

```
┌──────────────────────────────────────────────────────────────────┐
│  Research │ Workspace │ Pipeline │ Portfolio │ CASES             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RESEARCH CASE LIBRARY                                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ CASE 01 — AI Infrastructure Supply Chain                  │    │
│  │ ───────────────────────────────────────────────────────── │    │
│  │ Question: Is the AI infrastructure cycle sustainable?     │    │
│  │ Thesis:   Growth — Cloud CAPEX driving structural demand  │    │
│  │ Factors:  momentum_score(0.30), trend_strength(0.25)...   │    │
│  │ Strategy: momentum>0.6 AND trend>0.5, drawdown exit 10%  │    │
│  │ Backtest: Sharpe 1.25, Return +18.5%, MaxDD -12%          │    │
│  │                                                            │    │
│  │ [▸ View Full Case Study]                                   │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ CASE 02 — Consumer Value Recovery                         │    │
│  │ ...                                                        │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ CASE 03 — Semiconductor Cycle Bottom                      │    │
│  │ ...                                                        │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Data source**: `examples/research_cases/*.md` files, rendered as HTML.

**Implementation**: `templates/cases.html` + Markdown→HTML converter

---

## 4. Implementation Plan

### File Architecture After Migration

```
web_modern.py              →  ~200 lines (app factory + route registration)
templates/
  landing.html             →  Landing page
  research.html            →  Research workspace (new)
  pipeline.html            →  Pipeline visualization (new)
  portfolio.html           →  Portfolio dashboard (new)
  cases.html               →  Case library (new)
  login.html               →  (existing)
  studio.html              →  (existing)
  game.html                →  (existing)
  admin.html               →  (existing)
  professional.html        →  (existing)
static/
  css/
    terminal.css            →  Shared design system
  js/
    terminal.js             →  Shared interactions
  assets/
    logo.svg               →  Product logo placeholder
```

### Phase Execution

| Phase | Template | Backend Changes | Lines | Test |
|-------|----------|-----------------|-------|------|
| 1 | `landing.html` | `index()` → render_template | ~200 | Manual |
| 2 | `research.html` | + `/api/research/pipeline/all` | ~400 | Manual |
| 3 | `pipeline.html` | Static page, no new API | ~350 | Manual |
| 4 | `portfolio.html` | Reuses existing v2 API | ~300 | Manual |
| 5 | `cases.html` | Renders examples/*.md | ~200 | Manual |
| CSS | `terminal.css` | Shared stylesheet | ~400 | N/A |
| JS  | `terminal.js` | Navigation + transitions | ~100 | N/A |

### What Survives Unchanged
- All 60+ API routes
- All backend logic (factors, strategies, backtest, AI pipeline)
- `src/` and `src/lxl_quantaxis/` — zero modifications
- Existing templates (login, studio, game, admin)
- `/classic` — served from `web_modern.py` as before

---

## 5. Development Sequence

```
Commit 1: feat(web): add institutional landing page
  - templates/landing.html
  - static/css/terminal.css (shared styles)
  - web_modern.py: index() → render_template('landing.html')

Commit 2: feat(web): add research workspace terminal
  - templates/research.html
  - web_modern.py: /research → render_template
  - web_modern.py: + /api/research/pipeline/all route

Commit 3: feat(web): add pipeline visualization
  - templates/pipeline.html
  - web_modern.py: /pipeline route

Commit 4: feat(web): add portfolio dashboard
  - templates/portfolio.html
  - web_modern.py: /portfolio route

Commit 5: feat(web): add research case showcase
  - templates/cases.html
  - web_modern.py: /cases route

Commit 6: feat(web): add shared navigation and interactions
  - static/js/terminal.js
  - Consistent top bar across all templates
```
