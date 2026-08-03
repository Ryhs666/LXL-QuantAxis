"""Adapters exposing legacy CSV and SQLite layouts through V2 boundaries."""

from __future__ import annotations

from pathlib import Path

from src.lxl_quantaxis.data.contracts import StorageKey
from src.lxl_quantaxis.data.storage.data_root import DataRoot
from src.lxl_quantaxis.data.storage.local import LocalStorageAdapter


class LegacyCsvAdapter:
    """Map the existing ``cache/<market>_<symbol>_<period>.csv`` layout."""

    def __init__(self, root: DataRoot) -> None:
        self.storage = LocalStorageAdapter(root)

    @staticmethod
    def key(symbol: str, market: str, period: str = "daily") -> StorageKey:
        for value, name in ((symbol, "symbol"), (market, "market"), (period, "period")):
            if not value or any(separator in value for separator in ("/", "\\")):
                raise ValueError(f"{name} must be a non-empty path-safe value")
        return StorageKey(f"cache/{market}_{symbol}_{period}.csv")

    def read_bytes(self, symbol: str, market: str, period: str = "daily") -> bytes:
        return self.storage.read_bytes(self.key(symbol, market, period))

    def write_bytes(self, content: bytes, symbol: str, market: str, period: str = "daily") -> None:
        self.storage.write_bytes(self.key(symbol, market, period), content)


class LegacySqliteAdapter:
    """Locate existing SQLite files and lazily prepare primary write paths."""

    def __init__(self, root: DataRoot) -> None:
        self.root = root

    @staticmethod
    def _validate_name(name: str) -> str:
        if not name or Path(name).name != name or not name.lower().endswith((".db", ".sqlite", ".sqlite3")):
            raise ValueError("SQLite database name must be a safe database file name")
        return name

    def read_path(self, name: str) -> Path:
        safe_name = self._validate_name(name)
        for root in self.root.read_paths:
            candidate = root / safe_name
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(safe_name)

    def writable_path(self, name: str) -> Path:
        safe_name = self._validate_name(name)
        target = self.root.path / safe_name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def preferred_path(self, name: str) -> Path:
        """Use existing legacy data when present, otherwise return the primary path."""

        try:
            return self.read_path(name)
        except FileNotFoundError:
            return self.root.path / self._validate_name(name)
