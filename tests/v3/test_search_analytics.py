"""Tests for MemorySearch, MemoryAnalytics, and related functions."""
from __future__ import annotations

import shutil
import tempfile

import pytest

from src.v3.memory import (
    MemoryAnalytics,
    MemoryConfig,
    MemoryDatabase,
    MemoryEntry,
    MemoryRepository,
    MemorySearch,
    SearchFilters,
    find_similar,
)


def _setup():
    tmpdir = tempfile.mkdtemp()
    config = MemoryConfig(data_dir=tmpdir, db_name="test.db")
    repo = MemoryRepository(config)
    repo.initialize()

    entries = [
        MemoryEntry(type="thesis", ticker=["000858"], title="Consumer recovery",
                    content="Wuliangye recovery thesis.", confidence=0.8,
                    status="correct", tags=["consumer", "baijiu"]),
        MemoryEntry(type="thesis", ticker=["688981"], title="Chip cycle bottom",
                    content="SMIC thesis. Semicon cycle.", confidence=0.75,
                    status="wrong", tags=["tech", "semiconductor"]),
        MemoryEntry(type="thesis", ticker=["600519"], title="Moutai stable growth",
                    content="Moutai defensive play.", confidence=0.4,
                    status="correct", tags=["consumer", "baijiu"]),
        MemoryEntry(type="thesis", ticker=["000858"], title="Baijiu sector rotation",
                    content="Rotation into baijiu.", confidence=0.6,
                    status="pending", tags=["consumer", "rotation"]),
        MemoryEntry(type="decision", ticker=["000858"], title="Buy Wuliangye",
                    content="Entry at 145.", confidence=0.7, status="good",
                    tags=["consumer"], decision={"type": "buy", "price": 145.0}),
        MemoryEntry(type="decision", ticker=["688981"], title="Buy SMIC",
                    content="Entry too early.", status="bad",
                    tags=["tech"], decision={"type": "buy", "price": 65.0}),
        MemoryEntry(type="note", title="Q2 earnings review",
                    content="Consumer sector review.", tags=["consumer", "earnings"]),
        MemoryEntry(type="reflection", title="Lesson: patience",
                    content="Wait for confirmation signals.", tags=["lesson", "discipline"]),
    ]
    ids = repo.save_many(entries)
    return tmpdir, config, repo, ids


