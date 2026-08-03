"""Shared legacy backtest doubles that avoid external side effects."""

from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from unittest.mock import Mock, patch

from src.models.strategy import Signal


class BuyOnSecondBar:
    """Emit one deterministic close-derived BUY signal."""

    def on_bar(self, index, data, portfolio):
        if index != 1:
            return None
        row = data.iloc[-1]
        return Signal(
            action="BUY",
            symbol=row["symbol"],
            date=str(row["date"])[:10],
            price=float(row["close"]),
            quantity=100,
            reason="characterization signal",
        )


@contextmanager
def without_audit_files():
    """Replace the import-time audit singleton before BacktestEngine.run."""
    audit_module = types.ModuleType("src.audit.TradeAudit")
    audit_module.audit = Mock()
    with patch.dict(sys.modules, {"src.audit.TradeAudit": audit_module}):
        yield
