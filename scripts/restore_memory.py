"""Restore a checksum-verified Alpha Memory SQLite backup."""

import argparse
from pathlib import Path

from src.lxl_quantaxis.ops import BackupArtifact, restore_backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup")
    parser.add_argument("sha256")
    parser.add_argument("destination")
    arguments = parser.parse_args()
    restore_backup(BackupArtifact(Path(arguments.backup).resolve(), arguments.sha256), arguments.destination)
    print(f"restored={Path(arguments.destination).resolve()}")


if __name__ == "__main__":
    main()
