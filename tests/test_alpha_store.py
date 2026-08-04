"""Tests for AlphaSignalStore — signal memory database"""

import pytest
from src.ai.alpha_store import AlphaSignalStore, AlphaSignal, alpha_store


class TestAlphaSignal:
    def test_creates_signal_with_defaults(self):
        s = AlphaSignal(source="test", symbol="601398")
        assert s.source == "test"
        assert s.symbol == "601398"
        assert s.market == "A股"
        assert s.signal_id  # auto-generated
        assert s.date  # auto-generated

    def test_custom_values(self):
        s = AlphaSignal(
            source="factor_calc", symbol="000858", signal_action="BUY",
            factor_name="rsi_norm", market_regime=2, signal_strength=0.85,
            expected_return=0.02, strategy_name="ma_cross",
        )
        assert s.signal_action == "BUY"
        assert s.market_regime == 2
        assert s.signal_strength == 0.85

    def test_signal_id_is_unique(self):
        s1 = AlphaSignal(source="test", symbol="A")
        s2 = AlphaSignal(source="test", symbol="B")
        assert s1.signal_id != s2.signal_id


class TestAlphaSignalStore:
    def test_record_and_count(self):
        store = AlphaSignalStore()
        before = store.count()
        sid = store.record_signal(source="test", symbol="601398", signal_action="BUY")
        assert sid
        assert store.count() == before + 1

    def test_update_outcome(self):
        store = AlphaSignalStore()
        sid = store.record_signal(source="test", symbol="000858", signal_action="BUY")
        store.update_outcome(sid, 0.05, "win", 5.0)
        recent = store.get_recent(1)
        assert len(recent) >= 1

    def test_query_by_regime(self):
        store = AlphaSignalStore()
        store.record_signal(source="test", symbol="601398", market_regime=2, signal_action="BUY")
        results = store.query_by_regime(2, days=1)
        assert len(results) >= 1

    def test_query_by_source(self):
        store = AlphaSignalStore()
        store.record_signal(source="factor_calc", symbol="601398", signal_action="BUY")
        results = store.query_by_source("factor_calc", days=1)
        assert len(results) >= 1

    def test_query_by_factor(self):
        store = AlphaSignalStore()
        store.record_signal(source="test", symbol="601398", factor_name="rsi_norm", signal_action="BUY")
        results = store.query_by_factor("rsi_norm", days=1)
        assert len(results) >= 1

    def test_get_win_rate_by_factor(self):
        store = AlphaSignalStore()
        sid = store.record_signal(source="test", symbol="601398", factor_name="ma_cross", signal_action="BUY")
        store.update_outcome(sid, 0.03, "win", 3.0)
        wr = store.get_win_rate_by_factor(days=1)
        assert "ma_cross" in wr

    def test_get_regime_performance_matrix(self):
        store = AlphaSignalStore()
        sid = store.record_signal(source="test", symbol="601398", market_regime=2, factor_name="test", signal_action="BUY")
        store.update_outcome(sid, 0.02, "win", 2.0)
        matrix = store.get_regime_performance_matrix(days=1)
        assert 2 in matrix

    def test_get_factor_health(self):
        store = AlphaSignalStore()
        sid = store.record_signal(source="test", symbol="601398", factor_name="test_factor", signal_action="BUY")
        store.update_outcome(sid, 0.01, "win", 1.0)
        health = store.get_factor_health()
        assert "test_factor" in health

    def test_stats(self):
        store = AlphaSignalStore()
        stats = store.stats()
        assert "total_signals" in stats
        assert "db_path" in stats

    def test_record_batch(self):
        store = AlphaSignalStore()
        ids = store.record_batch([
            {"source": "test", "symbol": "A", "signal_action": "BUY"},
            {"source": "test", "symbol": "B", "signal_action": "SELL"},
        ])
        assert len(ids) == 2

    def test_mark_feedback_applied(self):
        store = AlphaSignalStore()
        sid = store.record_signal(source="test", symbol="601398")
        store.mark_feedback_applied(sid)
        # query to verify
        recent = store.query_by_symbol("601398", days=1)
        fed = [r for r in recent if r["signal_id"] == sid]
        assert len(fed) >= 1

    def test_global_singleton(self):
        assert alpha_store is not None
        assert isinstance(alpha_store, AlphaSignalStore)
