"""Tests for research notebook foundation."""

import os
import pytest
from src.lxl_quantaxis.research.models import ResearchNote
from src.lxl_quantaxis.research.repository import ResearchRepository
from src.lxl_quantaxis.research.notebook import (
    create_note, get_note, list_notes, search_notes,
    notes_by_symbol, delete_note, note_count,
)
from src.lxl_quantaxis.research.thesis import InvestmentThesis


@pytest.fixture
def repo(tmp_path):
    db = os.path.join(str(tmp_path), "test_notes.db")
    r = ResearchRepository(db_path=db)
    yield r
    # pytest will clean up tmp_path automatically


class TestResearchNote:
    def test_create_with_defaults(self):
        note = ResearchNote(title="test", symbol="600519")
        assert note.title == "test"
        assert note.symbol == "600519"
        assert note.date  # auto-filled

    def test_immutable(self):
        note = ResearchNote(title="test")
        with pytest.raises(Exception):
            note.title = "changed"  # type: ignore

    def test_to_dict_and_back(self):
        note = ResearchNote(
            title="茅台分析", symbol="600519",
            investment_thesis="消费升级长期利好",
            bull_case="涨价+销量增长", bear_case="政策打压",
            risk="政策风险", tags="白酒,消费",
        )
        d = note.to_dict()
        note2 = ResearchNote.from_dict(d)
        assert note2.title == note.title
        assert note2.investment_thesis == note.investment_thesis


class TestRepository:
    def test_create_and_get(self, repo):
        note = ResearchNote(title="测试", symbol="000001")
        nid = repo.create(note)
        assert nid > 0
        found = repo.get(nid)
        assert found is not None
        assert found.title == "测试"

    def test_list_all(self, repo):
        for i in range(5):
            repo.create(ResearchNote(title=f"Note {i}"))
        notes = repo.list_all()
        assert len(notes) == 5

    def test_search(self, repo):
        repo.create(ResearchNote(title="茅台分析", content="白酒龙头"))
        repo.create(ResearchNote(title="银行分析", content="工商银行"))
        results = repo.search("茅台")
        assert len(results) == 1
        assert results[0].title == "茅台分析"

    def test_list_by_symbol(self, repo):
        repo.create(ResearchNote(title="A", symbol="600519"))
        repo.create(ResearchNote(title="B", symbol="000001"))
        results = repo.list_by_symbol("600519")
        assert len(results) == 1
        assert results[0].title == "A"

    def test_delete(self, repo):
        nid = repo.create(ResearchNote(title="to delete"))
        assert repo.delete(nid)
        assert repo.get(nid) is None

    def test_count(self, repo):
        assert repo.count() == 0
        repo.create(ResearchNote(title="x"))
        assert repo.count() == 1


class TestNotebookAPI:
    def test_create_and_get_via_global(self):
        note_id = create_note(title="API test", symbol="TEST")
        assert note_id > 0
        note = get_note(note_id)
        assert note is not None
        assert note.title == "API test"
        delete_note(note_id)

    def test_search_via_global(self):
        nid = create_note(title="unique_search_term_xyz")
        results = search_notes("unique_search_term_xyz")
        assert len(results) >= 1
        delete_note(nid)

    def test_notes_by_symbol(self):
        nid = create_note(title="sym test", symbol="UNIQUE_SYM")
        results = notes_by_symbol("UNIQUE_SYM")
        assert len(results) >= 1
        delete_note(nid)


class TestThesis:
    def test_save_thesis(self):
        thesis = InvestmentThesis(
            symbol="600519", title="茅台看多",
            core_argument="消费升级", conviction="high",
        )
        nid = thesis.save()
        assert nid > 0
        note = get_note(nid)
        assert note.investment_thesis == "消费升级"
        assert "conviction-high" in note.tags
        delete_note(nid)
