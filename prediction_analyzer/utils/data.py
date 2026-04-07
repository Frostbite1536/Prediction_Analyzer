# prediction_analyzer/utils/data.py
"""
Data fetching utilities for Limitless Exchange API.

.. deprecated::
    This module delegates to :class:`LimitlessProvider` from the providers
    package.  Import directly from ``prediction_analyzer.providers`` instead.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def fetch_trade_history(api_key: str, page_limit: int = 100) -> List[dict]:
    """Fetch trade history from the Limitless Exchange API.

    Returns raw dicts (not Trade objects) for backward compatibility with
    callers that expect JSON-serialisable data.
    """
    from ..providers import ProviderRegistry

    provider = ProviderRegistry.get("limitless")
    trades = provider.fetch_trades(api_key, page_limit=page_limit)

    # Convert Trade dataclass objects back to dicts for legacy callers
    return [
        {
            "market": {"title": t.market, "slug": t.market_slug},
            "timestamp": t.timestamp.isoformat(),
            "price": t.price,
            "shares": t.shares,
            "cost": t.cost,
            "type": t.type,
            "side": t.side,
            "pnl": t.pnl,
            "tx_hash": t.tx_hash,
            "source": t.source,
            "currency": t.currency,
        }
        for t in trades
    ]


def fetch_market_details(market_slug: str) -> Optional[dict]:
    """Fetch live market details from API (public endpoint, no auth required)."""
    from ..providers import ProviderRegistry

    provider = ProviderRegistry.get("limitless")
    return provider.fetch_market_details(market_slug)
