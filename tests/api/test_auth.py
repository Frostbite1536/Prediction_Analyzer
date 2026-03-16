# tests/api/test_auth.py
"""Tests for authentication endpoints: signup, login, token validation."""


from .conftest import signup_user, auth_header, create_authenticated_user


class TestSignup:
    def test_signup_success(self, client):
        resp = signup_user(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["access_token"]
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["username"] == "testuser"

    def test_signup_duplicate_email(self, client):
        signup_user(client)
        resp = signup_user(client, username="other")
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    def test_signup_duplicate_username(self, client):
        signup_user(client)
        resp = signup_user(client, email="other@example.com")
        assert resp.status_code == 400
        assert "already taken" in resp.json()["detail"]

    def test_signup_short_password(self, client):
        resp = signup_user(client, password="short")
        assert resp.status_code == 422  # Pydantic validation

    def test_signup_short_username(self, client):
        resp = signup_user(client, username="ab")
        assert resp.status_code == 422

    def test_signup_invalid_email(self, client):
        resp = signup_user(client, email="not-an-email")
        assert resp.status_code == 422


class TestLoginJson:
    def test_login_json_success(self, client):
        signup_user(client)
        resp = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]
        assert resp.json()["token_type"] == "bearer"

    def test_login_json_wrong_password(self, client):
        signup_user(client)
        resp = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": "test@example.com",
                "password": "wrong",
            },
        )
        assert resp.status_code == 401
        assert "Incorrect email or password" in resp.json()["detail"]

    def test_login_json_nonexistent_user(self, client):
        resp = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": "nobody@example.com",
                "password": "password123",
            },
        )
        assert resp.status_code == 401


class TestLoginOAuth2:
    def test_login_form_success(self, client):
        signup_user(client)
        resp = client.post(
            "/api/v1/auth/login",
            data={
                "username": "test@example.com",
                "password": "password123",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]


class TestTokenValidation:
    def test_invalid_token_rejected(self, client):
        resp = client.get("/api/v1/trades", headers=auth_header("garbage.token.here"))
        assert resp.status_code == 401

    def test_missing_token_rejected(self, client):
        resp = client.get("/api/v1/trades")
        assert resp.status_code == 401

    def test_valid_token_accepted(self, client):
        _, headers = create_authenticated_user(client)
        resp = client.get("/api/v1/trades", headers=headers)
        assert resp.status_code == 200
