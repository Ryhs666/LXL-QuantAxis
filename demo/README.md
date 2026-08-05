# LXL·QuantAxis V2.0 — Demo Guide

Run the AI research pipeline in under 5 minutes.

## Quick Start

```bash
# Run with built-in example
python demo/demo_ai_research.py

# Run with your own thesis
python demo/demo_ai_research.py "Your investment idea here"

# Run a specific example
python demo/demo_ai_research.py --example 1

# Enable LLM (requires API key)
python demo/demo_ai_research.py --llm "AI servers benefiting from cloud CAPEX"
```

## What Happens

The demo runs 7 stages automatically:

```
[1/7] Thesis Extraction     → Structured investment thesis from text
[2/7] Factor Mapping         → Thesis mapped to 28-factor registry
[3/7] Strategy Generation    → Factor model compiled to safe DSL strategy
[4/7] Validation             → Strategy checked against all safety rules
[5/7] Backtest               → Strategy tested on historical data
[6/7] AI Analysis            → Backtest results assessed and graded
[7/7] Report Generation      → Institutional Markdown + HTML report
```

## Output

```
reports/
├── <strategy_name>.md       # Markdown research report
├── <strategy_name>.html     # Styled HTML report
└── demo_<timestamp>.json    # Full pipeline results as JSON
```

## Built-in Examples

| # | Theme | Description |
|---|-------|-------------|
| 1 | AI Server Supply Chain | Cloud CAPEX driving GPU demand |
| 2 | Consumer Value Recovery | Consumer sector at historical low valuation |
| 3 | Semiconductor Cycle | Cycle bottom with AI-driven recovery |

## Requirements

- Python 3.12
- `pip install -r requirements.txt`
- LLM mode: set `AI_API_KEY` env var or configure `$QUANT_DATA_DIR/config/ai_config.json`

## Pipeline Diagram

```
Natural Language Input
        │
        ▼
[1] AI Thesis Extraction (ai_parser)
        │  ParsedThesis {symbol, core_argument, bull, bear, risk}
        ▼
[2] Factor Mapping (factor_mapper)
        │  FactorModel {theme, factors[{name, weight, reason}]}
        ▼
[3] Strategy Building (strategy_builder)
        │  StrategySpec {entry_rule, exit_rule, risk_rules}
        ▼
[4] Validation (validator)
        │  ValidationResult {valid, errors, warnings}
        ▼
[5] Backtest (backtest_bridge)
        │  Metrics {sharpe, return, drawdown, win_rate}
        ▼
[6] AI Analysis (backtest_analyzer)
        │  BacktestAssessment {summary, strengths, weaknesses}
        ▼
[7] Report Generation (report_generator)
        │
        ▼
    Research Report (.md + .html)
```
