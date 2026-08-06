"""Journal page route — serves the Investment Memory System web UI."""

from __future__ import annotations

from flask import render_template

from src.auth import token_required
from src.v3.web import v3_bp


@v3_bp.route("/journal")
@token_required
def journal_page(current_user):
    """Investment Memory System — journal page."""
    return render_template("v3/journal.html", current_user=current_user)
