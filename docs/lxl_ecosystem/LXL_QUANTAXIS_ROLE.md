# LXL-QuantAxis Role in the LXL Ecosystem

## Traditional Research Workflow

In a traditional equity research setup, the analyst owns the entire pipeline:

```
Analyst
    │
    ├── Company research (2-3 days)
    ├── Industry analysis (1-2 days)
    ├── Financial modeling (2-3 days)
    ├── Report writing (1-2 days)
    │
    ▼
Research Report (1-2 weeks total)
```

**Limitations**:
- No systematic validation of investment logic against historical data
- Factor and strategy construction requires separate quantitative skills
- Research is ephemeral — theses are not tracked or compared over time
- Reports are static documents, not connected to ongoing performance tracking

## Upgraded Workflow with LXL-QuantAxis

```
Analyst (LXL Equity Research Lab)
    │
    ├── Company & industry research (fundamental judgment)
    │
    ▼
Investment Thesis (natural language)
    │
    ▼
LXL-QuantAxis AI Pipeline
    │
    ├── AI Thesis Extraction → structured investment argument
    ├── Factor Mapping → thesis converted to quantifiable factors
    ├── Strategy Construction → safe DSL strategy from factors
    ├── Backtest Validation → historical performance test
    ├── AI Analysis → automated strengths/weaknesses assessment
    │
    ▼
Integrated Research Report (fundamental + quantitative)
    │
    ▼
Research Notebook (permanent, searchable, trackable)
```

## What Changes

| Aspect | Before | After |
|--------|--------|-------|
| Research cycle | 1-2 weeks | 2-3 days (fundamental) + automated quant |
| Factor analysis | Manual, ad-hoc | Systematic, 28-factor registry |
| Strategy testing | Requires separate quant skills | AI-generated, safe DSL |
| Research tracking | Static documents | Permanent, searchable notebook |
| Reproducibility | Analyst-dependent | Manifest captures git/env/params |
| Report format | Word/PDF | Markdown + styled HTML + tables |

## What Stays the Same

- **Analyst judgment**: AI does not replace investment insight. It structures, validates, and documents it.
- **Fundamental research**: Company analysis, industry mapping, and financial modeling remain human-driven.
- **Final decision**: The analyst reviews and signs off on all AI-generated content before it becomes part of the research record.

## Integration Points

LXL-QuantAxis connects to the research lab at three points:

1. **Input**: Analyst writes investment thesis in natural language → `ai_parser.py` extracts structured thesis
2. **Processing**: Thesis flows through factor mapper, strategy builder, backtest engine
3. **Output**: Integrated report combines analyst's fundamental view with platform's quantitative validation
