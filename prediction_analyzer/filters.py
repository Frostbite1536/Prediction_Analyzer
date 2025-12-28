# prediction_analyzer/filters.py
"""
Advanced filtering functions for trades
"""
from datetime import datetime, timedelta
from typing import List, Optional
from .trade_loader import Trade


def _normalize_datetime(dt) -> datetime:
    """
    Normalize a datetime value to a naive datetime for consistent comparison.
    Handles both timezone-aware and naive datetimes, and numeric timestamps.

    Args:
        dt: datetime object, pandas Timestamp, or numeric timestamp

    Returns:
        Naive datetime object
    """
    if dt is None:
        return None

    # Handle numeric timestamps (Unix epoch)
    if isinstance(dt, (int, float)):
        # Use UTC to avoid local timezone issues
        return datetime.utcfromtimestamp(dt)

    # Handle pandas Timestamp
    if hasattr(dt, 'to_pydatetime'):
        dt = dt.to_pydatetime()

    # Handle timezone-aware datetime - convert to naive (assume UTC)
    if isinstance(dt, datetime) and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)

    return dt


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

    # Parse start/end as naive datetimes (midnight on those days)
    start_dt = None
    end_dt = None

    if isinstance(start, str) and start:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
    elif isinstance(start, datetime):
        start_dt = _normalize_datetime(start)

    if isinstance(end, str) and end:
        # End date should include the entire day (up to midnight next day)
        end_dt = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
    elif isinstance(end, datetime):
        end_dt = _normalize_datetime(end)

    filtered = []
    for t in trades:
        # Normalize trade timestamp for comparison
        ts = _normalize_datetime(t.timestamp)
        if ts is None:
            continue

        if start_dt and ts < start_dt:
            continue
        if end_dt and ts > end_dt:
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
