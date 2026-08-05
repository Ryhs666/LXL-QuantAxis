"""SQLite-backed repository for ResearchNote persistence."""

from __future__ import annotations

import os
import sqlite3


from src.lxl_quantaxis.core.config.loader import get_config
from src.lxl_quantaxis.research.models import ResearchNote


class ResearchRepository:
    """CRUD operations for research notes."""

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            cfg = get_config()
            db_path = os.path.join(cfg.data_dir, "research_notes.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS research_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    symbol TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL DEFAULT '',
                    investment_thesis TEXT NOT NULL DEFAULT '',
                    bull_case TEXT NOT NULL DEFAULT '',
                    bear_case TEXT NOT NULL DEFAULT '',
                    risk TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT ''
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_rn_date ON research_notes(date)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_rn_symbol ON research_notes(symbol)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_rn_tags ON research_notes(tags)")
            c.commit()

    def create(self, note: ResearchNote) -> int:
        with self._conn() as c:
            cur = c.execute(
                """INSERT INTO research_notes
                   (date, symbol, title, content, investment_thesis,
                    bull_case, bear_case, risk, tags, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (note.date, note.symbol, note.title, note.content,
                 note.investment_thesis, note.bull_case, note.bear_case,
                 note.risk, note.tags, note.created_at),
            )
            c.commit()
            return cur.lastrowid

    def get(self, note_id: int) -> ResearchNote | None:
        with self._conn() as c:
            cur = c.execute(
                "SELECT * FROM research_notes WHERE id = ?", (note_id,)
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_note(row)

    def list_all(self, limit: int = 50, offset: int = 0) -> list[ResearchNote]:
        with self._conn() as c:
            cur = c.execute(
                "SELECT * FROM research_notes ORDER BY date DESC, id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return [self._row_to_note(r) for r in cur.fetchall()]

    def search(self, keyword: str, limit: int = 50) -> list[ResearchNote]:
        pattern = f"%{keyword}%"
        with self._conn() as c:
            cur = c.execute(
                """SELECT * FROM research_notes
                   WHERE title LIKE ? OR content LIKE ? OR symbol LIKE ?
                      OR tags LIKE ? OR investment_thesis LIKE ?
                   ORDER BY date DESC LIMIT ?""",
                (pattern, pattern, pattern, pattern, pattern, limit),
            )
            return [self._row_to_note(r) for r in cur.fetchall()]

    def list_by_symbol(self, symbol: str, limit: int = 50) -> list[ResearchNote]:
        with self._conn() as c:
            cur = c.execute(
                "SELECT * FROM research_notes WHERE symbol = ? ORDER BY date DESC LIMIT ?",
                (symbol, limit),
            )
            return [self._row_to_note(r) for r in cur.fetchall()]

    def delete(self, note_id: int) -> bool:
        with self._conn() as c:
            c.execute("DELETE FROM research_notes WHERE id = ?", (note_id,))
            c.commit()
            return c.total_changes > 0

    def count(self) -> int:
        with self._conn() as c:
            cur = c.execute("SELECT COUNT(*) FROM research_notes")
            return cur.fetchone()[0]

    @staticmethod
    def _row_to_note(row: tuple) -> ResearchNote:
        cols = ["id", "date", "symbol", "title", "content",
                "investment_thesis", "bull_case", "bear_case",
                "risk", "tags", "created_at"]
        d = dict(zip(cols, row))
        return ResearchNote.from_dict(d)


# Global singleton
_repo: ResearchRepository | None = None


def get_repository() -> ResearchRepository:
    global _repo
    if _repo is None:
        _repo = ResearchRepository()
    return _repo
