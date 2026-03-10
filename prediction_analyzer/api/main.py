# prediction_analyzer/api/main.py
"""
FastAPI application - main entry point
"""
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
_rate_store: dict = defaultdict(list)  # ip -> list of timestamps
_RATE_LIMIT_AUTH = 5       # max requests per window on /auth/*
_RATE_LIMIT_GENERAL = 60   # max requests per window on all other endpoints
_RATE_WINDOW = 60          # window size in seconds


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
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Enforce per-IP rate limits (stricter on auth endpoints)."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()

    is_auth = request.url.path.startswith("/api/v1/auth")
    limit = _RATE_LIMIT_AUTH if is_auth else _RATE_LIMIT_GENERAL
    key = f"{client_ip}:{'auth' if is_auth else 'general'}"

    # Prune timestamps outside the window
    _rate_store[key] = [t for t in _rate_store[key] if now - t < _RATE_WINDOW]

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


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "api_prefix": API_PREFIX
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
