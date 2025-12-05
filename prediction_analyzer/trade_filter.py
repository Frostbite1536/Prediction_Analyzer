# prediction_analyzer/trade_filter.py
"""
Trade filtering and deduplication utilities
"""
from typing import List
from difflib import get_close_matches
from .trade_loader import Trade

def filter_trades(trades: List[Trade], market_name: str, fuzzy: bool = True) -> List[Trade]:
    """
    Filter trades by market name with optional fuzzy matching

    Args:
        trades: List of Trade objects
        market_name: Market name or slug to filter by
        fuzzy: Enable fuzzy string matching

    Returns:
        Filtered list of trades
    """
    if fuzzy:
        market_names = list({t.market for t in trades})
        market_slugs = list({t.market_slug for t in trades})

        # Try matching on both market name and slug
        name_matches = get_close_matches(market_name, market_names, n=1, cutoff=0.6)
        slug_matches = get_close_matches(market_name, market_slugs, n=1, cutoff=0.6)

        if name_matches:
            target = name_matches[0]
            return [t for t in trades if t.market == target]
        elif slug_matches:
            target = slug_matches[0]
            return [t for t in trades if t.market_slug == target]
        else:
            return []

    # Exact match on either field
    filtered = [t for t in trades if t.market == market_name or t.market_slug == market_name]
    return filtered

def filter_trades_by_market_slug(trades: List[Trade], market_slug: str) -> List[Trade]:
    """Filter trades by exact market slug match"""
    return [t for t in trades if t.market_slug == market_slug]

def deduplicate_trades(trades: List[Trade]) -> List[Trade]:
    """
    Remove exact duplicate trades based on unique identifiers
    """
    seen = set()
    unique_trades = []

    for t in trades:
        # Create identifier from key fields
        identifier = (
            t.market_slug,
            t.timestamp.isoformat() if hasattr(t.timestamp, 'isoformat') else str(t.timestamp),
            t.price,
            t.shares,
            t.type,
            t.side
        )

        if identifier not in seen:
            seen.add(identifier)
            unique_trades.append(t)

    return unique_trades

def get_unique_markets(trades: List[Trade]) -> dict:
    """
    Get a dictionary of unique markets from trades

    Returns:
        Dict mapping market_slug -> market_title
    """
    markets = {}
    for t in trades:
        if t.market_slug and t.market:
            markets[t.market_slug] = t.market
    return markets
