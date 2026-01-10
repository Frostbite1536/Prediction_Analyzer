# prediction_analyzer/api/main.py
"""
FastAPI application - main entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
)

# CORS configuration
origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with API versioning
API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(trades_router, prefix=API_PREFIX)
app.include_router(analysis_router, prefix=API_PREFIX)
app.include_router(charts_router, prefix=API_PREFIX)


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    init_db()


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
