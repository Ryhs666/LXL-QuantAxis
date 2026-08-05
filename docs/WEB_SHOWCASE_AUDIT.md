# Web Showcase Audit — LXL·QuantAxis v2.0.0

**Auditor**: Product Architect  
**Date**: 2026-08-05

## A. Current Web State

### Pages (9 routes)

| Route | Handler | Content | Quality |
|-------|---------|---------|---------|
| `/` | `index()` | Redirect → `/login` | ❌ Wrong default |
| `/login` | `login_page()` | Jinja2 template (`login.html`) | OK |
| `/classic` | `classic_dashboard()` | 57KB inline HTML string | Functional, dated UI |
| `/studio` | `studio_page()` | Jinja2 template (`studio.html`) | OK |
| `/research` | `research_center()` | Inline HTML — AI pipeline runner | Basic but works |
| `/game` | `game_page()` | Jinja2 template (`game.html`) | OK |
| `/admin` | `admin_page()` | Jinja2 template (`admin.html`) | OK |
| `/professional` | `professional_page()` | Redirect → `/studio` | ❌ Hidden |
| `/metrics` | `api_metrics()` | Prometheus text | N/A |

### API Routes (60+)
All functional. JSON responses. Good coverage of backtest, strategy, signals, portfolio, research.

### `web_modern.py`
- 3,342 lines, single file
- Flask-SocketIO for real-time
- Inline HTML strings mixed with Python
- No blueprint separation

## B. Defect List

### Critical

| # | Issue | Impact |
|---|-------|--------|
| 1 | `/` redirects to `/login` instead of a showcase landing page | First impression is a login form — terrible for GitHub visitors |
| 2 | No unified navigation between pages | Each page is an island. No way to discover other features |
| 3 | `/research` page has no navigation links back to other pages | User gets stuck |

### High

| # | Issue | Impact |
|---|-------|--------|
| 4 | `/classic` is 57KB of Python string | Unmaintainable. Every change risks breaking the giant string |
| 5 | No landing/hero page | No single page that explains what the product does |
| 6 | `/professional` is hidden behind env var | Intended for showcase but disabled by default |
| 7 | No screenshots or visual branding | Generic browser tab, no favicon customization |

### Medium

| # | Issue | Impact |
|---|-------|--------|
| 8 | Inline HTML has no shared CSS | Each page redefines styles independently |
| 9 | No responsive design testing | Pages break on mobile |
| 10 | No loading states or error boundaries in JS | API failures show raw errors or blank sections |
| 11 | Demo pipeline requires CLI | No one-click demo from the web UI |

### Low

| # | Issue |
|---|-------|
| 12 | Eventlet deprecation warning on startup |
| 13 | `web_modern.py` too large for single file |
| 14 | No OpenAPI spec for the 60+ routes |

## C. Modification Plan

### Phase 1: Landing Page (1 file, ~200 lines)

**New**: `/` — Hero landing page (inline HTML in `web_modern.py`)

```
┌─────────────────────────────────────────────┐
│  LXL·QuantAxis                              │
│  AI-Native Quantitative Investment Research  │
│                                             │
│  Convert investment ideas into validated    │
│  research — without writing strategy code.  │
│                                             │
│  [Live Demo]  [View on GitHub]  [Research]  │
├─────────────────────────────────────────────┤
│  What It Does (3 cards)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ AI Thesis│ │ Factor   │ │ Institutional│ │
│  │→ Factors │ │→ Strategy│ │ Report       │ │
│  └──────────┘ └──────────┘ └──────────────┘ │
├─────────────────────────────────────────────┤
│  Navigation: Dashboard | Research | Demo    │
└─────────────────────────────────────────────┘
```

### Phase 2: Unified Navigation (modify 5 pages, ~100 lines)

Add a shared navigation bar to all HTML pages:
```
[LXL·QuantAxis]  [Dashboard] [Research Center] [Paper Trade] [GitHub]
```
- Fixed top bar
- Active page highlighted
- Consistent across `/`, `/research`, `/classic`, `/studio`, `/game`

### Phase 3: One-Click Demo (1 API route + JS, ~80 lines)

Add "Run Demo" button to landing page that:
1. Calls `/api/research/pipeline/thesis` with a built-in example
2. Shows live progress in the UI
3. Links to the generated report

### Phase 4: README Screenshot (manual)

- Take screenshots of the landing page, research center, and memory dashboard
- Add to `docs/assets/` and reference in README

### Phase 5: Redirect Cleanup (1 line)

- Change `/` from `redirect('/login')` to the new landing page
- `/login` accessible via nav bar link

### Files Changed

| Phase | Files | Risk |
|-------|-------|------|
| 1 | `web_modern.py` (+200 lines) | Low — additive only |
| 2 | `web_modern.py` (modify 5 inline HTML sections) | Low — nav bar only |
| 3 | `web_modern.py` (+1 route, +JS) | Low |
| 4 | `docs/assets/` (new PNGs) | None |
| 5 | `web_modern.py` (1 line) | None |

### What NOT to Change
- All API routes — untouched
- All business logic — untouched
- Templates (`login.html`, `studio.html`, etc.) — untouched
- `/classic` — keep but add nav
- `/game` — keep but add nav

---

## Recommendation

**Start with Phase 1 + 5** (landing page + redirect fix). This is the highest-impact, lowest-risk change. A first-time visitor to `http://127.0.0.1:5000` should see a showcase, not a login form.

**Total effort**: ~3 hours for all 5 phases.
