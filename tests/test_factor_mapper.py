"""Tests for AI factor mapper — thesis → quant factors."""

import pytest
from src.lxl_quantaxis.research.factor_mapper import (
    FactorModel, FactorWeight,
    map_thesis_to_factors, thesis_to_factor_dict,
    _build_factor_model, _load_factors,
)


class TestFactorMapping:
    def test_growth_style_maps_to_momentum(self):
        model = _build_factor_model("growth")
        assert len(model.factors) >= 2
        names = [f.name for f in model.factors]
        assert "momentum_score" in names

    def test_value_style_maps_to_mean_reversion(self):
        model = _build_factor_model("value")
        names = [f.name for f in model.factors]
        assert "ma_deviation" in names or "bollinger_pos" in names

    def test_unknown_style_uses_default(self):
        model = _build_factor_model("unknown")
        assert len(model.factors) >= 2

    def test_weights_sum_to_one(self):
        for style in ["growth", "value", "momentum", "macro"]:
            model = _build_factor_model(style)
            total = sum(f.weight for f in model.factors)
            assert 0.99 < total < 1.01, f"{style}: sum={total}"

    def test_confidence_for_unknown_is_lower(self):
        known = _build_factor_model("growth")
        unknown = _build_factor_model("unknown")
        assert unknown.confidence < known.confidence

    def test_source_is_rule_for_rule_based(self):
        model = _build_factor_model("growth")
        assert model.source == "rule"


class TestMapThesisToFactors:
    def test_uses_rule_mode_when_llm_off(self):
        model = map_thesis_to_factors(
            text="AI servers growing. CAPEX rising.", style="growth",
            use_llm=False,
        )
        assert model.source == "rule"
        assert len(model.factors) >= 2

    def test_empty_text_returns_model(self):
        model = map_thesis_to_factors(text="", style="growth", use_llm=False)
        assert len(model.factors) >= 2

    def test_all_factor_names_in_registry(self):
        registry = _load_factors()
        model = _build_factor_model("growth")
        for f in model.factors:
            assert f.name in registry, f"{f.name} not in FACTOR_REGISTRY"

    def test_validate_passes_for_rule_model(self):
        model = _build_factor_model("value")
        assert model.validate()

    def test_validate_fails_for_unknown_factor(self):
        model = FactorModel(
            factors=[FactorWeight(name="nonexistent", weight=1.0)],
        )
        assert not model.validate()

    def test_invalid_style_falls_back(self):
        model = _build_factor_model("this_style_does_not_exist")
        assert len(model.factors) >= 2  # uses default

    def test_thesis_to_dict(self):
        d = thesis_to_factor_dict(text="growth thesis")
        assert "theme" in d
        assert "factors" in d
        assert len(d["factors"]) >= 2

    def test_from_thesis_object(self):
        from src.lxl_quantaxis.research.thesis import InvestmentThesis
        thesis = InvestmentThesis(
            symbol="600519", title="茅台成长",
            core_argument="消费升级+提价", conviction="high",
        )
        model = map_thesis_to_factors(thesis=thesis, use_llm=False)
        assert len(model.factors) >= 2

    def test_deterministic_rule_output(self):
        m1 = _build_factor_model("momentum")
        m2 = _build_factor_model("momentum")
        assert m1.theme == m2.theme
        assert [f.name for f in m1.factors] == [f.name for f in m2.factors]
