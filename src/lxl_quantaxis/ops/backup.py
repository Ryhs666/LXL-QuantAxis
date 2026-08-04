"""Verified SQLite backup and restore operations."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BackupArtifact:
    path: Path
    sha256: str


def create_backup(source: str | Path, destination: str | Path) -> BackupArtifact:
    source_path, destination_path = _paths(source, destination)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        closing(sqlite3.connect(source_path)) as source_connection,
        closing(sqlite3.connect(destination_path)) as destination_connection,
    ):
        source_connection.backup(destination_connection)
    return BackupArtifact(destination_path, _checksum(destination_path))


def restore_backup(artifact: BackupArtifact, destination: str | Path) -> None:
    destination_path = Path(destination).resolve()
    if not artifact.path.is_file() or _checksum(artifact.path) != artifact.sha256:
        raise ValueError("backup checksum verification failed")
    if artifact.path.resolve() == destination_path:
        raise ValueError("backup and restore destination must differ")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        closing(sqlite3.connect(artifact.path)) as source_connection,
        closing(sqlite3.connect(destination_path)) as destination_connection,
    ):
        source_connection.backup(destination_connection)


def _paths(source: str | Path, destination: str | Path) -> tuple[Path, Path]:
    source_path, destination_path = Path(source).resolve(), Path(destination).resolve()
    if source_path == destination_path:
        raise ValueError("backup source and destination must differ")
    return source_path, destination_path


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
