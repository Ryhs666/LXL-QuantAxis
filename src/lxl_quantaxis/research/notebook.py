"""High-level research notebook API — convenience wrappers."""

from __future__ import annotations

from src.lxl_quantaxis.research.models import ResearchNote
from src.lxl_quantaxis.research.repository import get_repository


def create_note(
    title: str,
    content: str = "",
    symbol: str = "",
    investment_thesis: str = "",
    bull_case: str = "",
    bear_case: str = "",
    risk: str = "",
    tags: str = "",
) -> int:
    """Create a research note. Returns the new note ID."""
    note = ResearchNote(
        symbol=symbol,
        title=title,
        content=content,
        investment_thesis=investment_thesis,
        bull_case=bull_case,
        bear_case=bear_case,
        risk=risk,
        tags=tags,
    )
    return get_repository().create(note)


def get_note(note_id: int) -> ResearchNote | None:
    return get_repository().get(note_id)


def list_notes(limit: int = 50, offset: int = 0) -> list[ResearchNote]:
    return get_repository().list_all(limit=limit, offset=offset)


def search_notes(keyword: str, limit: int = 50) -> list[ResearchNote]:
    return get_repository().search(keyword, limit=limit)


def notes_by_symbol(symbol: str, limit: int = 50) -> list[ResearchNote]:
    return get_repository().list_by_symbol(symbol, limit=limit)


def delete_note(note_id: int) -> bool:
    return get_repository().delete(note_id)


def note_count() -> int:
    return get_repository().count()
