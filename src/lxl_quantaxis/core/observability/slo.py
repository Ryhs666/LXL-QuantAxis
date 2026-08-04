"""SLO and alert evaluation contracts."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ServiceLevelObjective:
    name: str
    target: Decimal
    window: str

    def __post_init__(self) -> None:
        if not Decimal("0") < self.target <= Decimal("1") or not self.window.strip():
            raise ValueError("SLO target must be in (0, 1] with a window")

    def breached(self, achieved: Decimal) -> bool:
        return achieved < self.target


@dataclass(frozen=True, slots=True)
class Alert:
    name: str
    severity: str
    message: str
