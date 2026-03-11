# prediction_analyzer/providers/base.py
"""
Abstract base class for prediction market data providers and provider registry.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ..trade_loader import Trade

logger = logging.getLogger(__name__)


class MarketProvider(ABC):
    """Base class for prediction market data providers."""

    name: str  # e.g. "polymarket"
    display_name: str  # e.g. "Polymarket"
    api_key_prefix: str  # e.g. "poly_", "kalshi_", "lmts_"
    currency: str = "USD"

    @abstractmethod
    def fetch_trades(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        """Fetch user's trade history from this market."""
        ...

    @abstractmethod
    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch details for a specific market."""
        ...

    @abstractmethod
    def normalize_trade(self, raw: dict, **kwargs) -> Trade:
        """Convert a raw API response dict into a Trade object."""
        ...

    def detect_api_key(self, api_key: str) -> bool:
        """Check if an API key belongs to this provider."""
        return api_key.startswith(self.api_key_prefix)

    @abstractmethod
    def detect_file_format(self, records: List[dict]) -> bool:
        """Check if a list of raw dicts matches this provider's format."""
        ...


class ProviderRegistry:
    """Registry for market providers. Auto-detects provider from API key or file format."""

    _providers: Dict[str, MarketProvider] = {}

    @classmethod
    def register(cls, provider: MarketProvider):
        cls._providers[provider.name] = provider

    @classmethod
    def get(cls, name: str) -> MarketProvider:
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}. Available: {list(cls._providers.keys())}")
        return cls._providers[name]

    @classmethod
    def detect_from_key(cls, api_key: str) -> Optional[MarketProvider]:
        """Auto-detect provider from API key prefix."""
        for provider in cls._providers.values():
            if provider.detect_api_key(api_key):
                return provider
        return None

    @classmethod
    def detect_from_file(cls, records: List[dict]) -> Optional[MarketProvider]:
        """Auto-detect provider from file record format."""
        for provider in cls._providers.values():
            if provider.detect_file_format(records):
                return provider
        return None

    @classmethod
    def all(cls) -> List[MarketProvider]:
        return list(cls._providers.values())

    @classmethod
    def names(cls) -> List[str]:
        return list(cls._providers.keys())
