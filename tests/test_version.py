"""Tests for the shared product version."""

import re
import unittest

from src.lxl_quantaxis import __version__


class VersionTests(unittest.TestCase):
    def test_version_uses_semantic_versioning(self) -> None:
        self.assertRegex(__version__, re.compile(r"^\d+\.\d+\.\d+$"))


if __name__ == "__main__":
    unittest.main()
