"""Professional Dashboard workspace navigation and visibility rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WorkspaceId(StrEnum):
    RESEARCH = "research"
    STRATEGY = "strategy-lab"
    BACKTEST = "backtest"
    PORTFOLIO_RISK = "portfolio-risk"
    PAPER = "paper"
    MEMORY = "memory"
    DAILY_BRIEF = "daily-brief"


class WorkspaceStatus(StrEnum):
    READY = "ready"
    EMPTY = "empty"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Workspace:
    workspace_id: WorkspaceId
    label: str
    description: str
    route: str
    required_role: str = "researcher"


@dataclass(frozen=True, slots=True)
class WorkspaceView:
    workspace: Workspace
    status: WorkspaceStatus
    message: str


WORKSPACES = (
    Workspace(
        WorkspaceId.RESEARCH,
        "Research",
        "Company, industry, financial and valuation research",
        "/professional/research",
    ),
    Workspace(
        WorkspaceId.STRATEGY,
        "Strategy Lab",
        "Turn confirmed ideas into versioned strategies",
        "/professional/strategy-lab",
    ),
    Workspace(
        WorkspaceId.BACKTEST, "Backtest", "Validate strategies with point-in-time data", "/professional/backtest"
    ),
    Workspace(
        WorkspaceId.PORTFOLIO_RISK,
        "Portfolio & Risk",
        "Positions, exposure, drawdown and risk controls",
        "/professional/portfolio-risk",
    ),
    Workspace(
        WorkspaceId.PAPER,
        "Paper Trading",
        "Simulated orders, fills and reconciliation",
        "/professional/paper",
        "trader",
    ),
    Workspace(WorkspaceId.MEMORY, "Alpha Memory", "Notes, theses and strategy history", "/professional/memory"),
    Workspace(WorkspaceId.DAILY_BRIEF, "Daily Brief", "Evidence-backed market workflow", "/professional/daily-brief"),
)


def visible_workspaces(roles: frozenset[str]) -> tuple[Workspace, ...]:
    return tuple(workspace for workspace in WORKSPACES if workspace.required_role in roles or "admin" in roles)
