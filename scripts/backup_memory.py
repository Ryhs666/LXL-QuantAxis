"""Create a verified Alpha Memory SQLite backup."""

import argparse

from src.lxl_quantaxis.ops import create_backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    arguments = parser.parse_args()
    artifact = create_backup(arguments.source, arguments.destination)
    print(f"backup={artifact.path} sha256={artifact.sha256}")


if __name__ == "__main__":
    main()
