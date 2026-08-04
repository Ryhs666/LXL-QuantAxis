"""Thin API v1 router over application handlers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from src.lxl_quantaxis.api.middleware import AuditEvent, AuditLog, IdempotencyStore, authorized
from src.lxl_quantaxis.api.schemas import ApiError, ApiRequest, ApiResponse

Handler = Callable[[ApiRequest], object]


@dataclass(frozen=True, slots=True)
class Route:
    handler: Handler
    required_role: str | None = None


class V1Router:
    def __init__(self, *, audit_log: AuditLog | None = None, idempotency: IdempotencyStore | None = None) -> None:
        self.routes: dict[tuple[str, str], Route] = {}
        self.audit_log = audit_log or AuditLog()
        self.idempotency = idempotency or IdempotencyStore()

    def register(self, method: str, path: str, handler: Handler, *, required_role: str | None = None) -> None:
        if not path.startswith("/api/v1/"):
            raise ValueError("v1 routes must use /api/v1")
        self.routes[(method.upper(), path)] = Route(handler, required_role)

    def dispatch(self, request: ApiRequest) -> ApiResponse:
        route = self.routes.get((request.method.upper(), request.path))
        if route is None:
            return self._finish(request, ApiResponse(404, error=ApiError("not_found", "route not found")))
        if not authorized(request, route.required_role):
            return self._finish(request, ApiResponse(403, error=ApiError("forbidden", "permission denied")))
        if request.method.upper() in {"POST", "PUT", "PATCH"}:
            if not request.idempotency_key:
                return self._finish(
                    request,
                    ApiResponse(400, error=ApiError("idempotency_required", "idempotency key is required")),
                )
            cached = self.idempotency.get(request)
            if cached is not None:
                return self._finish(request, cached)
        try:
            response = ApiResponse(200, data=route.handler(request))
        except (KeyError, TypeError, ValueError) as error:
            response = ApiResponse(400, error=ApiError("invalid_request", str(error)))
        if response.status < 400:
            self.idempotency.put(request, response)
        return self._finish(request, response)

    def _finish(self, request: ApiRequest, response: ApiResponse) -> ApiResponse:
        self.audit_log.append(
            AuditEvent(
                datetime.now(UTC),
                request.organization_id,
                request.user_id,
                request.method.upper(),
                request.path,
                response.status,
            )
        )
        return response
