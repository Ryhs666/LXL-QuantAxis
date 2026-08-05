# LXL·QuantAxis v2.0.0 — Release Notes

**Date**: 2026-08-05  
**Tag**: `v2.0.0`  
**Branch**: `fix/portfolio-metrics-v2`

## Overview

LXL·QuantAxis v2.0.0 is a complete re-architecture of the quantitative investment research platform, introducing an **AI-native research pipeline** that converts natural language investment theses into validated quantitative strategies without AI-generated code execution.

## Architecture

The platform now has a dual-layer architecture:

- **Legacy layer** (`src/`): 37,500+ lines of battle-tested quant infrastructure — factors, strategies, backtesting, data providers
- **V2 layer** (`src/lxl_quantaxis/`): Clean domain-driven design with zero reverse dependencies — AI pipeline, strategy DSL, portfolio intelligence

14 V1 modules import V2. Zero V2 modules import V1.

## Major Features

### AI Research Pipeline (New)
7-stage automated pipeline: Natural Language → Thesis → Factor Model → Strategy → Backtest → Analysis → Report

### Safe Strategy DSL (New)
Declarative rule strings compiled through AST allowlist. Zero AI code execution, zero `exec`/`eval`.

### Factor Intelligence
28-factor registry with IC analysis, decay detection, correlation heatmap, and style-to-factor mapping (growth, value, momentum, macro, event-driven).

### Portfolio Analytics
Explicit return semantics (simple/log, periodic/buy-and-hold), 4 allocation models with walk-forward validation, factor exposure analysis across 6 categories.

### Backtest Engine
T+1 execution (no look-ahead), A-share cost model, benchmark-relative metrics, signal lag queue, centralized cost configuration.

### Research Report Generator
8-section institutional reports in Markdown and HTML, auto-populated from pipeline outputs.

### Documentation
25 professional documents: architecture, pipeline, cases, ecosystem, application materials, contributing guide.

## Example Workflow

```bash
# 1. Run the demo pipeline
python demo/demo_ai_research.py "AI servers benefiting from cloud CAPEX growth"

# 2. Open the web UI
python web_modern.py  # → http://127.0.0.1:5000

# 3. Explore research cases
cat examples/research_cases/case_ai_infrastructure.md
```

## Breaking Changes

None. All existing APIs, CLI commands, and strategies are preserved. The V2 layer is purely additive.

## Future Roadmap

- **v2.1**: Real fundamental data integration (financial statements, macro indicators)
- **v2.2**: Multi-step AI research agent with iterative refinement
- **v2.3**: Docker support and cloud deployment
- **v3.0**: Collaborative research with multi-user notebooks

## Acknowledgments

Built with Python, Flask, Pandas, NumPy, Plotly, akshare, yfinance, and the open-source quant community.
