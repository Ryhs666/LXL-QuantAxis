"""Configuration for the V3 Investment Memory System.

Resolves the database path using the same environment variables as V1/V2:
  1. QUANT_DATA_DIR    (recommended)
  2. TRADING_DATA_DIR  (legacy)
  3. ~/lxl_quantaxis_data  (default fallback)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _resolve_data_dir() -> Path:
    """Resolve the data directory with the same precedence as V1/V2."""
    quant_dir = os.environ.get("QUANT_DATA_DIR", "").strip()
    trading_dir = os.environ.get("TRADING_DATA_DIR", "").strip()

    if quant_dir:
        return Path(quant_dir).expanduser()
    if trading_dir:
        return Path(trading_dir).expanduser()
    return Path.home() / "lxl_quantaxis_data"


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    """Immutable configuration for the Memory System.

    Attributes:
        data_dir: Root data directory (resolved from env vars).
        db_name: SQLite database filename.
        db_path: Full path to the SQLite database (computed).
    """

    data_dir: Path | None = None
    db_name: str = "lxl_v3.db"

    def __post_init__(self) -> None:
        if self.data_dir is None:
            object.__setattr__(self, "data_dir", _resolve_data_dir())
        else:
            # Coerce str/PathLike to Path for type safety
            object.__setattr__(self, "data_dir", Path(self.data_dir).expanduser())
        if not self.db_name.strip():
            raise ValueError("db_name must be a non-empty file name")
        if Path(self.db_name).name != self.db_name:
            raise ValueError("db_name must be a simple file name, not a path")

    @property
    def db_path(self) -> Path:
        """Full path to the SQLite database file."""
        return self.data_dir / self.db_name  # type: ignore[operator]

    @classmethod
    def with_defaults(cls) -> MemoryConfig:
        """Create config with default values from environment."""
        return cls()
