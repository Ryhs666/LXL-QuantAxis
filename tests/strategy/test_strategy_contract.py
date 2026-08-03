"""Contract, safety, and legacy-equivalence tests for the V2 strategy layer."""

from __future__ import annotations

import json
import unittest

import pandas as pd

from src.lxl_quantaxis.strategy import ParameterSpec, ParameterType, StrategyCompiler, StrategyRuleError, StrategySpec
from src.lxl_quantaxis.strategy.legacy import get_legacy_strategy_registry
from src.lxl_quantaxis.strategy.registry import StrategyRegistry
from src.lxl_quantaxis.strategy.spec import schema_text
from src.models.strategy import StrategyConfig
from src.strategies.library import RSIStrategy


def _spec(
    *, version: str = "1.0.0", entry: str = "close > threshold", exit_rule: str = "close < threshold"
) -> StrategySpec:
    return StrategySpec(
        strategy_id="research.price-threshold",
        version=version,
        name="Price threshold",
        description="A deterministic contract fixture.",
        entry_rule=entry,
        exit_rule=exit_rule,
        parameters=(ParameterSpec("threshold", ParameterType.NUMBER, 10.0, minimum=0.0),),
        data_requirements=("close",),
    )


class StrategyContractTests(unittest.TestCase):
    def test_manifest_matches_packaged_schema_shape(self) -> None:
        schema = json.loads(schema_text())
        manifest = _spec().to_manifest()

        self.assertEqual(set(schema["required"]), set(manifest))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(manifest["rules"]["entry"], "close > threshold")

    def test_registry_versions_and_validates_parameters(self) -> None:
        registry = (
            StrategyRegistry().register(_spec()).register(_spec(version="2.0.0")).register(_spec(version="10.0.0"))
        )
        self.assertEqual(registry.get("research.price-threshold").version, "10.0.0")
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(_spec())
        with self.assertRaisesRegex(ValueError, "unknown strategy parameter"):
            registry.create("research.price-threshold", {"leverage": 100})

    def test_allowlisted_rules_are_deterministic(self) -> None:
        compiler = StrategyCompiler({"between": lambda value, low, high: low <= value <= high})
        spec = _spec(entry="between(close, threshold, threshold + 5) and volume > 0")
        spec = StrategySpec(
            strategy_id=spec.strategy_id,
            version=spec.version,
            name=spec.name,
            description=spec.description,
            entry_rule=spec.entry_rule,
            exit_rule=spec.exit_rule,
            parameters=spec.parameters,
            data_requirements=("close", "volume"),
        )
        compiled = compiler.compile(spec)

        context = {"close": 12.0, "volume": 100, "threshold": 10.0}
        self.assertTrue(compiled.should_enter(context))
        self.assertEqual(compiled.should_enter(context), compiled.should_enter(context))

    def test_illegal_operators_and_malicious_access_are_rejected(self) -> None:
        compiler = StrategyCompiler()
        unsafe_rules = (
            "close ** 2 > threshold",
            "__import__('os')",
            "close.__class__",
            "close[0] > threshold",
            "(lambda: True)()",
        )
        for rule in unsafe_rules:
            with self.subTest(rule=rule), self.assertRaises(StrategyRuleError):
                compiler.compile(_spec(entry=rule))
        with self.assertRaisesRegex(ValueError, "safe lowercase identifier"):
            ParameterSpec("__class__", ParameterType.STRING, "x")
        with self.assertRaisesRegex(ValueError, "finite"):
            ParameterSpec("threshold", ParameterType.NUMBER, float("nan"))

    def test_legacy_registry_preserves_strategy_signals(self) -> None:
        registry = get_legacy_strategy_registry()
        parameters = {"rsi_period": 7, "oversold": 40, "overbought": 60}
        adapted = registry.create("legacy.rsi", parameters, runtime_options={"config": StrategyConfig(name="fixture")})
        direct = RSIStrategy(**parameters, config=StrategyConfig(name="fixture"))
        data = pd.DataFrame(
            {
                "open": [10.0, 9.0, 8.0, 7.0, 8.0],
                "high": [10.5, 9.5, 8.5, 7.5, 8.5],
                "low": [9.5, 8.5, 7.5, 6.5, 7.5],
                "close": [10.0, 9.0, 8.0, 7.0, 8.0],
                "volume": [100, 100, 100, 100, 100],
            }
        )

        self.assertEqual(adapted.buy_signal(data), direct.buy_signal(data))
        self.assertEqual(adapted.sell_signal(data), direct.sell_signal(data))
        self.assertEqual(registry.get("legacy.rsi").source, "legacy")


if __name__ == "__main__":
    unittest.main()
