# prediction_analyzer/filters.py
"""
Advanced filtering functions for trades
"""
import math
from datetime import datetime, timedelta, timezone
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
        return datetime.fromtimestamp(dt, tz=timezone.utc).replace(tzinfo=None)

    # Handle pandas Timestamp
    if hasattr(dt, 'to_pydatetime'):
        dt = dt.to_pydatetime()

    # Handle timezone-aware datetime - convert to UTC then strip tzinfo
    if isinstance(dt, datetime) and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

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
        # End date should include the entire day (use strict less-than midnight next day)
        end_dt = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
    elif isinstance(end, datetime):
        # Add 1 day for consistency with string behavior (entire day inclusive)
        end_dt = _normalize_datetime(end) + timedelta(days=1)

    filtered = []
    for t in trades:
        # Normalize trade timestamp for comparison
        ts = _normalize_datetime(t.timestamp)
        if ts is None:
            continue

        if start_dt and ts < start_dt:
            continue
        if end_dt and ts >= end_dt:
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
    # Match variant types: "Buy" also matches "Market Buy", "Limit Buy", etc.
    # Use word-boundary check to avoid matching "Buyback" when filtering for "Buy"
    def _matches(trade_type: str) -> bool:
        if trade_type in types:
            return True
        for base in types:
            # Match "Market Buy", "Limit Buy" etc. but not "Rebuy"
            if trade_type.endswith(" " + base) or trade_type.startswith(base + " "):
                return True
        return False
    return [t for t in trades if _matches(t.type)]

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
        min_pnl: Minimum PnL threshold (must be finite)
        max_pnl: Maximum PnL threshold (must be finite)

    Returns:
        Filtered list of trades

    Raises:
        ValueError: If min_pnl or max_pnl is NaN or Infinity
    """
    # Guard against NaN/Infinity: comparisons with NaN always return False,
    # which would silently return all trades instead of filtering.
    for name, val in [("min_pnl", min_pnl), ("max_pnl", max_pnl)]:
        if val is not None and isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            raise ValueError(f"{name} must be a finite number, got {val}")

    filtered = []
    for t in trades:
        pnl = t.pnl
        if min_pnl is not None and pnl < min_pnl:
            continue
        if max_pnl is not None and pnl > max_pnl:
            continue
        filtered.append(t)
    return filtered
