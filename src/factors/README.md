# LXL QuantAxis — Factor Research Laboratory

> v6.0 · Institutional Multi-Factor Research Framework

---

## Factor Research Philosophy

In LXL QuantAxis, **factors are the atomic unit of quantitative research**. Every strategy, every signal, every diagnostic begins with factor computation.

We adhere to the following principles:

1. **Every factor is self-describing.** A factor carries its own name, category, parameters, and documentation — no external lookup needed.
2. **Factors are composable.** Individual factors combine into multi-factor signals through the Signal Composer. You control the logic: AND, OR, or weighted scoring.
3. **Factors are evaluable.** Every factor can be assessed via Information Coefficient (IC), Rank IC, and signal distribution analysis.
4. **Factors are extensible.** Adding a new factor is a single Python class. The registry discovers it automatically.

---

## Factor Categories

| Category | Count | Description |
|----------|-------|-------------|
| **Momentum** | 5 | Price velocity, ROC, multi-period momentum |
| **Trend** | 4 | Directional bias, MA alignment, trend strength |
| **Volatility** | 4 | Historical vol, Bollinger Bands, ATR |
| **Liquidity** | 3 | Volume ratio, volume trend, OBV divergence |
| **Pattern** | 2 | Hammer, engulfing candlestick patterns |
| **Value** | 3 | PE, PB, EV/EBITDA |
| **Quality** | 3 | ROE, gross margin, FCF yield |
| **Growth** | 3 | Revenue growth, EPS growth, profit growth |
| **Total** | **27** | 18 technical + 9 fundamental |

---

## Usage

### Quick Start

```python
from src.factors.factor_registry import get_factor, list_factors

# List all factors
print(list_factors())          # ['atr_ratio', 'bollinger_pos', ...]
print(list_factors("value"))   # ['value_ev_ebitda', 'value_pb', 'value_pe']

# Get a factor and compute
factor = get_factor("momentum_score")
signal = factor.calculate(data)    # data = OHLCV DataFrame
print(factor.description())
```

### Factor Evaluation

```python
from src.factors.core.evaluator import evaluate_factor, evaluate_all_factors

# Evaluate a single factor
result = evaluate_factor("momentum_score", data)
print(result["IC"])        # Information Coefficient
print(result["Rank_IC"])   # Rank IC

# Evaluate all factors
df = evaluate_all_factors(data)
print(df[["factor", "IC", "Rank_IC"]].head(10))
```

### Multi-Factor Composite

```python
from src.factors.composite.scoring import composite_score

# Equal-weighted composite
composite = composite_score(
    data,
    factors=["momentum_score", "trend_strength", "volume_ratio"]
)

# Custom-weighted composite
composite = composite_score(
    data,
    factors=["momentum_score", "trend_strength", "value_pe"],
    weights={"momentum_score": 2.0, "trend_strength": 1.0, "value_pe": 1.5}
)
```

### Signal Composition (Strategy Building)

```python
from src.factors.composer import SignalComposer

composer = (SignalComposer("My Strategy")
    .rsi_oversold(14, 30, weight=3)
    .volume_surge(1.5, weight=2)
    .set_logic("weighted", threshold=4.0)
    .rsi_overbought(14, 70, weight=2)
    .set_logic("or", action="SELL"))

signal = composer.evaluate(data)
```

---

## Directory Structure

```
src/factors/
├── __init__.py                  # Module exports
├── definitions.py               # Legacy FactorCalculator + FACTOR_REGISTRY (18 tech)
├── fundamental.py               # Legacy FundamentalFactors class
├── factor_registry.py           # Unified registry (auto-registers all factors)
├── README.md                    # This file
│
├── core/                        # Framework foundation
│   ├── factor_base.py           # BaseFactor abstract class
│   ├── registry.py              # FactorRegistry singleton
│   └── evaluator.py             # FactorEvaluator (IC, Rank IC, decay)
│
├── technical/                   # 18 technical factors
│   ├── momentum.py              # RSI, ROC, momentum_score, price_position, macd_hist
│   ├── trend.py                 # ma_deviation, ma_alignment, ma_slope, trend_strength
│   ├── volatility.py            # volatility, bollinger_pos, bollinger_width, atr_ratio
│   └── liquidity.py             # volume_ratio, volume_trend, obv_divergence, hammer, engulfing
│
├── fundamental/                 # 9 institutional fundamental factors
│   ├── value.py                 # PE, PB, EV/EBITDA
│   ├── quality.py               # ROE, Gross Margin, FCF Yield
│   └── growth.py                # Revenue Growth, EPS Growth, Profit Growth
│
└── composite/                   # Multi-factor composition
    ├── composer.py              # (imported from parent — SignalComposer)
    └── scoring.py               # FactorScoring engine
```

---

## Extending the Framework

### Add a New Technical Factor

```python
# In src/factors/technical/ (or a new file)
from src.factors.core.factor_base import BaseFactor

class MyNewFactor(BaseFactor):
    name = "my_factor"
    category = "momentum"
    display_name = "My Custom Factor"
    _description = "Description of what this factor measures."
    params = {"period": 20}

    def calculate(self, data):
        period = self._params["period"]
        # Your computation here
        result = data["close"].pct_change(period)
        return self._sigmoid(result, center=0.0, steepness=1.0)

# Register
from src.factors.core.registry import registry
registry.register(MyNewFactor())
```

### Add a New Fundamental Factor

```python
# In src/factors/fundamental/
from src.factors.core.factor_base import BaseFactor

class DividendYieldFactor(BaseFactor):
    name = "value_dividend_yield"
    category = "value"
    display_name = "Dividend Yield"
    _description = "..."
    source = "fundamental"

    def calculate(self, data):
        # ...

    @staticmethod
    def fetch(symbol: str):
        # AKShare fetch logic
        pass
```

---

*LXL QuantAxis v6.0 · Factor Research Laboratory · LXL Equity Research Lab*
