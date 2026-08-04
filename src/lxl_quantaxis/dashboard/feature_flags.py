"""User-scoped dashboard migration flag."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DashboardFeatureFlags:
    professional_dashboard_users: frozenset[str] = frozenset()
    globally_enabled: bool = False

    def professional_enabled(self, user_id: str) -> bool:
        return self.globally_enabled or user_id in self.professional_dashboard_users
