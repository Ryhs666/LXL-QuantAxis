from __future__ import annotations

import unittest

from src.lxl_quantaxis.api.legacy import adapt_legacy_request
from src.lxl_quantaxis.api.openapi import OPENAPI
from src.lxl_quantaxis.api.schemas import ApiRequest, Page
from src.lxl_quantaxis.api.services import V1Router


def _request(**changes: object) -> ApiRequest:
    values: dict[str, object] = {
        "method": "POST",
        "path": "/api/v1/memory/drafts",
        "organization_id": "org-a",
        "user_id": "u-1",
        "roles": frozenset({"researcher"}),
        "body": {"note": "test"},
        "idempotency_key": "key-1",
    }
    values.update(changes)
    return ApiRequest(**values)


class V1ContractTests(unittest.TestCase):
    def test_openapi_declares_core_workflows(self) -> None:
        self.assertEqual(OPENAPI["openapi"], "3.1.0")
        self.assertEqual(len(OPENAPI["paths"]), 4)

    def test_permissions_and_uniform_error(self) -> None:
        router = V1Router()
        router.register("POST", "/api/v1/memory/drafts", lambda request: request.body, required_role="researcher")
        denied = router.dispatch(_request(roles=frozenset()))
        self.assertEqual(denied.status, 403)
        self.assertEqual(denied.error.code if denied.error else None, "forbidden")

    def test_mutation_requires_and_reuses_idempotency_key(self) -> None:
        calls = 0

        def handler(request: ApiRequest) -> object:
            nonlocal calls
            calls += 1
            return {"calls": calls, "organization": request.organization_id}

        router = V1Router()
        router.register("POST", "/api/v1/memory/drafts", handler)
        missing = router.dispatch(_request(idempotency_key=None))
        self.assertEqual(missing.status, 400)
        first = router.dispatch(_request())
        second = router.dispatch(_request())
        self.assertEqual(first, second)
        self.assertEqual(calls, 1)
        self.assertEqual(len(router.audit_log.events), 3)

    def test_pagination_limits_are_enforced(self) -> None:
        self.assertEqual(Page(offset=20, limit=50).offset, 20)
        with self.assertRaises(ValueError):
            Page(limit=201)

    def test_all_legacy_entries_produce_equivalent_application_request(self) -> None:
        requests = [
            adapt_legacy_request(
                entrypoint=name,
                method="GET",
                path="/api/v1/daily-brief",
                organization_id="org-a",
                user_id="u-1",
                roles=frozenset({"researcher"}),
            )
            for name in ("cli", "classic-web", "modern-web", "tkinter")
        ]
        self.assertTrue(all(request == requests[0] for request in requests))


if __name__ == "__main__":
    unittest.main()
