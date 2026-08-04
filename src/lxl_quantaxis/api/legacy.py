"""Shared compatibility contract for legacy UI entry points."""

from collections.abc import Mapping

from src.lxl_quantaxis.api.schemas import ApiRequest

V2_API_PREFIX = "/api/v1"


def adapt_legacy_request(
    *,
    entrypoint: str,
    method: str,
    path: str,
    organization_id: str,
    user_id: str,
    roles: frozenset[str],
    body: Mapping[str, object] | None = None,
    idempotency_key: str | None = None,
) -> ApiRequest:
    if entrypoint not in {"cli", "classic-web", "modern-web", "tkinter"}:
        raise ValueError("unknown legacy entry point")
    return ApiRequest(method, path, organization_id, user_id, roles, body or {}, idempotency_key)
