"""Compatibility tests between legacy configuration and the V2 core."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class LegacyConfigAdapterTests(unittest.TestCase):
    def test_adapter_keeps_legacy_default_and_honors_v2_overrides(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        script = """
import json
from src.config import get_v2_core_settings

settings = get_v2_core_settings(overrides={'default_currency': 'USD'})
print(json.dumps(settings.to_dict(), sort_keys=True))
"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            environment = os.environ.copy()
            environment.update(
                {
                    "PYTHONPATH": str(project_root),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "QUANT_CONFIG": str(root / "missing-config.yaml"),
                    "QUANT_DATA_DIR": str(root / "data"),
                    "QUANT_CACHE_DIR": str(root / "cache"),
                    "QUANT_LOG_DIR": str(root / "logs"),
                    "V2_CORE_ENABLED": "true",
                    "LXL_ENV": "test",
                    "LXL_TIMEZONE": "UTC",
                }
            )
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=temporary_directory,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

        settings = json.loads(completed.stdout)
        self.assertEqual(
            settings,
            {
                "default_currency": "USD",
                "enabled": True,
                "environment": "test",
                "timezone": "UTC",
            },
        )


if __name__ == "__main__":
    unittest.main()
