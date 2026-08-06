"""Personal Investment Workspace — Phase 2 core module.

The Workspace is a VIEW layer over the Investment Memory System.
It provides the investor's daily driver dashboard: watchlist,
active theses, research queue, and portfolio overview.

Zero new database tables. All data stored via tag conventions
in memory_entries or read-only from V2 trades.db.

Public API:
  - WorkspaceService: Aggregate data from Memory + Portfolio
  - MemoryAdapter:    Tag-convention CRUD over memory_entries
  - PortfolioAdapter: Read-only V2 trades.db access
"""

from __future__ import annotations

from flask import Blueprint

v3_ws_bp = Blueprint(
    "v3_workspace",
    __name__,
    template_folder="../../../templates/v3",
    static_folder="../../../static",
)

# Import routes to register them on the blueprint
from src.v3.workspace import routes  # noqa: E402, F401 — side-effect route registration

__all__ = [
    "MemoryAdapter",
    "PortfolioAdapter",
    "WorkspaceService",
    "v3_ws_bp",
]

# Deferred imports to avoid circular dependencies
def __getattr__(name: str):
    if name == "WorkspaceService":
        from src.v3.workspace.service import WorkspaceService
        return WorkspaceService
    if name == "MemoryAdapter":
        from src.v3.workspace.repository import MemoryAdapter
        return MemoryAdapter
    if name == "PortfolioAdapter":
        from src.v3.workspace.repository import PortfolioAdapter
        return PortfolioAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
