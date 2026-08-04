"""Auditable operational kill switch for simulated execution."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class KillSwitchEvent:
    active: bool
    actor: str
    reason: str
    occurred_at: datetime


class OperationalKillSwitch:
    def __init__(self) -> None:
        self.active = False
        self.events: list[KillSwitchEvent] = []

    def set(self, *, active: bool, actor: str, reason: str, occurred_at: datetime) -> None:
        if not actor.strip() or not reason.strip():
            raise ValueError("kill switch changes require actor and reason")
        self.active = active
        self.events.append(KillSwitchEvent(active, actor, reason, occurred_at))
