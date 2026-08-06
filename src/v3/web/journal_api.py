"""Journal API routes — CRUD, search, and analytics.

Returns HTML partials for HTMX requests (HX-Request header present)
and JSON for programmatic access. All endpoints require JWT auth.
"""

from __future__ import annotations

import contextlib
from datetime import datetime

from flask import jsonify, render_template, request

from src.auth import token_required
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
from src.v3.web import v3_bp

# ── Lazy-init ────────────────────────────────────────────────

_repo: MemoryRepository | None = None


def _get_repo() -> MemoryRepository:
    global _repo
    if _repo is None:
        config = MemoryConfig.with_defaults()
        db = MemoryDatabase(config)
        db.initialize()
        _repo = MemoryRepository(config)
    return _repo


def _is_htmx() -> bool:
    """Check if this request came from HTMX."""
    return request.headers.get("HX-Request", "").lower() == "true"


# ── Entry serialization ─────────────────────────────────────

def _entry_to_dict(entry: MemoryEntry) -> dict:
    return {
        "id": entry.id, "type": entry.type,
        "ticker": entry.ticker, "title": entry.title,
        "content": entry.content, "thesis": entry.thesis,
        "decision": entry.decision, "confidence": entry.confidence,
        "status": entry.status, "outcome": entry.outcome,
        "tags": entry.tags, "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


def _parse_form(data: dict) -> MemoryEntry:
    """Parse form submission (ticker_str/tags_str as comma-separated)."""
    ticker_str = (data.get("ticker_str") or "").strip()
    tags_str = (data.get("tags_str") or "").strip()
    ticker = [t.strip() for t in ticker_str.split(",") if t.strip()] if ticker_str else []
    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

    # Build thesis sub-object
    thesis = None
    if data.get("type") == "thesis":
        thesis = {}
        if data.get("target_price"):
            thesis["target_price"] = float(data["target_price"])

    # Build decision sub-object
    decision = None
    if data.get("type") == "decision":
        decision = {}
        if data.get("decision_type"):
            decision["type"] = data["decision_type"]
        if data.get("decision_price"):
            decision["price"] = float(data["decision_price"])
        if data.get("mood"):
            decision["mood"] = data["mood"]

    confidence = None
    if data.get("confidence") not in (None, "", "None"):
        with contextlib.suppress(ValueError, TypeError):
            confidence = float(data["confidence"])

    return MemoryEntry(
        id=int(data.get("id", 0)),
        type=data.get("type", "note"),
        ticker=ticker,
        title=(data.get("title") or "").strip(),
        content=(data.get("content") or "").strip(),
        thesis=thesis,
        decision=decision,
        confidence=confidence,
        status=data.get("status"),
        outcome=None,
        tags=tags,
    )


# ── List / Search ────────────────────────────────────────────

@v3_bp.route("/api/memory/list")
@token_required
def api_memory_list(current_user):
    filters = SearchFilters(
        keyword=request.args.get("keyword"),
        entry_type=request.args.get("type_filter") or request.args.get("type"),
        ticker=request.args.get("ticker_filter") or request.args.get("ticker"),
        status=request.args.get("status"),
        confidence_min=float(c) if (c := request.args.get("conf_min")) else None,
        limit=int(request.args.get("limit", 50)),
        offset=int(request.args.get("offset", 0)),
    )
    searcher = MemorySearch(_get_repo()._db)
    entries = searcher.query(filters)
    total = searcher.count(filters)

    if _is_htmx():
        return render_template("v3/partials/timeline_items.html",
                              entries=[_entry_to_dict(e) for e in entries],
                              total=total)
    return jsonify({
        "entries": [_entry_to_dict(e) for e in entries],
        "total": total, "limit": filters.limit, "offset": filters.offset,
    })


# ── Create ───────────────────────────────────────────────────

@v3_bp.route("/api/memory/create", methods=["POST"])
@token_required
def api_memory_create(current_user):
    data = request.get_json(silent=True) or {} if request.is_json else request.form.to_dict()

    try:
        if request.is_json and "ticker" in data:
            entry = MemoryEntry(
                type=data.get("type", "note"),
                ticker=data.get("ticker") if isinstance(data.get("ticker"), list) else [],
                title=(data.get("title") or "").strip(),
                content=(data.get("content") or "").strip(),
                thesis=data.get("thesis") if isinstance(data.get("thesis"), dict) else None,
                decision=data.get("decision") if isinstance(data.get("decision"), dict) else None,
                confidence=float(data["confidence"]) if data.get("confidence") not in (None, "", "None") else None,
                tags=data.get("tags") if isinstance(data.get("tags"), list) else [],
            )
        else:
            entry = _parse_form(data)

        entry_id = _get_repo().save(entry)

        if _is_htmx():
            # Return refreshed timeline
            searcher = MemorySearch(_get_repo()._db)
            entries = searcher.query(SearchFilters(limit=50))
            return render_template("v3/partials/timeline_items.html",
                                  entries=[_entry_to_dict(e) for e in entries],
                                  total=len(entries))
        return jsonify({"id": entry_id, "message": "created"}), 201
    except (ValueError, TypeError) as e:
        if _is_htmx():
            return f'<div class="empty-state"><div class="empty-title">Error</div><div class="empty-desc">{e}</div></div>', 400
        return jsonify({"error": "validation_failed", "detail": str(e)}), 400


# ── Read / Update / Delete ──────────────────────────────────

@v3_bp.route("/api/memory/<int:entry_id>")
@token_required
def api_memory_detail(current_user, entry_id):
    entry = _get_repo().get_by_id(entry_id)
    if entry is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(_entry_to_dict(entry))


@v3_bp.route("/api/memory/<int:entry_id>", methods=["PUT"])
@token_required
def api_memory_update(current_user, entry_id):
    data = request.get_json(silent=True) or {}
    try:
        if isinstance(data.get("ticker"), list):
            entry = MemoryEntry(
                type=data.get("type", "note"),
                ticker=data["ticker"],
                title=data.get("title", ""),
                content=data.get("content", ""),
                confidence=float(data["confidence"]) if data.get("confidence") not in (None, "", "None") else None,
                status=data.get("status"),
                tags=data.get("tags") if isinstance(data.get("tags"), list) else [],
            )
        else:
            entry = _parse_form(data)
        ok = _get_repo().update(entry_id, entry)
        if not ok:
            return jsonify({"error": "not_found"}), 404
        return jsonify({"message": "updated"})
    except (ValueError, TypeError) as e:
        return jsonify({"error": "validation_failed", "detail": str(e)}), 400


@v3_bp.route("/api/memory/<int:entry_id>", methods=["DELETE"])
@token_required
def api_memory_delete(current_user, entry_id):
    ok = _get_repo().delete(entry_id)
    if not ok:
        return jsonify({"error": "not_found"}), 404
    if _is_htmx():
        searcher = MemorySearch(_get_repo()._db)
        entries = searcher.query(SearchFilters(limit=50))
        return render_template("v3/partials/timeline_items.html",
                              entries=[_entry_to_dict(e) for e in entries],
                              total=len(entries))
    return jsonify({"message": "deleted"})


# ── Review ───────────────────────────────────────────────────

@v3_bp.route("/api/memory/<int:entry_id>/review", methods=["POST"])
@token_required
def api_memory_review(current_user, entry_id):
    entry = _get_repo().get_by_id(entry_id)
    if entry is None:
        return jsonify({"error": "not_found"}), 404
    data = request.get_json(silent=True) or {}
    outcome = {
        "detail": data.get("detail", ""),
        "return_pct": float(data["return_pct"]) if data.get("return_pct") else None,
        "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    updated = MemoryEntry(
        id=entry.id, type=entry.type, ticker=entry.ticker,
        title=entry.title, content=entry.content,
        thesis=entry.thesis, decision=entry.decision,
        confidence=entry.confidence,
        status=data.get("status", entry.status),
        outcome=outcome, tags=entry.tags, created_at=entry.created_at,
    )
    _get_repo().update(entry_id, updated)
    return jsonify({"message": "reviewed", "status": data.get("status")})


# ── Analytics ────────────────────────────────────────────────

@v3_bp.route("/api/memory/analytics")
@token_required
def api_memory_analytics(current_user):
    a = MemoryAnalytics(_get_repo()._db)
    stats = a.get_stats()
    cal = a.get_calibration()

    payload = {
        "stats": {
            "total_entries": stats.total_entries,
            "notes": stats.notes, "theses": stats.theses,
            "decisions": stats.decisions, "reflections": stats.reflections,
            "active_theses": stats.active_theses,
            "thesis_hit_rate": stats.thesis_hit_rate,
            "thesis_correct": stats.thesis_correct,
            "thesis_wrong": stats.thesis_wrong,
            "thesis_pending": stats.thesis_pending,
            "decision_win_rate": stats.decision_win_rate,
            "decision_good": stats.decision_good,
            "decision_bad": stats.decision_bad,
            "streak_days": stats.streak_days,
            "avg_confidence": stats.avg_confidence,
            "top_tags": [{"tag": t, "count": c} for t, c in stats.top_tags],
        },
        "calibration": {
            "buckets": [
                {"label": b.label, "total": b.total, "hit_rate": b.hit_rate,
                 "min_conf": b.min_conf, "max_conf": b.max_conf}
                for b in cal.buckets
            ],
            "overall_hit_rate": cal.overall_hit_rate,
            "is_calibrated": cal.is_calibrated,
            "insight": cal.insight,
        },
    }

    if _is_htmx():
        if "sidebar" in request.args:
            return render_template("v3/partials/analytics_sidebar.html", **payload)
        return render_template("v3/partials/stat_bar.html", **payload)
    return jsonify(payload)


@v3_bp.route("/api/memory/pending-reviews")
@token_required
def api_memory_pending_reviews(current_user):
    a = MemoryAnalytics(_get_repo()._db)
    pending = a.get_pending_reviews(min_days_since_creation=0)
    return jsonify({"pending_reviews": pending, "total": len(pending)})


# ── Related ──────────────────────────────────────────────────

@v3_bp.route("/api/memory/<int:entry_id>/related")
@token_required
def api_memory_related(current_user, entry_id):
    searcher = MemorySearch(_get_repo()._db)
    related = searcher.find_related(entry_id=entry_id)
    return jsonify({
        "related": [_entry_to_dict(e) for e in related],
        "total": len(related),
    })


@v3_bp.route("/api/memory/<int:entry_id>/similar")
@token_required
def api_memory_similar(current_user, entry_id):
    similar = find_similar(_get_repo()._db, entry_id, limit=10)
    return jsonify({
        "similar": [_entry_to_dict(e) for e in similar],
        "total": len(similar),
    })
