# prediction_analyzer/utils/auth.py
"""
Authentication utilities for Limitless Exchange API access.

Uses API key authentication (X-API-Key header).
API keys can be generated at limitless.exchange -> profile -> Api keys.
Keys use the format: lmts_...
"""
import os


def get_api_key(api_key: str | None = None) -> str | None:
    """
    Resolve an API key from the provided argument or environment variable.

    Args:
        api_key: Explicit API key, or None to read from LIMITLESS_API_KEY env var.

    Returns:
        The API key string, or None if not found.
    """
    key = api_key or os.environ.get("LIMITLESS_API_KEY")
    if key:
        key = key.strip()
    return key or None


def get_auth_headers(api_key: str) -> dict:
    """
    Build the authentication headers for Limitless Exchange API requests.

    Args:
        api_key: Limitless API key (lmts_...)

    Returns:
        Dict of headers to include on every authenticated request.
    """
    return {"X-API-Key": api_key}
