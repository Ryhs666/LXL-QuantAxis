# LXL·QuantAxis V2.0 — Research Case Library

This library demonstrates how LXL·QuantAxis transforms **human investment ideas** into **structured quantitative research**. Each case follows the same 8-section format, showing every stage of the AI research pipeline.

## What These Cases Demonstrate

```
Human Research Question
        │
        ▼
Investment Thesis (structured argument)
        │
        ▼
AI Thesis Extraction (natural language → ParsedThesis)
        │
        ▼
Factor Mapping (thesis → 28-factor registry)
        │
        ▼
Strategy Construction (factors → safe DSL rules)
        │
        ▼
Backtest Interpretation (metrics explanation, no fabricated returns)
        │
        ▼
Risk Analysis (market/factor/model risk)
        │
        ▼
Research Conclusion
```

## Cases

| # | Case | Theme | Style | Research Question |
|---|------|-------|-------|-------------------|
| 1 | AI Infrastructure | AI服务器产业链 | Growth | Is the AI infrastructure investment cycle sustainable? |
| 2 | Consumer Recovery | 消费板块复苏 | Value | Is the consumer sector undervalued at current levels? |
| 3 | Semiconductor Cycle | 半导体周期 | Macro-Momentum | Are we at a semiconductor cycle bottom? |

## Important Notes

- **No fabricated returns**: Backtest metrics sections explain how to interpret metrics, not fake results.
- **Not investment advice**: These cases illustrate research methodology, not recommendations.
- **Rule-based AI**: Cases use deterministic rule-based mode for reproducibility.
- **Proxy symbols**: Backtest demonstrations use generic symbols (000001) for illustration.

## Running a Case

```bash
python demo/demo_ai_research.py --example 1
python demo/demo_ai_research.py --example 2
python demo/demo_ai_research.py --example 3
```
