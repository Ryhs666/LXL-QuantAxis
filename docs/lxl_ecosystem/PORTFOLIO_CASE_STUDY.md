# Portfolio Case Study — AI Infrastructure Research

*This case study demonstrates how the LXL Ecosystem processes a real investment research question from idea to validated report. No investment advice.*

## Research Question

**Is the AI infrastructure investment cycle structurally different from previous hardware cycles, and how should a systematic research process evaluate this thesis?**

## 1. Fundamental Research (LXL Equity Research Lab)

### Industry Analysis
- Global cloud CAPEX projected at $200B+ for 2025-2026
- GPU supply chain shows 12-18 month order visibility
- Enterprise AI adoption expanding beyond tech sector (finance, healthcare, manufacturing)
- Structural difference from prior cycles: demand is enterprise-driven, not consumer-driven

### Company Analysis
- Leading GPU vendor: 80%+ data center GPU market share, pricing power sustained
- Server ODMs: Revenue growth accelerating, margins expanding with product mix shift
- HBM memory: Supply constrained through 2025, ASP increases on each generation

### Valuation Framework
- Growth-adjusted PE suggests room for multiple expansion if growth sustains
- DCF sensitivity: 20-30% revenue CAGR scenarios produce significant upside
- Key variable: duration of CAPEX cycle (2-year vs 5-year assumption)

## 2. Investment Thesis

**Core Argument**: Cloud CAPEX growth creates a multi-year structural demand cycle for AI server supply chains that differs from previous hardware cycles in duration and end-demand composition.

**Conviction**: High (structural thesis, not cyclical timing)

## 3. Quant Framework (LXL-QuantAxis)

### Factor Selection Rationale

The thesis is growth-oriented and structural, not cyclical or value-contrarian. The factor model should capture sustained directional movement rather than mean-reversion or undervaluation signals.

**Selected Factors**:

| Factor | Weight | Selection Logic |
|--------|--------|-----------------|
| momentum_score | 0.30 | Multi-period momentum captures the sustained CAPEX-driven trend. Shorter lookback than typical to reduce lag at cycle start. |
| trend_strength | 0.25 | Trend direction confirmation differentiates structural growth from volatile noise. Acts as a filter on momentum signals. |
| roc_10 | 0.25 | Rate-of-change measures growth acceleration — important for identifying when CAPEX growth is accelerating vs. decelerating. |
| volume_trend | 0.20 | Rising volume confirms institutional participation in the trend. Without volume confirmation, price trends may be speculative. |

**Factors explicitly excluded**:
- Value factors (ma_deviation, bollinger_pos): Would generate sell signals in a strong uptrend
- Volatility factors: Growth stocks have higher vol; penalizing vol reduces exposure to the thesis
- Pattern factors (hammer, engulfing): Too noisy for a structural thesis

### Strategy Construction

```yaml
Strategy: AI Infrastructure Growth
Entry: momentum_score > 0.6 AND trend_strength > 0.5
Exit: max_drawdown > 0.10 OR trend_strength < 0.3
Risk:
  max_drawdown_pct: 10%
  stop_loss_pct: 5%
  position_size_pct: 20%
  max_single_pct: 15%
```

**Design Notes**:
- Higher momentum threshold (0.6 vs 0.5 default): Stronger signal requirement for structural thesis
- Trend strength exit (0.3): Exit if structural trend breaks, even without drawdown trigger
- Moderate position sizing (20%): Structural thesis justifies larger allocation than cycle-timing thesis

## 4. Risk Analysis

### Factor Risk
- Momentum factors underperform during sector rotation or broad market drawdowns
- Mitigation: Trend strength exit rule at 0.3 provides structural trend break protection

### Concentration Risk
- Heavy exposure to growth and momentum categories
- Mitigation: Position size cap at 20%; stop loss at 5%

### Model Risk
- Factor thresholds are default values, not optimized for this specific universe
- Mitigation: Walk-forward optimization in production use; periodic threshold review

## 5. Research Output

The complete pipeline produces an 8-section institutional research report combining:

- Analyst's fundamental research (LXL Equity Research Lab)
- AI-structured thesis with factor justification
- Safe DSL strategy rules
- Backtest metrics for validation
- Risk assessment with mitigation strategies

## 6. Key Takeaways

1. **Structural vs. cyclical matters**: The factor model for a structural growth thesis is fundamentally different from a cyclical timing thesis. Using the wrong factor template (e.g., value factors for a growth thesis) would generate systematically wrong signals.

2. **Factor exclusion is as important as factor selection**: Explicitly documenting why factors are excluded demonstrates analytical rigor and prevents future researchers from mistakenly adding contradictory signals.

3. **AI assists, analysts decide**: The platform structured the thesis into factors and generated strategy rules, but the analyst selected the growth template, reviewed every factor choice, and signed off on the final strategy.

---

*This case study demonstrates research methodology. It does not constitute investment advice. No real capital was deployed.*
