"""Packaged JSON schema for StrategySpec manifests."""

from importlib.resources import files


def schema_text() -> str:
    return files(__package__).joinpath("schema.json").read_text(encoding="utf-8")


__all__ = ["schema_text"]
