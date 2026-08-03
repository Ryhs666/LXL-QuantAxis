"""Import-safety contract for the framework-independent V2 core."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CoreImportSafetyTests(unittest.TestCase):
    def test_import_has_no_framework_thread_or_working_directory_side_effects(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        script = """
import json
import os
import sys
import threading

before_files = sorted(os.listdir('.'))
before_threads = len(threading.enumerate())
import src.lxl_quantaxis.core
result = {
    'files_unchanged': before_files == sorted(os.listdir('.')),
    'threads_unchanged': before_threads == len(threading.enumerate()),
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
        self.assertTrue(result["threads_unchanged"])
        self.assertEqual(result["forbidden_modules"], [])


if __name__ == "__main__":
    unittest.main()
