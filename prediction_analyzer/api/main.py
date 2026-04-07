# prediction_analyzer/api/main.py
"""
FastAPI application - main entry point
"""

import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .config import get_settings
from .database import init_db
from .routers import (
    auth_router,
    users_router,
    trades_router,
    analysis_router,
    charts_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database on startup."""
    init_db()
    yield


# ---------------------------------------------------------------------------
# In-memory rate limiter (per-IP, sliding window)
# ---------------------------------------------------------------------------
# Two tiers: a strict limit for auth endpoints and a general limit for all others.
#
# NOTE: This rate limiter is in-memory and per-process. It does NOT share
# state across multiple workers/servers. For multi-instance deployments,
# replace with a Redis-backed solution (e.g. fastapi-limiter).
_rate_store: dict = defaultdict(list)  # key -> list of timestamps
_rate_lock = threading.Lock()
_RATE_LIMIT_AUTH = 5  # max requests per window on /auth/*
_RATE_LIMIT_GENERAL = 60  # max requests per window on all other endpoints
_RATE_WINDOW = 60  # window size in seconds
_RATE_MAX_KEYS = 10_000  # max tracked IPs before evicting oldest entries


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    API for analyzing prediction market trades.

    ## Features

    - **User Accounts**: Create an account, login, and manage your profile
    - **Trade Management**: Upload trade files (JSON, CSV, XLSX), view and manage trades
    - **Analysis**: Calculate PnL summaries, market breakdowns, and time-series data
    - **Charts**: Get chart data for price history, cumulative PnL, and exposure
    - **Saved Analyses**: Save and retrieve analysis results

    ## Authentication

    Most endpoints require authentication. Use the `/auth/signup` endpoint to create
    an account, then `/auth/login` to get an access token. Include the token in the
    `Authorization` header as `Bearer <token>`.
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject standard security headers on every response."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'"
        )
        # HSTS — only enable when actually serving over TLS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# CORS configuration
_raw_origins = settings.ALLOWED_ORIGINS.strip()
if _raw_origins == "*":
    # Wildcard mode: no credentials allowed (per CORS spec)
    origins = ["*"]
    _allow_credentials = False
else:
    origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Enforce per-IP rate limits (stricter on auth endpoints)."""
    # Skip rate limiting for static assets — a single SPA page load
    # fetches many CSS/JS files and would exhaust the general budget.
    if request.url.path.startswith("/static"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()

    is_auth = request.url.path.startswith("/api/v1/auth")
    limit = _RATE_LIMIT_AUTH if is_auth else _RATE_LIMIT_GENERAL
    key = f"{client_ip}:{'auth' if is_auth else 'general'}"

    with _rate_lock:
        # Prune timestamps outside the window
        _rate_store[key] = [t for t in _rate_store[key] if now - t < _RATE_WINDOW]

        # Evict stale keys to bound memory usage
        if len(_rate_store) > _RATE_MAX_KEYS:
            stale = [k for k, v in _rate_store.items() if not v or (now - v[-1]) >= _RATE_WINDOW]
            for k in stale:
                del _rate_store[k]

        if len(_rate_store[key]) >= limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(_RATE_WINDOW)},
            )

        _rate_store[key].append(now)

    return await call_next(request)


# Include routers with API versioning
API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(trades_router, prefix=API_PREFIX)
app.include_router(analysis_router, prefix=API_PREFIX)
app.include_router(charts_router, prefix=API_PREFIX)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Static file serving for the web frontend
# ---------------------------------------------------------------------------
_STATIC_DIR = Path(__file__).parent / "static"

if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        """Serve the main SPA page."""
        return FileResponse(str(_STATIC_DIR / "index.html"))

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        """
        SPA catch-all: serve the requested file if it exists under /static,
        otherwise serve index.html so client-side routing can handle it.
        """
        # Don't intercept API or docs paths
        if path.startswith(("api/", "docs", "redoc", "openapi.json", "health")):
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        # Prevent path traversal: resolve and verify containment
        file_path = (_STATIC_DIR / path).resolve()
        static_root = _STATIC_DIR.resolve()
        if str(file_path).startswith(str(static_root)) and file_path.is_file():
            return FileResponse(str(file_path))

        return FileResponse(str(_STATIC_DIR / "index.html"))
else:

    @app.get("/")
    async def root():
        """Root endpoint - API information (no frontend deployed)."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "redoc": "/redoc",
            "api_prefix": API_PREFIX,
        }
