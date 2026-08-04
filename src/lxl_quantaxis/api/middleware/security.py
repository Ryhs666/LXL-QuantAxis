"""Authorization, idempotency, and audit middleware primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.lxl_quantaxis.api.schemas import ApiRequest, ApiResponse


@dataclass(frozen=True, slots=True)
class AuditEvent:
    occurred_at: datetime
    organization_id: str
    user_id: str
    method: str
    path: str
    status: int


class AuditLog:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self.events.append(event)


class IdempotencyStore:
    def __init__(self) -> None:
        self._responses: dict[tuple[str, str, str], ApiResponse] = {}

    def get(self, request: ApiRequest) -> ApiResponse | None:
        if request.idempotency_key is None:
            return None
        return self._responses.get((request.organization_id, request.path, request.idempotency_key))

    def put(self, request: ApiRequest, response: ApiResponse) -> None:
        if request.idempotency_key is not None:
            self._responses[(request.organization_id, request.path, request.idempotency_key)] = response


def authorized(request: ApiRequest, required_role: str | None) -> bool:
    return required_role is None or required_role in request.roles or "admin" in request.roles
