"""Local filesystem implementation of the V2 storage port."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.lxl_quantaxis.data.contracts import StorageKey, StorageMetadata
from src.lxl_quantaxis.data.storage.data_root import DataRoot


class LocalStorageAdapter:
    """Binary local storage with primary-write and legacy dual-read behavior."""

    def __init__(self, root: DataRoot | Path) -> None:
        self.root = root if isinstance(root, DataRoot) else DataRoot(path=Path(root))

    @staticmethod
    def _path(base: Path, key: StorageKey) -> Path:
        resolved_base = base.resolve(strict=False)
        candidate = base.joinpath(*key.parts)
        if not candidate.resolve(strict=False).is_relative_to(resolved_base):
            raise ValueError("storage key resolves outside its configured root")
        return candidate

    def path_for_read(self, key: StorageKey) -> Path:
        for base in self.root.read_paths:
            candidate = self._path(base, key)
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(str(key))

    def path_for_write(self, key: StorageKey) -> Path:
        return self._path(self.root.path, key)

    def exists(self, key: StorageKey) -> bool:
        return any(self._path(base, key).is_file() for base in self.root.read_paths)

    def read_bytes(self, key: StorageKey) -> bytes:
        return self.path_for_read(key).read_bytes()

    def write_bytes(self, key: StorageKey, content: bytes) -> None:
        if not isinstance(content, bytes):
            raise TypeError("storage content must be bytes")
        target = self.path_for_write(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def metadata(self, key: StorageKey) -> StorageMetadata:
        details = self.path_for_read(key).stat()
        return StorageMetadata(
            key=key,
            size=details.st_size,
            modified_at=datetime.fromtimestamp(details.st_mtime, tz=UTC),
        )

    def iter_keys(self, prefix: StorageKey | None = None) -> tuple[StorageKey, ...]:
        prefix_parts = prefix.parts if prefix is not None else ()
        found: set[StorageKey] = set()
        for base in self.root.read_paths:
            start = base.joinpath(*prefix_parts)
            if start.is_file() and prefix is not None:
                found.add(prefix)
                continue
            if not start.is_dir():
                continue
            for path in start.rglob("*"):
                if path.is_file():
                    found.add(StorageKey(path.relative_to(base).as_posix()))
        return tuple(sorted(found))

    def delete(self, key: StorageKey) -> bool:
        """Delete only from the primary root; legacy data is never removed."""

        target = self.path_for_write(key)
        if not target.is_file():
            return False
        target.unlink()
        return True
