# prediction_analyzer/providers/__init__.py
"""
Multi-market provider system for prediction market data.

Supports: Limitless Exchange, Polymarket, Kalshi, Manifold Markets.
"""
from .base import MarketProvider, ProviderRegistry
from .limitless import LimitlessProvider
from .polymarket import PolymarketProvider
from .kalshi import KalshiProvider
from .manifold import ManifoldProvider

# Auto-register all providers
ProviderRegistry.register(LimitlessProvider())
ProviderRegistry.register(PolymarketProvider())
ProviderRegistry.register(KalshiProvider())
ProviderRegistry.register(ManifoldProvider())

__all__ = [
    "MarketProvider",
    "ProviderRegistry",
    "LimitlessProvider",
    "PolymarketProvider",
    "KalshiProvider",
    "ManifoldProvider",
]
