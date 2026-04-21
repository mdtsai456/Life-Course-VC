from __future__ import annotations

import uuid


class TestRequestIdMiddleware:
    def test_preserves_valid_request_id(self, client):
        request_id = "req-123._ABC"

        response = client.get("/health", headers={"X-Request-ID": request_id})

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == request_id

    def test_replaces_invalid_request_id(self, client):
        response = client.get("/health", headers={"X-Request-ID": "invalid request id"})

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] != "invalid request id"
        uuid.UUID(response.headers["X-Request-ID"])
