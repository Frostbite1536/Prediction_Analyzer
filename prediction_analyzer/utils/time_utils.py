# prediction_analyzer/utils/time_utils.py
"""
Time and date utility functions
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Union, Any

import pandas as pd

logger = logging.getLogger(__name__)


def parse_timestamp(value: Union[int, float, str, "datetime", Any]) -> datetime:
    """Parse timestamp from various formats into a timezone-naive UTC datetime."""
    if value is None or (isinstance(value, (int, float)) and value == 0):
        return datetime(1970, 1, 1)

    # If it's already a datetime, convert to naive UTC
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    # If it's a pandas Timestamp
    if hasattr(value, "to_pydatetime"):
        dt = value.to_pydatetime()
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    # Try to parse as string first (RFC 3339, ISO 8601)
    if isinstance(value, str):
        try:
            # Handle RFC 3339/ISO 8601 format (e.g., "2024-01-15T10:30:00Z")
            # Replace 'Z' with '+00:00' for fromisoformat compatibility
            clean_value = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_value)
            # Convert to naive UTC
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            pass

        # Try parsing as numeric string
        try:
            numeric_value = float(value)
            # If it's a large number, assume milliseconds
            if numeric_value > 1e12:
                return datetime.fromtimestamp(
                    numeric_value / 1000, tz=timezone.utc
                ).replace(tzinfo=None)
            return datetime.fromtimestamp(numeric_value, tz=timezone.utc).replace(
                tzinfo=None
            )
        except ValueError:
            pass

    # Handle numeric timestamps
    if isinstance(value, (int, float)):
        # If it's a very large number, assume milliseconds
        if value > 1e12:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).replace(
                tzinfo=None
            )
        return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)

    # Fallback: try pandas parsing
    try:
        result = pd.to_datetime(value, utc=True)
        if hasattr(result, "to_pydatetime"):
            dt = result.to_pydatetime()
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        return result
    except Exception:
        logger.warning(
            "Could not parse timestamp value %r; defaulting to epoch", value
        )
        return datetime(1970, 1, 1)


def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats (YYYY-MM-DD, YYYY/MM/DD, etc.)."""
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%m-%d-%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date: {date_str}")


def format_timestamp(timestamp: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp to string using the given strftime format."""
    return timestamp.strftime(fmt)


def get_date_range(days_back: int) -> tuple:
    """Return (start_date, end_date) tuple spanning N days back to now."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    return start_date, end_date
