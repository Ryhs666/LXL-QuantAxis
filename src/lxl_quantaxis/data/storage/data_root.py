"""Cross-platform, side-effect-free data-root configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath


class DataRootConfigurationError(ValueError):
    """Raised when a configured data root is invalid."""


def _parse_bool(value: object, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise DataRootConfigurationError(f"{name} must be true or false")


@dataclass(frozen=True, slots=True)
class DataRoot:
    """Primary storage root plus optional read-only legacy roots.

    Construction never creates directories. Callers perform writes through a
    storage adapter, which creates only the parent directory it needs.
    """

    path: Path
    legacy_paths: tuple[Path, ...] = ()
    v2_enabled: bool = False

    def __post_init__(self) -> None:
        primary = Path(self.path).expanduser()
        legacy: list[Path] = []
        for candidate in self.legacy_paths:
            normalized = Path(candidate).expanduser()
            if normalized != primary and normalized not in legacy:
                legacy.append(normalized)
        object.__setattr__(self, "path", primary)
        object.__setattr__(self, "legacy_paths", tuple(legacy))
        object.__setattr__(self, "v2_enabled", _parse_bool(self.v2_enabled, "v2_enabled"))

    @property
    def read_paths(self) -> tuple[Path, ...]:
        return (self.path, *self.legacy_paths)

    @property
    def cache_path(self) -> Path:
        return self.path / "cache"

    def database_path(self, name: str) -> Path:
        if not name or Path(name).name != name:
            raise ValueError("database name must be a file name")
        return self.path / name

    @classmethod
    def from_sources(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        home: Path | None = None,
    ) -> DataRoot:
        source = os.environ if environ is None else environ
        home_path = Path.home() if home is None else Path(home)
        quant_path = source.get("QUANT_DATA_DIR", "").strip()
        trading_path = source.get("TRADING_DATA_DIR", "").strip()

        primary = Path(quant_path or trading_path) if quant_path or trading_path else home_path / ".lxl_quantaxis"
        legacy = (Path(trading_path),) if quant_path and trading_path and Path(trading_path) != primary else ()
        enabled = _parse_bool(source.get("V2_STORAGE_ENABLED", "false"), "V2_STORAGE_ENABLED")
        return cls(path=primary, legacy_paths=legacy, v2_enabled=enabled)

    @staticmethod
    def parse_configured_path(value: str, *, flavor: str = "native") -> PurePath:
        """Parse configuration without depending on the host operating system."""

        if not isinstance(value, str) or not value.strip():
            raise DataRootConfigurationError("configured path must be a non-empty string")
        normalized = value.strip()
        if flavor == "windows":
            return PureWindowsPath(normalized)
        if flavor == "posix":
            return PurePosixPath(normalized)
        if flavor == "native":
            return Path(normalized)
        raise DataRootConfigurationError(f"unsupported path flavor: {flavor!r}")
