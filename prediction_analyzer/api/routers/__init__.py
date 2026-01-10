# prediction_analyzer/api/routers/__init__.py
"""
API route handlers
"""
from .auth import router as auth_router
from .users import router as users_router
from .trades import router as trades_router
from .analysis import router as analysis_router
from .charts import router as charts_router

__all__ = [
    "auth_router",
    "users_router",
    "trades_router",
    "analysis_router",
    "charts_router",
]