def _teardown(tmpdir):
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestMemorySearch:
    def test_keyword_search(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.query(SearchFilters(keyword="baijiu"))
            assert len(r) >= 1
        finally:
            _teardown(tmpdir)

    def test_type_filter(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.query(SearchFilters(entry_type="thesis"))
            assert len(r) == 4
        finally:
            _teardown(tmpdir)

    def test_ticker_filter(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.query(SearchFilters(ticker="000858"))
            assert len(r) >= 2
        finally:
            _teardown(tmpdir)

    def test_date_range(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.query(SearchFilters(date_from="2020-01-01", date_to="2030-12-31"))
            assert len(r) == 8
        finally:
            _teardown(tmpdir)

    def test_confidence_range(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.query(SearchFilters(confidence_min=0.7))
            assert len(r) >= 2
        finally:
            _teardown(tmpdir)

    def test_status_filter(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.query(SearchFilters(status="pending"))
            assert len(r) == 1
        finally:
            _teardown(tmpdir)

    def test_combined_filters(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.query(SearchFilters(
                entry_type="thesis", ticker="000858", status="pending"
            ))
            assert len(r) == 1
            assert r[0].type == "thesis"
            assert "000858" in r[0].ticker
        finally:
            _teardown(tmpdir)

    def test_pending_reviews_shortcut(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.search_pending_reviews()
            assert len(r) == 1
            assert r[0].status == "pending"
        finally:
            _teardown(tmpdir)

    def test_high_confidence_shortcut(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.search_high_confidence(min_confidence=0.7)
            assert len(r) >= 2
            assert all(e.confidence is not None and e.confidence >= 0.7 for e in r)
        finally:
            _teardown(tmpdir)

    def test_search_count(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            c = searcher.count(SearchFilters(entry_type="thesis"))
            assert c == 4
        finally:
            _teardown(tmpdir)

    def test_related_by_ticker(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.find_related(ticker="000858")
            assert len(r) >= 1
            # Should not include non-000858 entries without tag overlap
        finally:
            _teardown(tmpdir)

    def test_related_by_entry_id(self):
        tmpdir, _config, repo, ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.find_related(entry_id=ids[0])
            assert len(r) >= 1
            assert all(e.id != ids[0] for e in r)
        finally:
            _teardown(tmpdir)

    def test_find_similar(self):
        tmpdir, _config, repo, ids = _setup()
        try:
            r = find_similar(repo._db, ids[0])
            assert len(r) >= 1
        finally:
            _teardown(tmpdir)

    def test_no_results(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            searcher = MemorySearch(repo._db)
            r = searcher.query(SearchFilters(keyword="BITCOIN_NOT_FOUND_XYZ"))
            assert len(r) == 0
        finally:
            _teardown(tmpdir)


class TestMemoryAnalytics:
    def test_stats_totals(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            stats = analytics.get_stats()
            assert stats.total_entries == 8
            assert stats.theses == 4
            assert stats.decisions == 2
            assert stats.notes == 1
            assert stats.reflections == 1
        finally:
            _teardown(tmpdir)

    def test_thesis_hit_rate(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            stats = analytics.get_stats()
            assert stats.thesis_correct == 2
            assert stats.thesis_wrong == 1
            assert stats.thesis_pending == 1
            assert stats.thesis_hit_rate == pytest.approx(2 / 3, abs=0.001)
            assert stats.active_theses == 1
        finally:
            _teardown(tmpdir)

    def test_decision_win_rate(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            stats = analytics.get_stats()
            assert stats.decision_good == 1
            assert stats.decision_bad == 1
            assert stats.decision_win_rate == 0.5
        finally:
            _teardown(tmpdir)

    def test_avg_confidence(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            stats = analytics.get_stats()
            expected = round((0.8 + 0.75 + 0.4 + 0.6) / 4, 2)
            assert round(stats.avg_confidence, 2) == expected
        finally:
            _teardown(tmpdir)

    def test_top_tags(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            stats = analytics.get_stats()
            assert len(stats.top_tags) >= 1
            tags_dict = dict(stats.top_tags)
            assert tags_dict.get("consumer", 0) >= 3
        finally:
            _teardown(tmpdir)

    def test_calibration_buckets(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            cal = analytics.get_calibration()
            assert len(cal.buckets) == 3
            assert cal.overall_hit_rate == pytest.approx(2 / 3, abs=0.001)
            high = cal.buckets[2]
            assert high.label.startswith("High")
            assert high.total == 2  # conf 0.8 + 0.75
        finally:
            _teardown(tmpdir)

    def test_calibration_insight(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            cal = analytics.get_calibration()
            assert len(cal.insight) > 10
            # High bucket: conf 0.8(correct) + 0.75(wrong) = 50%
            # Low bucket: conf 0.4(correct) = 100%
            # So calibration is inverted — not calibrated
            assert not cal.is_calibrated
        finally:
            _teardown(tmpdir)

    def test_tag_performance(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            tp = analytics.get_tag_performance()
            assert len(tp) >= 1
            consumer = [t for t in tp if t.tag == "consumer"]
            assert len(consumer) == 1
            assert consumer[0].total >= 1
        finally:
            _teardown(tmpdir)

    def test_activity_timeline(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            tl = analytics.get_activity_timeline(days=365)
            assert len(tl) >= 1
            assert "day" in tl[0]
            assert "total" in tl[0]
        finally:
            _teardown(tmpdir)

    def test_pending_reviews(self):
        tmpdir, _config, repo, _ids = _setup()
        try:
            analytics = MemoryAnalytics(repo._db)
            pr = analytics.get_pending_reviews(min_days_since_creation=0)
            assert len(pr) == 1
            assert pr[0]["title"] == "Baijiu sector rotation"
        finally:
            _teardown(tmpdir)

    def test_empty_database(self):
        tmpdir = tempfile.mkdtemp()
        try:
            config = MemoryConfig(data_dir=tmpdir, db_name="empty.db")
            db = MemoryDatabase(config)
            db.initialize()
            analytics = MemoryAnalytics(db)
            stats = analytics.get_stats()
            assert stats.total_entries == 0
            assert stats.thesis_hit_rate == 0.0
            cal = analytics.get_calibration()
            assert cal.overall_hit_rate == 0.0
            assert "Not enough data" in cal.insight
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
