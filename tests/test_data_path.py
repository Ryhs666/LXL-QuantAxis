"""Tests for resolve_data_root() — cross-platform data directory."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import after path setup
from src.backtest.data_feed import resolve_data_root


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


if __name__ == "__main__":
    unittest.main()
