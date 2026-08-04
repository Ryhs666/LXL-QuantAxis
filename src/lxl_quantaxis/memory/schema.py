"""Alembic-compatible expand-only migration operations for Alpha Memory."""

import sqlite3

REVISION = "001_alpha_memory"
DOWN_REVISION = None

TABLES = (
    "memory_links",
    "memory_research_runs",
    "memory_dataset_snapshots",
    "memory_strategy_versions",
    "memory_strategies",
    "memory_theses",
    "memory_extractions",
    "memory_notes",
)


def upgrade(connection: sqlite3.Connection) -> None:
    statements = (
        "CREATE TABLE IF NOT EXISTS memory_notes (note_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, body TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS memory_extractions (extraction_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, note_id TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS memory_theses (thesis_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, note_id TEXT NOT NULL, statement TEXT NOT NULL, assumptions_json TEXT NOT NULL, risks_json TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS memory_strategies (strategy_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL, legacy_key TEXT UNIQUE)",
        "CREATE TABLE IF NOT EXISTS memory_strategy_versions (strategy_id TEXT NOT NULL, organization_id TEXT NOT NULL, version INTEGER NOT NULL, specification_json TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL, PRIMARY KEY(strategy_id, version), FOREIGN KEY(strategy_id) REFERENCES memory_strategies(strategy_id))",
        "CREATE TABLE IF NOT EXISTS memory_dataset_snapshots (snapshot_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, content_hash TEXT NOT NULL, data_as_of TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS memory_research_runs (run_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, strategy_id TEXT NOT NULL, strategy_version INTEGER NOT NULL, snapshot_id TEXT NOT NULL, result_json TEXT NOT NULL, started_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS memory_links (link_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, source_type TEXT NOT NULL, source_id TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT NOT NULL)",
    )
    for statement in statements:
        connection.execute(statement)
    for table in TABLES:
        connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_organization ON {table}(organization_id)")


def downgrade(connection: sqlite3.Connection) -> None:
    for table in TABLES:
        connection.execute(f"DROP TABLE IF EXISTS {table}")
