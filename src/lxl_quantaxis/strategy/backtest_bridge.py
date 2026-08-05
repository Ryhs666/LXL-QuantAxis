"""StrategySpec → BacktestEngine bridge.

Validates, compiles, and runs AI-generated strategies through the
existing backtest engine.  Zero code generation — pure AST compilation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.lxl_quantaxis.core.logging import get_logger
from src.lxl_quantaxis.strategy.validator import validate_strategy_spec, ValidationResult
from src.lxl_quantaxis.strategy.compiler.compiler import StrategyCompiler, CompiledStrategy

_log = get_logger("strategy.backtest_bridge")


@dataclass
class BridgeResult:
    """Complete validation + compilation + backtest result."""
    spec: object
    validation: ValidationResult = field(default_factory=ValidationResult)
    compiled: Optional[CompiledStrategy] = None
    backtest_metrics: dict = field(default_factory=dict)
    status: str = "pending"  # pending | validated | compiled | backtested | failed

    def to_dict(self) -> dict:
        return {
            "spec_name": self.spec.name if hasattr(self.spec, 'name') else "unknown",
            "status": self.status,
            "validation": self.validation.to_dict(),
            "compiled": self.compiled is not None,
            "backtest_metrics": self.backtest_metrics,
        }


def compile_strategy(spec) -> tuple[Optional[CompiledStrategy], ValidationResult]:
    """Validate then compile a StrategySpec.

    Returns (compiled_strategy, validation_result).
    compiled_strategy is None if validation failed.
    """
    result = validate_strategy_spec(spec)
    if not result.valid:
        _log.warning(f"Strategy validation failed: {result.errors}")
        return None, result

    try:
        compiler = StrategyCompiler()
        compiled = compiler.compile(spec)
        _log.info(f"Strategy compiled: {spec.name}")
        return compiled, result
    except Exception as e:
        result.errors.append(f"Compilation failed: {e}")
        result.valid = False
        return None, result


def run_backtest(spec, symbol: str = "601398", start_date: str = "2024-01-01",
                 initial_capital: float = 100_000) -> BridgeResult:
    """Full pipeline: validate → compile → backtest.

    Args:
        spec: StrategySpec to test
        symbol: Trading symbol
        start_date: Backtest start date
        initial_capital: Initial capital

    Returns:
        BridgeResult with all steps recorded
    """
    bridge = BridgeResult(spec=spec)
    bridge.status = "validating"

    # Step 1: Validate
    bridge.validation = validate_strategy_spec(spec)
    if not bridge.validation.valid:
        bridge.status = "failed"
        return bridge

    bridge.status = "compiling"

    # Step 2: Compile
    try:
        compiler = StrategyCompiler()
        bridge.compiled = compiler.compile(spec)
    except Exception as e:
        bridge.validation.errors.append(f"Compilation: {e}")
        bridge.validation.valid = False
        bridge.status = "failed"
        return bridge

    bridge.status = "backtesting"

    # Step 3: Run backtest
    try:
        from src.backtest.data_feed import get_data
        from src.backtest.engine import BacktestEngine
        from src.models.strategy import StrategyConfig

        data = get_data(symbol, "A股", start_date=start_date)
        if data is None or len(data) < 60:
            bridge.backtest_metrics = {"error": "insufficient data"}
            bridge.status = "failed"
            return bridge

        engine = BacktestEngine(initial_capital=initial_capital)

        # Build a runnable strategy from the compiled spec
        class _BridgeStrategy:
            def __init__(self, compiled_strat, factor_calculator=None):
                self.compiled = compiled_strat
                self.calc = factor_calculator
                self.config = StrategyConfig(name=symbol)

            def on_bar(self, i, bar_data, portfolio):
                from src.models.strategy import Signal
                from src.factors.definitions import FactorCalculator

                if i < 21:
                    return None

                self.calc = FactorCalculator(bar_data)
                factors = self.calc.compute_all().iloc[-1]

                context = {}
                for col in factors.index:
                    val = factors[col]
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        context[col] = float(val)

                has_pos = symbol in portfolio.positions

                if not has_pos and self.compiled.should_enter(context):
                    price = float(bar_data["close"].iloc[-1])
                    date = str(bar_data.iloc[-1].get("date", ""))[:10]
                    return Signal(action="BUY", symbol=symbol, date=date,
                                  price=price, reason="AI strategy entry")
                if has_pos and self.compiled.should_exit(context):
                    price = float(bar_data["close"].iloc[-1])
                    date = str(bar_data.iloc[-1].get("date", ""))[:10]
                    return Signal(action="SELL", symbol=symbol, date=date,
                                  price=price, reason="AI strategy exit")
                return None

        strategy = _BridgeStrategy(bridge.compiled)
        result = engine.run(strategy, data)

        bridge.backtest_metrics = {
            k: v for k, v in result.get("metrics", {}).items()
        }
        bridge.status = "backtested"

    except Exception as e:
        bridge.backtest_metrics = {"error": str(e)}
        bridge.status = "failed"

    return bridge


def quick_validate_and_test(spec, symbol: str = "601398") -> BridgeResult:
    """Validate + compile + quick backtest in one call."""
    return run_backtest(spec, symbol=symbol)
