# prediction_analyzer/filters.py
"""
Advanced filtering functions for trades
"""
from datetime import datetime
from typing import List, Optional
from .trade_loader import Trade

def filter_by_date(trades: List[Trade], start: Optional[str] = None, end: Optional[str] = None) -> List[Trade]:
    """
    Filter trades between start and end dates

    Args:
        trades: List of Trade objects
        start: Start date as 'YYYY-MM-DD' string
        end: End date as 'YYYY-MM-DD' string

    Returns:
        Filtered list of trades
    """
    if not start and not end:
        return trades

    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d")
    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d")

    filtered = []
    for t in trades:
        ts = t.timestamp if isinstance(t.timestamp, datetime) else datetime.fromtimestamp(t.timestamp)
        if start and ts < start:
            continue
        if end and ts > end:
            continue
        filtered.append(t)
    return filtered

def filter_by_trade_type(trades: List[Trade], types: Optional[List[str]] = None) -> List[Trade]:
    """
    Filter trades by type (Buy/Sell)

    Args:
        trades: List of Trade objects
        types: List of trade types to include ['Buy', 'Sell']

    Returns:
        Filtered list of trades
    """
    if not types:
        return trades
    return [t for t in trades if t.type in types]

def filter_by_side(trades: List[Trade], sides: Optional[List[str]] = None) -> List[Trade]:
    """
    Filter trades by side (YES/NO)

    Args:
        trades: List of Trade objects
        sides: List of sides to include ['YES', 'NO']

    Returns:
        Filtered list of trades
    """
    if not sides:
        return trades
    return [t for t in trades if t.side in sides]

def filter_by_pnl(trades: List[Trade], min_pnl: Optional[float] = None, max_pnl: Optional[float] = None) -> List[Trade]:
    """
    Filter trades by PnL thresholds

    Args:
        trades: List of Trade objects
        min_pnl: Minimum PnL threshold
        max_pnl: Maximum PnL threshold

    Returns:
        Filtered list of trades
    """
    filtered = []
    for t in trades:
        pnl = t.pnl
        if min_pnl is not None and pnl < min_pnl:
            continue
        if max_pnl is not None and pnl > max_pnl:
            continue
        filtered.append(t)
    return filtered
