"""Transport-neutral API v1 request and response schemas."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Page:
    offset: int = 0
    limit: int = 50

    def __post_init__(self) -> None:
        if self.offset < 0 or not 1 <= self.limit <= 200:
            raise ValueError("pagination requires offset >= 0 and limit between 1 and 200")


@dataclass(frozen=True, slots=True)
class ApiRequest:
    method: str
    path: str
    organization_id: str
    user_id: str
    roles: frozenset[str]
    body: Mapping[str, object] = field(default_factory=dict)
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class ApiError:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ApiResponse:
    status: int
    data: object | None = None
    error: ApiError | None = None
