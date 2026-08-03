"""Tests for resolve_data_root() — cross-platform data directory."""

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import after path setup
from src.backtest.data_feed import DataCache, resolve_data_root


class TestDataPath(unittest.TestCase):
    """Test data directory resolution with environment variable priority."""

    def setUp(self):
        self._saved = {}
        for k in ("QUANT_DATA_DIR", "TRADING_DATA_DIR"):
            self._saved[k] = os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v

    def test_default_to_home_dir(self):
        """When no env vars set, uses ~/.lxl_quantaxis."""
        root = resolve_data_root()
        expected = Path.home() / ".lxl_quantaxis"
        self.assertEqual(root, expected)

    def test_quant_data_dir_priority(self):
        """QUANT_DATA_DIR takes top priority."""
        os.environ["QUANT_DATA_DIR"] = "/custom/quant"
        root = resolve_data_root()
        self.assertEqual(root, Path("/custom/quant"))

    def test_trading_data_dir_fallback(self):
        """TRADING_DATA_DIR used when QUANT_DATA_DIR not set."""
        os.environ["TRADING_DATA_DIR"] = "/legacy/trading"
        root = resolve_data_root()
        self.assertEqual(root, Path("/legacy/trading"))

    def test_quant_wins_over_trading(self):
        """QUANT_DATA_DIR takes priority when both are set."""
        os.environ["QUANT_DATA_DIR"] = "/custom/quant"
        os.environ["TRADING_DATA_DIR"] = "/legacy/trading"
        root = resolve_data_root()
        self.assertEqual(root, Path("/custom/quant"))

    def test_data_cache_reads_legacy_root_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            primary = base / "primary"
            legacy = base / "legacy"
            legacy_cache = legacy / "cache"
            legacy_cache.mkdir(parents=True)
            legacy_file = legacy_cache / "A股_600519_daily.csv"
            legacy_content = (f"date,open,high,low,close,volume\n{date.today().isoformat()},1,2,0.5,1.5,100\n").encode()
            legacy_file.write_bytes(legacy_content)

            with patch.dict(
                os.environ,
                {"QUANT_DATA_DIR": str(primary), "TRADING_DATA_DIR": str(legacy)},
                clear=False,
            ):
                frame = DataCache().load("600519", "A股")

            self.assertIsNotNone(frame)
            self.assertFalse(primary.exists())
            self.assertEqual(legacy_file.read_bytes(), legacy_content)

    def test_importing_data_feed_does_not_create_configured_directories(self):
        project_root = Path(__file__).resolve().parents[1]
        script = "import src.backtest.data_feed"
        with tempfile.TemporaryDirectory() as temporary_directory:
            configured_root = Path(temporary_directory) / "configured"
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(project_root)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["QUANT_DATA_DIR"] = str(configured_root)
            environment.pop("TRADING_DATA_DIR", None)

            subprocess.run(
                [sys.executable, "-c", script],
                cwd=temporary_directory,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertFalse(configured_root.exists())

    def test_importing_database_does_not_create_configured_directories(self):
        project_root = Path(__file__).resolve().parents[1]
        script = "import src.database"
        with tempfile.TemporaryDirectory() as temporary_directory:
            configured_root = Path(temporary_directory) / "configured"
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(project_root)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["QUANT_DATA_DIR"] = str(configured_root)
            environment.pop("QUANT_DATABASE_URL", None)
            environment.pop("TRADING_DATA_DIR", None)

            subprocess.run(
                [sys.executable, "-c", script],
                cwd=temporary_directory,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertFalse(configured_root.exists())


if __name__ == "__main__":
    unittest.main()
