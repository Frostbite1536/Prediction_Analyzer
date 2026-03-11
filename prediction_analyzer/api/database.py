# prediction_analyzer/api/database.py
"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

from .config import get_settings

settings = get_settings()

# Resolve data directory relative to the project root (parent of prediction_analyzer package)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_db_url = settings.DATABASE_URL

# For SQLite relative paths, anchor to the project root instead of CWD
if _db_url.startswith("sqlite:///./"):
    _relative_path = _db_url.replace("sqlite:///./", "")
    _abs_path = _PROJECT_ROOT / _relative_path
    _abs_path.parent.mkdir(parents=True, exist_ok=True)
    _db_url = f"sqlite:///{_abs_path}"
elif _db_url.startswith("sqlite:///") and not Path(_db_url.replace("sqlite:///", "")).is_absolute():
    _relative_path = _db_url.replace("sqlite:///", "")
    _abs_path = _PROJECT_ROOT / _relative_path
    _abs_path.parent.mkdir(parents=True, exist_ok=True)
    _db_url = f"sqlite:///{_abs_path}"

# Create SQLAlchemy engine
engine = create_engine(_db_url, connect_args={"check_same_thread": False})  # SQLite specific

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def init_db():
    """Initialize database - create all tables"""
    from .models import user, trade, analysis  # noqa: F401 - Import models to register them

    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency that provides a database session.
    Yields a session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
