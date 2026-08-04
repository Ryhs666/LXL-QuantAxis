"""Unified configuration loader — single source of truth.

Priority (highest to lowest):
  1. Environment variables (QUANT_ prefix)
  2. YAML config file (QUANT_CONFIG_PATH or ./config.yaml)
  3. Built-in defaults

All modules must use this loader.  Hardcoded paths are forbidden.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent.parent


# ═══════════════════════════════════════════════════════════
# Defaults — the single source of truth
# ═══════════════════════════════════════════════════════════

DEFAULTS: dict[str, Any] = {
    # Paths
    "data_dir": "~/lxl_quantaxis_data",
    "cache_dir": "{data_dir}/cache",
    "log_dir": "{data_dir}/logs",
    "journal_dir": "{data_dir}/journal",
    "charts_dir": "{data_dir}/charts",
    "reports_dir": "{data_dir}/reports",
    "config_dir": "{data_dir}/config",

    # Backtest
    "initial_capital": 100_000,
    "commission_rate": 0.0003,
    "slippage": 0.001,
    "position_size_pct": 0.2,
    "risk_free_rate": 0.02,

    # Risk
    "max_positions": 10,
    "stop_loss_pct": 0.05,
    "max_drawdown_limit": 0.25,
    "risk_trailing_stop_pct": 0.05,
    "risk_max_drawdown_pct": 0.10,
    "risk_kelly_fraction": 0.5,
    "risk_max_single_position_pct": 0.15,

    # A-share
    "a_stock_lot_size": 100,
    "a_stock_stamp_tax": 0.001,

    # System
    "log_level": "INFO",
    "verbose": True,

    # Realtime
    "realtime_poll_interval": 3,
    "realtime_retry_interval": 10,
}


@dataclass(frozen=True, slots=True)
class QuantConfig:
    """Immutable typed configuration, loaded once at startup."""

    data_dir: str
    cache_dir: str
    log_dir: str
    journal_dir: str
    charts_dir: str
    reports_dir: str
    config_dir: str

    initial_capital: float
    commission_rate: float
    slippage: float
    position_size_pct: float
    risk_free_rate: float

    max_positions: int
    stop_loss_pct: float
    max_drawdown_limit: float

    log_level: str
    verbose: bool
    realtime_poll_interval: int

    _loaded_from: tuple[str, ...] = field(default=(), repr=False)

    @classmethod
    def load(
        cls,
        config_path: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> QuantConfig:
        """Load configuration from YAML/JSON file + environment variables.

        Args:
            config_path: path to YAML or JSON config file.
                         Default: $QUANT_CONFIG_PATH or <project_root>/config.yaml
            env: environment dict (defaults to os.environ)
        """
        env = env or os.environ
        values = dict(DEFAULTS)

        # 1. Load from file
        file_path = config_path or env.get(
            "QUANT_CONFIG_PATH",
            str(_project_root() / "config.yaml"),
        )
        _load_file(file_path, values)

        # 2. Override from environment (QUANT_ prefix)
        for key in list(values.keys()):
            env_key = f"QUANT_{key.upper()}"
            if env_key in env:
                values[key] = _coerce(env[env_key], values[key])

        # 3. Resolve path templates
        data_dir = _resolve_path(values["data_dir"], env)
        for path_key in ["cache_dir", "log_dir", "journal_dir",
                         "charts_dir", "reports_dir", "config_dir"]:
            values[path_key] = values[path_key].format(data_dir=data_dir)
            values[path_key] = _resolve_path(values[path_key], env)

        return cls(
            data_dir=data_dir,
            cache_dir=values["cache_dir"],
            log_dir=values["log_dir"],
            journal_dir=values["journal_dir"],
            charts_dir=values["charts_dir"],
            reports_dir=values["reports_dir"],
            config_dir=values["config_dir"],
            initial_capital=float(values["initial_capital"]),
            commission_rate=float(values["commission_rate"]),
            slippage=float(values["slippage"]),
            position_size_pct=float(values["position_size_pct"]),
            risk_free_rate=float(values["risk_free_rate"]),
            max_positions=int(values["max_positions"]),
            stop_loss_pct=float(values["stop_loss_pct"]),
            max_drawdown_limit=float(values["max_drawdown_limit"]),
            log_level=str(values["log_level"]),
            verbose=bool(values["verbose"]),
            realtime_poll_interval=int(values["realtime_poll_interval"]),
        )

    def ensure_dirs(self) -> None:
        for d in [self.data_dir, self.cache_dir, self.log_dir,
                   self.journal_dir, self.charts_dir, self.reports_dir]:
            os.makedirs(d, exist_ok=True)


def _resolve_path(raw: str, env: Mapping[str, str]) -> str:
    """Resolve ~ and env vars in paths."""
    expanded = os.path.expanduser(raw)
    # Substitute $VAR and ${VAR}
    import re
    def _sub(m):
        return env.get(m.group(1), m.group(0))
    expanded = re.sub(r'\$\{?(\w+)\}?', _sub, expanded)
    return str(Path(expanded).resolve())


def _load_file(path: str, values: dict[str, Any]) -> None:
    if not os.path.exists(path):
        return
    try:
        if path.endswith(".yaml") or path.endswith(".yml"):
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        if isinstance(data, dict):
            values.update({k: v for k, v in data.items() if k in values})
    except Exception:
        pass  # config file is optional


def _coerce(raw: str, template: Any) -> Any:
    if isinstance(template, bool):
        return raw.lower() in ("1", "true", "yes", "on")
    if isinstance(template, int):
        return int(raw)
    if isinstance(template, float):
        return float(raw)
    return raw


# Global singleton
_config: QuantConfig | None = None


def get_config() -> QuantConfig:
    global _config
    if _config is None:
        _config = QuantConfig.load()
    return _config
