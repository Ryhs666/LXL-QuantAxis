# Case 3: Semiconductor Cycle Bottom

## 1. Research Question

**Are we at a semiconductor cycle bottom, and how can factor-based analysis time the inflection point?**

This is a macro-momentum thesis combining cyclical analysis with trend confirmation. The challenge is that cycle bottoms are only visible in hindsight — factors must detect the turn without excessive lag.

## 2. Investment Thesis

### Background

The semiconductor industry follows a well-documented 3-4 year boom-bust cycle driven by capacity additions and demand fluctuations. Current indicators suggest the cycle is approaching a trough: memory chip prices have stabilized after 18 months of decline, foundry utilization rates are bottoming, and inventory days at major chip designers have peaked.

### Core Argument

Global semiconductor cycle is near a bottom, with inventory destocking entering its final phase. AI-driven demand (data center GPUs, edge inference chips) will provide the catalyst for the next upcycle. Early-cycle indicators (booking trends, lead time expansion) should confirm the turn before it appears in earnings.

### Bull Case

- Memory prices (DRAM, NAND) have stabilized — historically a 1-2 quarter leading indicator
- AI inference demand creates a new structural growth driver beyond traditional PC/smartphone cycles
- Inventory days at NVIDIA, AMD, Qualcomm peaked in Q3 2024 and are declining
- Foundry utilization at TSMC, SMIC rebounding from 70% to 85%+

### Bear Case

- "AI-driven cycle" may already be priced in after 2024 rally
- Traditional end markets (PC, smartphone, automotive) remain weak
- Geopolitical tensions (Taiwan Strait, export controls) create supply chain uncertainty
- Cycle bottom could extend if enterprise AI adoption takes longer than expected

## 3. AI Thesis Extraction

**Natural Language Input**:

```
全球半导体周期接近底部，库存去化进入尾声。
AI驱动的需求增量将成为下一轮上行周期的催化剂。
风险：地缘政治、出口管制升级、需求反弹幅度不确定。
```

**AI Extraction Result** (rule-based mode):

| Field | Value |
|-------|-------|
| Symbol | Semiconductor |
| Core Argument | Cycle bottom, AI demand to drive next upcycle |
| Bullish | Inventory destocking ending, AI demand catalyst |
| Bearish | Geopolitical risks, export controls, demand uncertainty |
| Key Risks | Geopolitics, export controls, demand magnitude |
| Style | Macro-Momentum |
| Conviction | Medium |

## 4. Factor Mapping

The cycle-bottom thesis combines macro awareness with momentum confirmation:

| Factor | Weight | Category | Why This Factor |
|--------|--------|----------|-----------------|
| trend_strength | 0.35 | trend | Macro direction — confirms cycle is actually turning |
| bollinger_width | 0.25 | volatility | Expanding Bollinger width signals regime change |
| volatility | 0.25 | volatility | Rising vol during bottoming process is normal |
| ma_slope | 0.15 | trend | MA slope direction change is an early turn signal |

**Why macro-style factors?** Cycle bottoms are macro events, not stock-specific. Individual stock factors (RSI, volume ratio) are noisy at turning points. Macro factors (trend, volatility regime) better capture the systemic nature of the thesis.

**Why no pure momentum?** At a cycle bottom, momentum is still negative (prices have been falling). Pure momentum factors would keep you out. The thesis requires detecting the *change* in momentum, not the level.

## 5. Strategy Construction

```yaml
Strategy:
  name: Semiconductor Cycle Bottom
  entry: trend_strength > 0.4 AND bollinger_width > 0.5
  exit:  trend_strength < 0.3 OR max_drawdown > 0.12
  risk:
    max_drawdown_pct: 12%
    stop_loss_pct: 7%
    position_size_pct: 15%
    max_single_pct: 10%
```

**Design rationale**:
- `trend_strength > 0.4`: Lower threshold than growth strategy — at cycle bottom, trend is just beginning
- `bollinger_width > 0.5`: Expanding width signals the end of the low-volatility downtrend
- Wider drawdown (12%): Cycle bottoms are volatile; too-tight stops get whipsawed
- Smaller position (15%): Higher uncertainty at inflection points

## 6. Backtest Interpretation

*This section explains how to interpret backtest metrics for cycle-timing strategies.*

### Key Metrics for Cycle Strategies

| Metric | What To Look For | Red Flag |
|--------|-----------------|----------|
| Information Ratio | Consistency of timing skill | < 0.3 suggests no timing edge |
| Max Drawdown | Acceptable given cycle volatility | > 20% suggests poor entry timing |
| Average Entry Delay | Bars between cycle bottom and entry | > 20 bars suggests factor is too slow |

### Cycle-Specific Pitfalls

- **False bottom**: Factors signal a turn, but the cycle continues down. This is the most expensive error.
- **Late entry**: Factors confirm the turn too late, after most of the move. Reduce position size or accept lower returns.
- **Whipsaw**: Factors flip between buy/sell during a volatile bottoming process. Require confirmation from multiple factors.

## 7. Risk Analysis

### Market Risk
- Cycle bottom may extend for multiple quarters
- Mitigation: Use moderate position sizing (15%), wide stop (7%)

### Factor Risk
- Trend factors lag at turning points by design
- Mitigation: Lower entry threshold (0.4 vs 0.6) to reduce lag

### Model Risk
- Historical cycle patterns may not repeat given AI-driven structural change
- Mitigation: Combine with fundamental data (inventory days, utilization rates) in production

## 8. Research Conclusion

The semiconductor cycle thesis is **challenging but viable** for systematic factor research. The key difficulty is timing — factors must detect the turn without excessive lag or false signals. The approach outlined here uses lower thresholds and confirmation from volatility regime change to balance speed and accuracy.

**Next steps for a researcher**:
1. Add fundamental data: inventory days, foundry utilization, memory spot prices
2. Test across multiple past cycles (2008, 2012, 2016, 2019, 2023) for consistency
3. Consider a staged entry: small position at first signal, add on confirmation

---

*This case study illustrates research methodology. Not investment advice.*
