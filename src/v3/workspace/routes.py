"""Workspace Flask routes — dashboard page + REST API.

All routes require JWT auth. HTMX requests get HTML partials.
JSON requests get structured data.
"""

from __future__ import annotations

from flask import jsonify, render_template, request

from src.auth import token_required
from src.v3.workspace import v3_ws_bp
from src.v3.workspace.service import WorkspaceService


def _get_service() -> WorkspaceService:
    """Lazy-init the workspace service singleton."""
    if not hasattr(_get_service, "_instance"):
        _get_service._instance = WorkspaceService()  # type: ignore[attr-defined]
    return _get_service._instance  # type: ignore[attr-defined]


def _is_htmx() -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


# ═══════════════════════════════════════════════════════════════
# Page route
# ═══════════════════════════════════════════════════════════════

@v3_ws_bp.route("/workspace")
@token_required
def workspace_page():
    """Personal Investment Workspace — daily driver dashboard."""
    return render_template("v3/workspace.html")


# ═══════════════════════════════════════════════════════════════
# Dashboard API
# ═══════════════════════════════════════════════════════════════

@v3_ws_bp.route("/api/workspace/dashboard")
@token_required
def api_dashboard():
    """Full dashboard data — all panels in one response."""
    svc = _get_service()
    dash = svc.get_dashboard()

    payload = {
        "stats": {
            "active_theses": dash.active_thesis_count,
            "watchlist": dash.watchlist_count,
            "queue": dash.queue_count,
            "pending_reviews": dash.pending_review_count,
        },
        "active_theses": dash.active_theses,
        "watchlist": dash.watchlist,
        "queue": dash.queue,
        "pending_reviews": dash.pending_reviews,
        "portfolio": dash.portfolio,
        "recent_reflections": dash.recent_reflections,
    }

    if _is_htmx():
        return render_template("v3/partials/workspace_dashboard.html", **payload)
    return jsonify(payload)


# ═══════════════════════════════════════════════════════════════
# Watchlist API
# ═══════════════════════════════════════════════════════════════

@v3_ws_bp.route("/api/workspace/watchlist")
@token_required
def api_watchlist():
    """Get watchlist entries."""
    svc = _get_service()
    items = svc.get_watchlist()
    if _is_htmx():
        return render_template("v3/partials/workspace_watchlist.html", items=items)
    return jsonify(items)


@v3_ws_bp.route("/api/workspace/watchlist", methods=["POST"])
@token_required
def api_watchlist_add():
    """Add a watchlist entry."""
    data = request.get_json(silent=True) or request.form.to_dict()
    ticker_str = (data.get("ticker") or "").strip()
    ticker = [t.strip() for t in ticker_str.split(",") if t.strip()]

    if not ticker:
        return jsonify({"error": "ticker is required"}), 400

    svc = _get_service()
    eid = svc.add_watchlist(
        ticker=ticker,
        title=(data.get("title") or "").strip() or ticker[0],
        content=(data.get("content") or "").strip(),
        priority=data.get("priority", "med"),
    )
    if _is_htmx():
        items = svc.get_watchlist()
        return render_template("v3/partials/workspace_watchlist.html", items=items)
    return jsonify({"id": eid, "message": "added"}), 201


@v3_ws_bp.route("/api/workspace/watchlist/<int:entry_id>", methods=["DELETE"])
@token_required
def api_watchlist_remove(entry_id):
    """Remove a watchlist entry."""
    svc = _get_service()
    ok = svc.remove_watchlist(entry_id)
    if not ok:
        return jsonify({"error": "not_found"}), 404
    if _is_htmx():
        items = svc.get_watchlist()
        return render_template("v3/partials/workspace_watchlist.html", items=items)
    return jsonify({"message": "removed"})


# ═══════════════════════════════════════════════════════════════
# Queue API
# ═══════════════════════════════════════════════════════════════

@v3_ws_bp.route("/api/workspace/queue")
@token_required
def api_queue():
    """Get research queue entries."""
    svc = _get_service()
    items = svc.get_queue()
    if _is_htmx():
        return render_template("v3/partials/workspace_queue.html", items=items)
    return jsonify(items)


@v3_ws_bp.route("/api/workspace/queue", methods=["POST"])
@token_required
def api_queue_add():
    """Add a queue entry."""
    data = request.get_json(silent=True) or request.form.to_dict()
    ticker_str = (data.get("ticker") or "").strip()
    ticker = [t.strip() for t in ticker_str.split(",") if t.strip()] if ticker_str else []

    svc = _get_service()
    eid = svc.add_queue(
        title=(data.get("title") or "").strip(),
        ticker=ticker or None,
        content=(data.get("content") or "").strip(),
        priority=data.get("priority", "med"),
    )
    if _is_htmx():
        items = svc.get_queue()
        return render_template("v3/partials/workspace_queue.html", items=items)
    return jsonify({"id": eid, "message": "added"}), 201


@v3_ws_bp.route("/api/workspace/queue/<int:entry_id>/done", methods=["PUT"])
@token_required
def api_queue_done(entry_id):
    """Mark a queue item as done."""
    svc = _get_service()
    ok = svc.mark_queue_done(entry_id)
    if not ok:
        return jsonify({"error": "not_found"}), 404
    if _is_htmx():
        items = svc.get_queue()
        return render_template("v3/partials/workspace_queue.html", items=items)
    return jsonify({"message": "done"})


# ═══════════════════════════════════════════════════════════════
# Thesis API
# ═══════════════════════════════════════════════════════════════

@v3_ws_bp.route("/api/workspace/theses")
@token_required
def api_theses():
    """Get active theses."""
    svc = _get_service()
    items = svc.get_active_theses()
    if _is_htmx():
        return render_template("v3/partials/workspace_thesis.html", items=items)
    return jsonify(items)


@v3_ws_bp.route("/api/workspace/theses/<int:entry_id>/outcome", methods=["POST"])
@token_required
def api_thesis_outcome(entry_id):
    """Mark a thesis outcome (correct/wrong)."""
    data = request.get_json(silent=True) or {}
    status = data.get("status", "").strip()
    if status not in ("correct", "wrong"):
        return jsonify({"error": "status must be 'correct' or 'wrong'"}), 400

    svc = _get_service()
    ok = svc.mark_thesis_outcome(
        entry_id, status,
        detail=(data.get("detail") or "").strip(),
        return_pct=float(data["return_pct"]) if data.get("return_pct") else None,
    )
    if not ok:
        return jsonify({"error": "not_found"}), 404

    if _is_htmx():
        items = svc.get_active_theses()
        return render_template("v3/partials/workspace_thesis.html", items=items)
    return jsonify({"message": "outcome_recorded", "status": status})


# ═══════════════════════════════════════════════════════════════
# Portfolio API
# ═══════════════════════════════════════════════════════════════

@v3_ws_bp.route("/api/workspace/portfolio")
@token_required
def api_portfolio():
    """Get portfolio overview (read-only from V2 trades.db)."""
    svc = _get_service()
    data = svc.get_portfolio()
    if _is_htmx():
        return render_template("v3/partials/workspace_portfolio.html", portfolio=data)
    return jsonify(data)


# ═══════════════════════════════════════════════════════════════
# Pending Reviews
# ═══════════════════════════════════════════════════════════════

@v3_ws_bp.route("/api/workspace/pending-reviews")
@token_required
def api_pending_reviews():
    """Get pending thesis reviews."""
    svc = _get_service()
    items = svc.get_pending_reviews()
    if _is_htmx():
        return render_template("v3/partials/workspace_reviews.html", items=items)
    return jsonify(items)
