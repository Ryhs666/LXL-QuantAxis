"""Journal page route — serves the Investment Memory System web UI."""

from __future__ import annotations

from flask import g, render_template

from src.auth import token_required
from src.v3.web import v3_bp


@v3_bp.route("/journal")
@token_required
def journal_page():
    """Investment Memory System — journal page."""
    return render_template("v3/journal.html", user_id=getattr(g, "user_id", None))
