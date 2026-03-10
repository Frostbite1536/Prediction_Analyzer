# tests/mcp/test_sse_transport.py
"""Tests for HTTP/SSE transport setup."""
import pytest
from starlette.testclient import TestClient

from prediction_mcp.server import create_sse_app


class TestSSEApp:
    def test_app_creates_successfully(self):
        app = create_sse_app()
        assert app is not None

    def test_health_endpoint(self):
        app = create_sse_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["server"] == "prediction-analyzer"
        assert data["version"] == "1.0.0"

    def test_custom_paths(self):
        app = create_sse_app(sse_path="/custom-sse", message_path="/custom-messages")
        assert app is not None
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_routes_registered(self):
        """Verify SSE and messages routes are registered."""
        app = create_sse_app()
        route_paths = [r.path for r in app.routes]
        assert "/health" in route_paths
        assert "/sse" in route_paths
        assert "/messages" in route_paths

    def test_custom_route_paths(self):
        """Verify custom SSE/message paths are registered."""
        app = create_sse_app(sse_path="/my-sse", message_path="/my-msgs")
        route_paths = [r.path for r in app.routes]
        assert "/my-sse" in route_paths
        assert "/my-msgs" in route_paths
        assert "/health" in route_paths

    def test_messages_requires_post(self):
        """Messages endpoint should only accept POST."""
        app = create_sse_app()
        for route in app.routes:
            if route.path == "/messages":
                assert "POST" in route.methods
                break
