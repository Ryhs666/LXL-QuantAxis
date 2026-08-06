-- ============================================================
-- lxl_v3.db: Investment Memory System Schema
-- Phase 1 — memory_entries table + FTS5 full-text search
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------
-- 1. memory_entries — Unified memory table
--    One table for all four entry types:
--    note | thesis | decision | reflection
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Core classification
    type        TEXT    NOT NULL CHECK (type IN (
                   'note', 'thesis', 'decision', 'reflection'
                )),
    ticker      TEXT    NOT NULL DEFAULT '[]',   -- JSON array, e.g. '["000858","600519"]'
    title       TEXT    NOT NULL,
    content     TEXT    NOT NULL,                -- Markdown body (clean, for display)

    -- FTS-optimized search text (application-level CJK tokenization)
    search_text TEXT    NOT NULL DEFAULT '',

    -- Structured sub-objects (JSON blobs)
    thesis      TEXT,                            -- NULL for non-thesis types
    decision    TEXT,                            -- NULL for non-decision types

    -- Top-level fields for easy querying
    confidence  REAL,                            -- 0.0 - 1.0, thesis conviction
    status      TEXT    DEFAULT 'pending',       -- pending | correct | wrong | expired | partial
    outcome     TEXT,                            -- {detail, return_pct, reviewed_at}

    -- Associations
    tags        TEXT    NOT NULL DEFAULT '[]',   -- JSON array, e.g. '["消费","白酒"]'

    -- Timestamps
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT
);

-- -----------------------------------------------------------
-- 2. Indexes
-- -----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_memory_type    ON memory_entries(type);
CREATE INDEX IF NOT EXISTS idx_memory_status  ON memory_entries(status);
CREATE INDEX IF NOT EXISTS idx_memory_ticker  ON memory_entries(ticker);
CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_entries(created_at);

-- -----------------------------------------------------------
-- 3. memory_entries_fts — FTS5 full-text search
--    Indexes search_text (CJK-tokenized) + tags + ticker.
--    unicode61 tokenizer handles English + space-separated CJK.
-- -----------------------------------------------------------
CREATE VIRTUAL TABLE IF NOT EXISTS memory_entries_fts USING fts5(
    search_text,
    tags,
    ticker,
    content='memory_entries',
    content_rowid='id',
    tokenize='unicode61'
);

-- -----------------------------------------------------------
-- 4. Triggers — keep FTS index in sync with memory_entries
-- -----------------------------------------------------------

-- INSERT
CREATE TRIGGER IF NOT EXISTS memory_fts_ai AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_entries_fts(rowid, search_text, tags, ticker)
    VALUES (new.id, new.search_text, new.tags, new.ticker);
END;

-- DELETE
CREATE TRIGGER IF NOT EXISTS memory_fts_ad AFTER DELETE ON memory_entries BEGIN
    INSERT INTO memory_entries_fts(memory_entries_fts, rowid, search_text, tags, ticker)
    VALUES ('delete', old.id, old.search_text, old.tags, old.ticker);
END;

-- UPDATE
CREATE TRIGGER IF NOT EXISTS memory_fts_au AFTER UPDATE ON memory_entries BEGIN
    INSERT INTO memory_entries_fts(memory_entries_fts, rowid, search_text, tags, ticker)
    VALUES ('delete', old.id, old.search_text, old.tags, old.ticker);
    INSERT INTO memory_entries_fts(rowid, search_text, tags, ticker)
    VALUES (new.id, new.search_text, new.tags, new.ticker);
END;
