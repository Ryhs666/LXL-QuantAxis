# Case 2: Consumer Sector Value Recovery

## 1. Research Question

**Is the consumer sector undervalued at current levels, and can mean-reversion factors systematically identify entry points?**

This is a value-oriented thesis driven by valuation normalization. The key question is whether factor-based analysis can distinguish genuine undervaluation from a value trap.

## 2. Investment Thesis

### Background

China's consumer sector has underperformed the broad market for 3 consecutive years. Sector PE has compressed from 35x to 18x, approaching levels last seen during the 2018 trade war bottom. Leading consumer staples companies have maintained revenue growth of 8-12% despite macro headwinds, suggesting earnings resilience.

### Core Argument

Consumer sector valuation is at historical lows while earnings fundamentals remain intact. Market pessimism about consumption downgrade is over-discounted. Mean-reversion factors should identify entry points when prices deviate significantly from fundamental trends.

### Bull Case

- Sector PE at 18x vs 5-year average of 28x — 35% discount to historical mean
- Leading companies (liquor, dairy, condiments) maintained positive earnings growth through the downturn
- Policy stimulus targeting consumption could catalyze re-rating
- Household savings rate elevated — potential for consumption recovery

### Bear Case

- Consumer confidence remains weak — "consumption downgrade" may be structural, not cyclical
- Demographic headwinds (aging population, declining birth rate) reduce long-term growth
- E-commerce competition erodes traditional brand pricing power
- Value trap risk: low PE may reflect permanently lower growth expectations

## 3. AI Thesis Extraction

**Natural Language Input**:

```
消费板块估值处于历史低位，经济复苏预期升温。
龙头企业市场份额提升，现金流充裕。
风险：消费复苏不及预期、渠道库存积压。
```

**AI Extraction Result** (rule-based mode):

| Field | Value |
|-------|-------|
| Symbol | Consumer_sector |
| Core Argument | Consumer sector undervalued, recovery expected |
| Bullish | Leading companies gaining share, strong cash flow |
| Bearish | Recovery slower than expected, channel inventory |
| Key Risks | Consumption recovery pace, channel destocking |
| Style | Value |
| Conviction | Medium |

## 4. Factor Mapping

The value thesis maps to mean-reversion and low-volatility factors:

| Factor | Weight | Category | Why This Factor |
|--------|--------|----------|-----------------|
| ma_deviation | 0.35 | trend | Price deviation from MA signals oversold conditions |
| bollinger_pos | 0.25 | volatility | Bollinger position identifies statistical extremes |
| volatility | 0.20 | volatility | Low volatility confirms defensive positioning |
| volume_ratio | 0.20 | volume | Declining volume during selloff suggests capitulation |

**Why not momentum factors?** A value thesis contradicts momentum. We're betting on reversal, not continuation. Adding momentum factors would dilute the signal.

**Why volatility matters**: In a value context, low volatility confirms that the selling pressure is exhausting. High volatility would suggest the downtrend still has momentum.

## 5. Strategy Construction

```yaml
Strategy:
  name: Consumer Value Mean Reversion
  entry: ma_deviation < 0.3 AND bollinger_pos < 0.3
  exit:  ma_deviation > 0.6 OR max_drawdown > 0.08
  risk:
    max_drawdown_pct: 8%
    stop_loss_pct: 5%
    position_size_pct: 15%
    max_single_pct: 10%
```

**Design rationale**:
- `ma_deviation < 0.3`: Price significantly below moving average (oversold)
- `bollinger_pos < 0.3`: Near lower Bollinger band (statistical extreme)
- Tighter drawdown (8% vs 10%): Value strategies should have lower volatility
- Smaller position (15%): Value traps require more conservative sizing

## 6. Backtest Interpretation

*This section explains how to interpret backtest metrics for value strategies.*

### Key Metrics for Value Strategies

| Metric | What To Look For | Red Flag |
|--------|-----------------|----------|
| Sharpe Ratio | > 0.8 acceptable for value | < 0.3 suggests no edge |
| Win Rate | > 55% for mean-reversion | < 45% suggests value trap |
| Average Holding Period | 10-30 days typical | > 60 days suggests not mean-reverting |
| Calmar Ratio | > 1.0 (return/drawdown) | < 0.5 suggests poor risk-reward |

### Value-Specific Pitfalls

- **Value trap**: Stock stays cheap and gets cheaper. The factor keeps generating buy signals as the price keeps falling.
- **False reversal**: Brief bounce followed by continued decline. Exit rule must distinguish genuine reversal from dead cat bounce.
- **Sector correlation**: Consumer stocks often move together. Diversification benefit is limited.

## 7. Risk Analysis

### Market Risk
- Macro slowdown could push valuations even lower
- Mitigation: Tighter drawdown exit (8%), stop at 5%

### Factor Risk
- Mean-reversion factors generate false signals in trending markets
- Mitigation: Require both `ma_deviation` AND `bollinger_pos` to confirm

### Model Risk
- Historical PE ranges may not be relevant if growth expectations have structurally changed
- Mitigation: Monitor earnings revisions; if earnings are being cut, the "value" is illusory

## 8. Research Conclusion

The consumer value thesis is **moderately suited** to systematic factor research. Mean-reversion factors can identify statistical extremes, but the researcher must distinguish genuine undervaluation from structural decline. The key differentiator is earnings trajectory — if earnings are stable or growing while prices fall, the value signal is genuine. If earnings are declining, it's a trap.

**Next steps for a researcher**:
1. Filter universe to companies with positive YoY earnings growth
2. Add a sector-relative valuation check (PE vs sector median)
3. Backtest during different macro regimes (2018 trade war, 2020 COVID, 2022 lockdowns)

---

*This case study illustrates research methodology. Not investment advice.*
