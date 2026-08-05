# LXL·QuantAxis — Project Showcase

## Vision

**Democratize quantitative investment research.** Make systematic factor-based analysis accessible to anyone with an investment idea, not just those who can write Python strategy code.

## Problem

Traditional quant research has a fundamental bottleneck:

```
Investment Idea → Manual Coding → Factors → Strategy → Backtest → Report
       ↑                                                    |
       └──────────── 3-7 days of boilerplate ───────────────┘
```

A researcher spends days translating a qualitative insight ("cloud CAPEX will benefit AI servers") into code before they can test whether it actually works.

## Solution

LXL·QuantAxis inverts the workflow:

```
Investment Idea (Natural Language)
       │
       ▼  [AI Thesis Extraction]
Structured Thesis
       │
       ▼  [Factor Mapping]
Weighted Factor Model
       │
       ▼  [Strategy DSL]
Safe, Compilable Strategy
       │
       ▼  [Backtest Engine]
Historical Validation
       │
       ▼  [AI Analysis + Report]
Institutional Research Output
```

**Time saved**: Days → minutes. **Safety**: Zero AI code execution.

## Architecture

The platform uses a dual-layer architecture:

```
┌──────────────────────────────────────────┐
│  Web UI (Flask)  │  CLI  │  Desktop GUI  │
├──────────────────────────────────────────┤
│  V2 Research Layer (src/lxl_quantaxis/)  │
│  AI Pipeline · Strategy DSL · Portfolio  │
├──────────────────────────────────────────┤
│  V1 Quant Engine (src/)                   │
│  28 Factors · 16 Strategies · Backtest   │
├──────────────────────────────────────────┤
│  Data: akshare · yfinance · SQLite ×10   │
└──────────────────────────────────────────┘
```

## Innovation

### 1. AI-Assisted, Not AI-Replaced
The platform structures and validates investment ideas. It never makes investment decisions. AI output is always schema-validated, human-reviewed, and saved to an immutable research record.

### 2. Safe by Design
Strategy rules use a declarative DSL compiled through an AST allowlist. No AI-generated code ever executes. This is a deliberate architectural choice, not a short-term workaround.

### 3. Research-First, Not Trading-First
Every thesis, factor model, and backtest result is preserved in a permanent, searchable research notebook. The platform is designed for systematic research, not automated trading.

## Application

**For Quant Researchers**: Reduce research cycle time from days to minutes. Test more ideas. Document every decision.

**For Students**: Learn quantitative methods by seeing how investment theses map to factors and strategies. The pipeline is transparent and explainable.

**For Individual Investors**: Apply institutional-grade factor analysis to your investment ideas. No coding required.

## Key Metrics

- **28 factors** across 5 categories
- **16 strategies** with parameter optimization
- **7-stage AI pipeline** from thesis to report
- **400+ tests** passing
- **25 professional documents**
- **Zero AI code execution**
