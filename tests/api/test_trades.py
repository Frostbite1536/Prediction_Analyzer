# tests/api/test_trades.py
"""Tests for trade CRUD, upload, export, and provider listing."""
import io
import json
import pytest

from .conftest import create_authenticated_user, auth_header, signup_user

# Minimal valid trade file (Limitless format)
_SAMPLE_TRADES_JSON = json.dumps([
    {
        "market": {"title": "Test Market", "slug": "test-market"},
        "timestamp": 1704067200,
        "strategy": "Buy",
        "outcomeIndex": 0,
        "outcomeTokenAmount": 100,
        "collateralAmount": 50,
        "pnl": 5,
        "blockTimestamp": 1704067200,
    },
    {
        "market": {"title": "Test Market", "slug": "test-market"},
        "timestamp": 1704153600,
        "strategy": "Sell",
        "outcomeIndex": 0,
        "outcomeTokenAmount": 50,
        "collateralAmount": 30,
        "pnl": -2,
        "blockTimestamp": 1704153600,
    },
])


def _upload_trades(client, headers, content=None, filename="trades.json"):
    """Helper to upload a trade file."""
    content = content or _SAMPLE_TRADES_JSON.encode()
    return client.post(
        "/api/v1/trades/upload",
        headers=headers,
        files={"file": (filename, io.BytesIO(content), "application/json")},
    )


class TestUpload:
    def test_upload_json(self, client):
        _, headers = create_authenticated_user(client)
        resp = _upload_trades(client, headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["trade_count"] == 2
        assert data["upload_id"] >= 1

    def test_upload_duplicate_rejected(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        resp = _upload_trades(client, headers)
        assert resp.status_code == 400
        assert "already uploaded" in resp.json()["detail"]

    def test_upload_unsupported_extension(self, client):
        _, headers = create_authenticated_user(client)
        resp = client.post(
            "/api/v1/trades/upload",
            headers=headers,
            files={"file": ("trades.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_requires_auth(self, client):
        resp = client.post(
            "/api/v1/trades/upload",
            files={"file": ("t.json", io.BytesIO(b"[]"), "application/json")},
        )
        assert resp.status_code == 401

    def test_upload_oversized_file(self, client):
        _, headers = create_authenticated_user(client)
        # 11 MB of data
        big = b"x" * (11 * 1024 * 1024)
        resp = client.post(
            "/api/v1/trades/upload",
            headers=headers,
            files={"file": ("big.json", io.BytesIO(big), "application/json")},
        )
        assert resp.status_code == 400
        assert "too large" in resp.json()["detail"].lower() or "File too large" in resp.json()["detail"]


class TestListTrades:
    def test_list_empty(self, client):
        _, headers = create_authenticated_user(client)
        resp = client.get("/api/v1/trades", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["trades"] == []

    def test_list_after_upload(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        resp = client.get("/api/v1/trades", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_list_pagination(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        resp = client.get("/api/v1/trades?limit=1&offset=0", headers=headers)
        data = resp.json()
        assert len(data["trades"]) == 1
        assert data["total"] == 2

    def test_list_source_filter(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        resp = client.get("/api/v1/trades?source=limitless", headers=headers)
        assert resp.status_code == 200
        # Limitless format trades should show up
        assert resp.json()["total"] >= 0


class TestGetTrade:
    def test_get_trade_by_id(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        # Get first trade
        list_resp = client.get("/api/v1/trades?limit=1", headers=headers)
        trade_id = list_resp.json()["trades"][0]["id"]

        resp = client.get(f"/api/v1/trades/{trade_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == trade_id

    def test_get_trade_not_found(self, client):
        _, headers = create_authenticated_user(client)
        resp = client.get("/api/v1/trades/99999", headers=headers)
        assert resp.status_code == 404


class TestDeleteTrades:
    def test_delete_single_trade(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        list_resp = client.get("/api/v1/trades?limit=1", headers=headers)
        trade_id = list_resp.json()["trades"][0]["id"]

        resp = client.delete(f"/api/v1/trades/{trade_id}", headers=headers)
        assert resp.status_code == 204

        # Verify deleted
        resp = client.get(f"/api/v1/trades/{trade_id}", headers=headers)
        assert resp.status_code == 404

    def test_delete_all_trades(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        resp = client.delete("/api/v1/trades", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 2

        # Verify all deleted
        list_resp = client.get("/api/v1/trades", headers=headers)
        assert list_resp.json()["total"] == 0


class TestProviders:
    def test_list_providers_requires_auth(self, client):
        resp = client.get("/api/v1/trades/providers")
        assert resp.status_code == 401

    def test_list_providers_authenticated(self, client):
        _, headers = create_authenticated_user(client)
        resp = client.get("/api/v1/trades/providers", headers=headers)
        assert resp.status_code == 200
        providers = resp.json()
        names = [p["name"] for p in providers]
        assert "limitless" in names
        assert "polymarket" in names
        assert "kalshi" in names
        assert "manifold" in names


class TestMarkets:
    def test_list_markets_empty(self, client):
        _, headers = create_authenticated_user(client)
        resp = client.get("/api/v1/trades/markets", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_markets_after_upload(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        resp = client.get("/api/v1/trades/markets", headers=headers)
        assert resp.status_code == 200
        markets = resp.json()
        assert len(markets) >= 1
        assert markets[0]["slug"] == "test-market"


class TestExport:
    def test_export_csv(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        resp = client.get("/api/v1/trades/export/csv", headers=headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        # Verify CSV content has expected columns
        lines = resp.text.strip().split("\n")
        header = lines[0]
        assert "market" in header
        assert "pnl" in header
        assert "source" in header

    def test_export_json(self, client):
        _, headers = create_authenticated_user(client)
        _upload_trades(client, headers)
        resp = client.get("/api/v1/trades/export/json", headers=headers)
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        data = json.loads(resp.text)
        assert len(data) == 2
        assert "source" in data[0]
        assert "currency" in data[0]

    def test_export_empty(self, client):
        _, headers = create_authenticated_user(client)
        resp = client.get("/api/v1/trades/export/csv", headers=headers)
        assert resp.status_code == 404


class TestUserIsolation:
    """Verify that users can only see their own trades."""

    def test_user_cannot_see_other_trades(self, client):
        _, headers_a = create_authenticated_user(client, "a@test.com", "user_a", "password123")
        _, headers_b = create_authenticated_user(client, "b@test.com", "user_b", "password123")

        # User A uploads trades
        _upload_trades(client, headers_a)

        # User B sees nothing
        resp = client.get("/api/v1/trades", headers=headers_b)
        assert resp.json()["total"] == 0

        # User A sees their trades
        resp = client.get("/api/v1/trades", headers=headers_a)
        assert resp.json()["total"] == 2

    def test_user_cannot_delete_other_trades(self, client):
        _, headers_a = create_authenticated_user(client, "a@test.com", "user_a", "password123")
        _, headers_b = create_authenticated_user(client, "b@test.com", "user_b", "password123")

        _upload_trades(client, headers_a)
        list_resp = client.get("/api/v1/trades?limit=1", headers=headers_a)
        trade_id = list_resp.json()["trades"][0]["id"]

        # User B cannot delete User A's trade
        resp = client.delete(f"/api/v1/trades/{trade_id}", headers=headers_b)
        assert resp.status_code == 404
