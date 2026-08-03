"""Behavior contract for V2 data roots, storage adapters, and catalog models."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath

from src.lxl_quantaxis.core import Instant
from src.lxl_quantaxis.data.catalog import Dataset, DatasetSnapshot
from src.lxl_quantaxis.data.contracts import StorageKey, StoragePort
from src.lxl_quantaxis.data.storage import DataRoot, LegacySqliteAdapter, LocalStorageAdapter


class DataRootTests(unittest.TestCase):
    def test_environment_priority_and_legacy_dual_read_are_explicit(self) -> None:
        root = DataRoot.from_sources(
            environ={
                "QUANT_DATA_DIR": "/new/quant",
                "TRADING_DATA_DIR": "/legacy/trading",
                "V2_STORAGE_ENABLED": "true",
            },
            home=Path("/home/researcher"),
        )

        self.assertEqual(root.path, Path("/new/quant"))
        self.assertEqual(root.legacy_paths, (Path("/legacy/trading"),))
        self.assertTrue(root.v2_enabled)

    def test_default_is_portable_and_v2_storage_is_rollback_safe(self) -> None:
        root = DataRoot.from_sources(environ={}, home=Path("/home/researcher"))

        self.assertEqual(root.path, Path("/home/researcher/.lxl_quantaxis"))
        self.assertEqual(root.legacy_paths, ())
        self.assertFalse(root.v2_enabled)

    def test_configured_paths_support_windows_and_posix_flavors(self) -> None:
        windows = DataRoot.parse_configured_path(r"C:\Quant\data", flavor="windows")
        posix = DataRoot.parse_configured_path("/var/lib/lxl", flavor="posix")

        self.assertEqual(windows, PureWindowsPath(r"C:\Quant\data"))
        self.assertEqual(posix, PurePosixPath("/var/lib/lxl"))


class LocalStorageAdapterContractTests(unittest.TestCase):
    def test_adapter_satisfies_port_and_creates_directories_only_on_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root_path = Path(temporary_directory) / "not-created-yet"
            adapter = LocalStorageAdapter(DataRoot(path=root_path))

            self.assertIsInstance(adapter, StoragePort)
            self.assertFalse(root_path.exists())
            adapter.write_bytes(StorageKey("cache/CN_600519_daily.csv"), b"date,close\n2026-01-01,1\n")
            self.assertTrue(root_path.exists())
            self.assertEqual(
                adapter.read_bytes(StorageKey("cache/CN_600519_daily.csv")),
                b"date,close\n2026-01-01,1\n",
            )

    def test_dual_read_prefers_primary_and_never_overwrites_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            primary = base / "primary"
            legacy = base / "legacy"
            legacy_file = legacy / "cache" / "CN_600519_daily.csv"
            legacy_file.parent.mkdir(parents=True)
            legacy_file.write_bytes(b"legacy")
            adapter = LocalStorageAdapter(DataRoot(path=primary, legacy_paths=(legacy,)))
            key = StorageKey("cache/CN_600519_daily.csv")

            self.assertEqual(adapter.read_bytes(key), b"legacy")
            adapter.write_bytes(key, b"primary")

            self.assertEqual(adapter.read_bytes(key), b"primary")
            self.assertEqual(legacy_file.read_bytes(), b"legacy")

    def test_storage_key_rejects_path_traversal_and_absolute_paths(self) -> None:
        for unsafe in ("../users.db", "/etc/passwd", r"C:\users.db", "cache/../../users.db"):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                StorageKey(unsafe)

    def test_legacy_sqlite_adapter_finds_old_database_without_creating_primary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            primary = base / "primary"
            legacy = base / "legacy"
            legacy.mkdir()
            old_database = legacy / "users.db"
            old_database.write_bytes(b"SQLite format 3\x00")
            adapter = LegacySqliteAdapter(DataRoot(path=primary, legacy_paths=(legacy,)))

            self.assertEqual(adapter.read_path("users.db"), old_database)
            self.assertFalse(primary.exists())


class DatasetCatalogTests(unittest.TestCase):
    def test_snapshot_hash_is_deterministic_and_verifiable(self) -> None:
        dataset = Dataset(
            dataset_id="cn-equity-daily",
            name="CN equity daily bars",
            storage_key=StorageKey("market/cn/daily.csv"),
            media_type="text/csv",
            schema_version="1.0.0",
        )
        content = b"date,symbol,close\n2026-08-03,600519,1400.00\n"

        snapshot = DatasetSnapshot.from_bytes(
            dataset=dataset,
            content=content,
            captured_at=Instant.parse("2026-08-03T08:00:00Z"),
            row_count=1,
        )

        self.assertEqual(snapshot.content_hash, hashlib.sha256(content).hexdigest())
        self.assertTrue(snapshot.verify(content))
        self.assertFalse(snapshot.verify(content + b"corrupt"))
        self.assertEqual(DatasetSnapshot.from_dict(snapshot.to_dict()), snapshot)


class DataImportSafetyTests(unittest.TestCase):
    def test_import_has_no_disk_write_or_heavy_framework_side_effects(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        script = """
import json
import os
import sys

before_files = sorted(os.listdir('.'))
import src.lxl_quantaxis.data
result = {
    'files_unchanged': before_files == sorted(os.listdir('.')),
    'forbidden_modules': sorted(
        name for name in ('flask', 'sqlalchemy', 'pandas', 'akshare') if name in sys.modules
    ),
}
print(json.dumps(result))
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(project_root)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

        with tempfile.TemporaryDirectory() as temporary_directory:
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=temporary_directory,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

        result = json.loads(completed.stdout)
        self.assertTrue(result["files_unchanged"])
        self.assertEqual(result["forbidden_modules"], [])


if __name__ == "__main__":
    unittest.main()
