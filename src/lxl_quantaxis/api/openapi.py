"""Minimal executable OpenAPI contract for the parallel v1 routes."""

OPENAPI = {
    "openapi": "3.1.0",
    "info": {"title": "LXL QuantAxis API", "version": "1.0.0"},
    "paths": {
        "/api/v1/research": {"post": {"operationId": "createResearch"}},
        "/api/v1/memory/drafts": {"post": {"operationId": "createMemoryDraft"}},
        "/api/v1/paper/orders": {"post": {"operationId": "submitPaperOrder"}},
        "/api/v1/daily-brief": {"get": {"operationId": "getDailyBrief"}},
    },
}
