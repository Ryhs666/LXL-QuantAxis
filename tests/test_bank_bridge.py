"""Tests for UnifiedStrategyBank — bridge between evolution and user banks"""

import pytest
from src.ai.bank_bridge import UnifiedStrategyBank, unified_bank


class TestUnifiedStrategyBank:
    def test_list_all(self):
        bank = UnifiedStrategyBank()
        results = bank.list_all()
        assert isinstance(results, list)

    def test_get_best(self):
        bank = UnifiedStrategyBank()
        best = bank.get_best(n=3)
        assert isinstance(best, list)
        assert len(best) <= 3

    def test_search(self):
        bank = UnifiedStrategyBank()
        results = bank.search("ma_cross")
        assert isinstance(results, list)

    def test_find_by_factor(self):
        bank = UnifiedStrategyBank()
        results = bank.find_by_factor("rsi_norm")
        assert isinstance(results, list)

    def test_stats(self):
        bank = UnifiedStrategyBank()
        stats = bank.stats()
        assert "evolution_bank" in stats
        assert "user_bank" in stats
        assert "total" in stats

    def test_get_best_for_regime(self):
        bank = UnifiedStrategyBank()
        # Even without data, should return a list
        results = bank.get_best_for_regime(2, n=3)
        assert isinstance(results, list)

    def test_global_singleton(self):
        assert unified_bank is not None
