# tests/api/conftest.py
"""
Fixtures for FastAPI integration tests.

Uses an in-memory SQLite database so tests are fast and isolated.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from prediction_analyzer.api.database import Base
from prediction_analyzer.api.dependencies import get_db
from prediction_analyzer.api.main import app, _rate_store

# In-memory SQLite for tests
_TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _setup_db():
    """Create all tables before each test, drop after. Clear rate limiter."""
    Base.metadata.create_all(bind=_TEST_ENGINE)
    _rate_store.clear()
    yield
    Base.metadata.drop_all(bind=_TEST_ENGINE)


@pytest.fixture()
def client():
    """FastAPI TestClient with overridden DB dependency."""
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session():
    """Direct DB session for setting up test data."""
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


# ---- Helpers ---------------------------------------------------------------


def signup_user(
    client: TestClient, email="test@example.com", username="testuser", password="password123"
):
    """Register a user and return the response."""
    resp = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "username": username,
            "password": password,
        },
    )
    return resp


def auth_header(token: str) -> dict:
    """Build an Authorization header from a bearer token."""
    return {"Authorization": f"Bearer {token}"}


def create_authenticated_user(
    client: TestClient, email="test@example.com", username="testuser", password="password123"
):
    """Register a user and return (response_json, auth_headers)."""
    resp = signup_user(client, email, username, password)
    assert resp.status_code == 201, f"Signup failed: {resp.status_code} {resp.text}"
    data = resp.json()
    return data, auth_header(data["access_token"])
