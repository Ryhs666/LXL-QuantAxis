from __future__ import annotations

import unittest
from pathlib import Path

from src.lxl_quantaxis.dashboard import DashboardFeatureFlags
from src.lxl_quantaxis.dashboard.workspaces import (
    WORKSPACES,
    WorkspaceId,
    WorkspaceStatus,
    WorkspaceView,
    visible_workspaces,
)


class WorkspaceContractTests(unittest.TestCase):
    def test_all_investment_workflow_workspaces_exist(self) -> None:
        self.assertEqual({workspace.workspace_id for workspace in WORKSPACES}, set(WorkspaceId))

    def test_trading_workspace_requires_trader_role(self) -> None:
        researcher = visible_workspaces(frozenset({"researcher"}))
        trader = visible_workspaces(frozenset({"researcher", "trader"}))
        self.assertNotIn(WorkspaceId.PAPER, {item.workspace_id for item in researcher})
        self.assertIn(WorkspaceId.PAPER, {item.workspace_id for item in trader})

    def test_feature_flag_preserves_classic_dashboard(self) -> None:
        flags = DashboardFeatureFlags(professional_dashboard_users=frozenset({"u-2"}))
        self.assertFalse(flags.professional_enabled("u-1"))
        self.assertTrue(flags.professional_enabled("u-2"))

    def test_degraded_and_empty_states_have_user_facing_messages(self) -> None:
        workspace = WORKSPACES[0]
        for status in (WorkspaceStatus.EMPTY, WorkspaceStatus.DEGRADED, WorkspaceStatus.ERROR):
            view = WorkspaceView(workspace, status, "Data is temporarily unavailable.")
            self.assertTrue(view.message)

    def test_template_has_landmarks_live_region_and_keyboard_skip_link(self) -> None:
        root = Path(__file__).parents[2]
        template = root.joinpath("templates", "professional.html").read_text(encoding="utf-8")
        self.assertIn('<nav aria-label="Research workspaces">', template)
        self.assertIn('<main id="workspace-main">', template)
        self.assertIn('aria-live="polite"', template)
        self.assertIn('class="skip-link"', template)
        self.assertNotIn('tabindex="1"', template)


if __name__ == "__main__":
    unittest.main()
