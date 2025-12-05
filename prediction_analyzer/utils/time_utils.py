# prediction_analyzer/utils/time_utils.py
"""
Time and date utility functions
"""
from datetime import datetime, timedelta
from typing import Optional

def parse_date(date_str: str) -> datetime:
    """
    Parse date string in various formats

    Args:
        date_str: Date string (YYYY-MM-DD, YYYY/MM/DD, etc.)

    Returns:
        datetime object
    """
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date: {date_str}")

def format_timestamp(timestamp: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format timestamp to string

    Args:
        timestamp: datetime object
        fmt: strftime format string

    Returns:
        Formatted date string
    """
    return timestamp.strftime(fmt)

def get_date_range(days_back: int) -> tuple:
    """
    Get a date range from N days ago to now

    Args:
        days_back: Number of days to go back

    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    return start_date, end_date
