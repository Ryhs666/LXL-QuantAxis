# v2.1 Pre-Development Audit

**Date**: 2026-08-05 | **Branch**: `fix/portfolio-metrics-v2` | **CI**: Green

## Repository Structure

| Area | Status | Note |
|------|--------|------|
| Clean gitignore | Pass | .idea, dist, build, .ruff_cache excluded |
| Sensitive files | Pass | `8`, `_inline_js.js` removed |
| Duplicate files | Minor | `demo_ai_research.py` exists at root AND in `demo/` |
| Build artifacts | Clean | Not committed |

## README Professionalism

| Aspect | Rating |
|--------|--------|
| First-screen clarity | Good — pipeline diagram + badges + one-liner |
| Demo output | Good — real CLI output shown |
| Architecture | Good — layered diagram |
| Quick start | Good — 3 commands to running |
| Research cases | Good — 3 linked cases |
| Roadmap | Adequate — v2.1-v3.0 outlined |

## Release Readiness

| Item | Status |
|------|--------|
| Tag v2.0.0 | Created |
| CHANGELOG | Complete |
| Release notes | docs/RELEASE_NOTES_v2.0.0.md |
| PR #6 | Open to merge into main |
| CI green | test workflow + CI workflow passing |

## Missing Documentation

| Priority | Item |
|----------|------|
| High | `.env.example` — missing. Should document `JWT_SECRET_KEY`, `ADMIN_PASSWORD`, `QUANT_DATA_DIR` |
| Medium | API documentation — 60+ routes, no OpenAPI spec |
| Low | Module-level docstrings — many legacy modules have minimal docs |

## Security Issues

| Severity | Issue | Detail |
|----------|-------|--------|
| Low | `uv.lock` committed | Contains hashes, desirable for reproducibility |
| Info | No `.env.example` | Makes secure setup harder for new users |
| Info | Bandit B310 (urllib) | Acceptable — external API calls with HTTPS |
| Info | Bandit B324 (MD5) | Acceptable — cache keys, not security use |

## Packaging & Deployment

| Item | Status |
|------|--------|
| pyproject.toml | Complete — metadata, dependencies, tool configs |
| Build | `python -m build` works |
| Docker | Missing — local install only |
| CI Matrix | ubuntu + windows, Python 3.11 + 3.12 |

## Critical Issues (Must Fix)

1. **Missing `.env.example`** — New users don't know which env vars to set.
2. **Duplicate `demo_ai_research.py`** — Root copy should be a thin wrapper pointing to `demo/demo_ai_research.py`.

## Recommended Improvements

1. Add `.env.example` with safe defaults and comments
2. Remove root `demo_ai_research.py`, keep only `demo/demo_ai_research.py`
3. Add OpenAPI/Swagger for key API routes
4. Add `Dockerfile` for reproducible deployment
5. Add screenshots to README (`docs/assets/`)

## v2.1 Roadmap Suggestions

| Priority | Feature | Rationale |
|----------|---------|-----------|
| P0 | Fix duplicate files + add .env.example | Polish |
| P1 | Docker support | Deployment consistency |
| P1 | API documentation (OpenAPI) | Developer experience |
| P2 | Real fundamental data (financial statements) | Research capability |
| P2 | Multi-step AI agent | Research depth |
| P2 | Screenshots in README | Showcase |
| P3 | Live paper trading bridge | Forward testing |
| P3 | Multi-user research notebook | Collaboration |
