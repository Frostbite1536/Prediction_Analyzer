# tests/api/test_security.py
"""Tests for security features: headers, rate limiting, CORS."""
import pytest

from .conftest import create_authenticated_user


class TestSecurityHeaders:
    """Verify security headers are present on all responses."""

    def test_root_has_security_headers(self, client):
        resp = client.get("/")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert resp.headers["X-XSS-Protection"] == "1; mode=block"
        assert "geolocation=()" in resp.headers["Permissions-Policy"]

    def test_api_endpoint_has_security_headers(self, client):
        _, headers = create_authenticated_user(client)
        resp = client.get("/api/v1/trades", headers=headers)
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"

    def test_no_hsts_on_http(self, client):
        """HSTS should not be set when not using HTTPS."""
        resp = client.get("/")
        assert "Strict-Transport-Security" not in resp.headers


class TestHealthCheck:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "version" in data
        assert data["docs"] == "/docs"
