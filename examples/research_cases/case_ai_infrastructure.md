# Case 1: AI Infrastructure Investment Cycle

## 1. Research Question

**Is the AI infrastructure investment cycle sustainable, and how should a quantitative researcher systematically evaluate this thesis?**

This is a growth-oriented thesis driven by structural demand rather than cyclical factors. The key question is whether factor-based analysis can distinguish structural growth from speculative momentum.

## 2. Investment Thesis

### Background

Major cloud service providers (AWS, Azure, GCP) have announced $200B+ in combined AI infrastructure CAPEX for 2025-2026. GPU supply chains (NVIDIA H100/B200, server ODMs, HBM memory) show 12-18 month order backlogs. This differs from previous tech cycles in that demand is enterprise-driven rather than consumer-driven.

### Core Argument

Cloud CAPEX growth creates a multi-year structural demand cycle for AI server supply chains. Order visibility extends beyond typical cyclical patterns, suggesting sustained revenue growth for component suppliers.

### Bull Case

- Enterprise AI adoption is accelerating across industries (finance, healthcare, manufacturing)
- GPU supply remains constrained, maintaining pricing power for suppliers
- Order backlogs provide earnings visibility uncommon in hardware cycles
- New architectures (B200, GB200) drive ASP increases on top of unit growth

### Bear Case

- Current CAPEX levels may prove excessive if enterprise AI ROI disappoints
- Rapid chip iteration creates obsolescence risk (H100 → B200 in 18 months)
- Export controls on advanced chips could fragment the supply chain
- Valuation multiples already price in significant growth

## 3. AI Thesis Extraction

**Natural Language Input**:

```
AI服务器产业链受益于云厂商资本开支持续提升。
GPU算力需求增长确定性高，订单可见度达12个月以上。
风险：产能过剩、技术迭代快、芯片管制。
```

**AI Extraction Result** (rule-based mode):

| Field | Value |
|-------|-------|
| Symbol | AI_server |
| Core Argument | Cloud CAPEX driving GPU compute demand |
| Bullish | Cloud CAPEX growth, order visibility 12+ months |
| Bearish | Overcapacity risk, rapid tech iteration |
| Key Risks | Chip export controls |
| Style | Growth |
| Conviction | High |

## 4. Factor Mapping

The growth thesis maps to momentum and trend factors that capture sustained directional movement:

| Factor | Weight | Category | Why This Factor |
|--------|--------|----------|-----------------|
| momentum_score | 0.30 | momentum | Multi-period momentum captures sustained CAPEX-driven price trends |
| trend_strength | 0.25 | trend | Trend direction differentiates structural growth from noise |
| roc_10 | 0.25 | momentum | Short-term rate-of-change measures growth acceleration |
| volume_trend | 0.20 | volume | Rising volume confirms institutional participation in the trend |

**Why not value factors?** The thesis is growth-oriented, not value. Low PE/PB would actually contradict the thesis (it would suggest the market doesn't believe the growth story). Value factors like `ma_deviation` and `bollinger_pos` would generate false sell signals in a strong uptrend.

**Why not volatility factors?** Growth stocks typically have higher volatility. Penalizing volatility would reduce exposure to exactly the thesis we're testing.

## 5. Strategy Construction

```yaml
Strategy:
  name: AI Infrastructure Growth
  entry: momentum_score > 0.6 AND trend_strength > 0.5
  exit:  max_drawdown > 0.10
  risk:
    max_drawdown_pct: 10%
    stop_loss_pct: 5%
    position_size_pct: 20%
    max_single_pct: 15%
```

**Design rationale**:
- `momentum_score > 0.6`: Requires strong multi-period momentum (above median)
- `trend_strength > 0.5`: Confirms directional movement
- `AND` logic: Both conditions must hold — reduces false signals
- Drawdown exit: Protects against trend reversals without requiring factor condition timing

## 6. Backtest Interpretation

*This section explains how to interpret backtest metrics, not fabricated results.*

### Key Metrics to Evaluate

| Metric | What It Tells You | Good Signal |
|--------|-------------------|-------------|
| Sharpe Ratio | Risk-adjusted return consistency | > 1.0 suggests genuine alpha |
| Max Drawdown | Worst peak-to-trough decline | < 15% for a growth strategy |
| Win Rate | Percentage of profitable trades | > 50% suggests factor edge |
| Trade Count | Statistical significance | > 20 trades for reliable inference |

### What To Watch For

- **High Sharpe + low trade count**: May be overfit to a few lucky trades
- **High return + high drawdown**: Uncompensated risk — add stop loss
- **Low win rate + high Sharpe**: Trend-following pattern (few big wins, many small losses) — acceptable if expected

## 7. Risk Analysis

### Market Risk
- AI sentiment shift could trigger sector-wide drawdown
- Mitigation: `max_drawdown` exit rule at 10%

### Factor Risk
- Momentum factors underperform in range-bound markets
- Mitigation: `trend_strength` filter reduces exposure in sideways markets

### Model Risk
- Factor thresholds (0.6, 0.5) are defaults, not optimized
- Mitigation: Walk-forward optimization in production use

## 8. Research Conclusion

The AI infrastructure thesis is **well-suited to systematic factor-based research**. The growth thesis maps cleanly to momentum and trend factors, and the structural nature of the demand (enterprise CAPEX, not consumer speculation) provides a testable hypothesis.

**Next steps for a researcher**:
1. Run the strategy across the actual supply chain universe (server ODMs, GPU vendors, HBM suppliers)
2. Add a market regime filter to reduce exposure during broad tech selloffs
3. Compare factor exposures against a passive AI theme ETF to measure alpha

---

*This case study was generated using LXL·QuantAxis V2.0 AI Research Pipeline (rule-based mode). It demonstrates research methodology, not investment advice.*
