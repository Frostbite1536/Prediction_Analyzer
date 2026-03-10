# prediction_analyzer/utils/auth.py
"""
Authentication utilities for prediction market APIs.

Supports multiple providers:
  - Limitless Exchange: API key (lmts_...) via X-API-Key header
  - Polymarket: wallet address (0x...) — no auth needed for public Data API
  - Kalshi: RSA key pair — per-request RSA-PSS signing
  - Manifold Markets: API key (manifold_...) via "Authorization: Key ..." header
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Environment variable names per provider
_ENV_MAP = {
    "limitless": "LIMITLESS_API_KEY",
    "polymarket": "POLYMARKET_WALLET",
    "kalshi": "KALSHI_API_KEY_ID",
    "manifold": "MANIFOLD_API_KEY",
}


def get_api_key(api_key: Optional[str] = None, provider: str = "limitless") -> Optional[str]:
    """
    Resolve an API key from the provided argument or environment variable.

    Args:
        api_key: Explicit API key, or None to read from environment.
        provider: Provider name for env var lookup (default: "limitless").

    Returns:
        The API key string, or None if not found.
    """
    if api_key:
        return api_key.strip() or None

    env_var = _ENV_MAP.get(provider, f"{provider.upper()}_API_KEY")
    key = os.environ.get(env_var, "")
    return key.strip() or None


def get_auth_headers(api_key: str) -> dict:
    """
    Build authentication headers for Limitless Exchange API requests.

    For other providers, use the provider's own auth mechanism via the
    provider classes in prediction_analyzer.providers.

    Args:
        api_key: Limitless API key (lmts_...)

    Returns:
        Dict of headers for Limitless API requests.
    """
    return {"X-API-Key": api_key}


def detect_provider_from_key(api_key: str) -> str:
    """Detect provider name from API key format.

    Returns:
        Provider name string: "limitless", "polymarket", "kalshi", or "manifold".
    """
    if not api_key:
        return "limitless"
    if api_key.startswith("lmts_"):
        return "limitless"
    elif api_key.startswith("0x"):
        return "polymarket"
    elif api_key.startswith("kalshi_"):
        return "kalshi"
    elif api_key.startswith("manifold_"):
        return "manifold"
    return "limitless"  # Default fallback
