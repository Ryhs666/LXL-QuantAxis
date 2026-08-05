"""Domain-specific exceptions for LXL-QuantAxis.

Replace bare except Exception: pass with typed exceptions.
"""

from __future__ import annotations


class QuantAxisError(Exception):
    """Base exception for all domain errors."""


class DataError(QuantAxisError):
    """Data loading, validation, or integrity failure."""


class StrategyError(QuantAxisError):
    """Strategy definition, compilation, or execution failure."""


class BacktestError(QuantAxisError):
    """Backtest engine failure."""


class RiskError(QuantAxisError):
    """Risk check violation (pre-trade or post-trade)."""


class AIError(QuantAxisError):
    """AI/LLM interaction failure."""


class ConfigError(QuantAxisError):
    """Configuration validation failure."""


class SecurityError(QuantAxisError):
    """Authentication or authorization failure."""


class ValidationError(QuantAxisError):
    """Input validation failure — the caller made an error."""
