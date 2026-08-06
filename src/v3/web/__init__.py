"""V3 Web Layer — Flask Blueprint for Investment Memory System.

Registers all /journal and /api/memory/* routes.
Import and register in web_modern.py:

    from src.v3.web import register_v3_routes
    register_v3_routes(app)
"""

from __future__ import annotations

from flask import Blueprint

v3_bp = Blueprint(
    "v3",
    __name__,
    template_folder="../../../templates/v3",
    static_folder="../../../static",
)


def register_v3_routes(app) -> None:
    """Register the V3 blueprint on the Flask app."""
    from src.v3.web import journal_api, journal_page  # noqa: F401 — route registration side-effects

    app.register_blueprint(v3_bp)
