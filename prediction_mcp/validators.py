# prediction_mcp/validators.py
"""
Input validation helpers for MCP tool parameters.

Validates and normalizes tool inputs before passing them to the
core library functions. Raises InvalidFilterError for bad inputs.
"""

import math
from datetime import datetime
from typing import Optional, List, Dict

from prediction_analyzer.exceptions import InvalidFilterError, MarketNotFoundError

VALID_TRADE_TYPES = {"Buy", "Sell"}
VALID_SIDES = {"YES", "NO"}
VALID_CHART_TYPES = {"simple", "pro", "enhanced", "global"}
VALID_EXPORT_FORMATS = {"csv", "xlsx", "json"}
VALID_SORT_FIELDS = {"timestamp", "pnl", "cost"}
VALID_COST_BASIS_METHODS = {"fifo", "lifo", "average"}
VALID_SORT_ORDERS = {"asc", "desc"}

# Maps common LLM casing variants to canonical values
_TRADE_TYPE_NORMALIZE = {"buy": "Buy", "sell": "Sell"}
_SIDE_NORMALIZE = {"yes": "YES", "no": "NO"}


def validate_date(value: Optional[str], param_name: str) -> Optional[str]:
    """Validate a date string is in YYYY-MM-DD format."""
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        raise InvalidFilterError(f"Invalid {param_name}: '{value}'. Expected format: YYYY-MM-DD")


def validate_trade_types(types: Optional[List[str]]) -> Optional[List[str]]:
    """Validate and normalize trade type filter values.

    Accepts case-insensitive input (e.g. "buy" -> "Buy").
    """
    if types is None:
        return None
    normalized = [
        _TRADE_TYPE_NORMALIZE.get(t.lower(), t) if isinstance(t, str) else t for t in types
    ]
    invalid = [t for t in normalized if t not in VALID_TRADE_TYPES]
    if invalid:
        raise InvalidFilterError(
            f"Invalid trade types: {invalid}. Valid values: {sorted(VALID_TRADE_TYPES)}"
        )
    return normalized


def validate_sides(sides: Optional[List[str]]) -> Optional[List[str]]:
    """Validate and normalize side filter values.

    Accepts case-insensitive input (e.g. "yes" -> "YES").
    """
    if sides is None:
        return None
    normalized = [_SIDE_NORMALIZE.get(s.lower(), s) if isinstance(s, str) else s for s in sides]
    invalid = [s for s in normalized if s not in VALID_SIDES]
    if invalid:
        raise InvalidFilterError(f"Invalid sides: {invalid}. Valid values: {sorted(VALID_SIDES)}")
    return normalized


def validate_chart_type(chart_type: str) -> str:
    """Validate chart type parameter."""
    if chart_type not in VALID_CHART_TYPES:
        raise InvalidFilterError(
            f"Invalid chart type: '{chart_type}'. Valid values: {sorted(VALID_CHART_TYPES)}"
        )
    return chart_type


def validate_export_format(fmt: str) -> str:
    """Validate export format parameter."""
    if fmt not in VALID_EXPORT_FORMATS:
        raise InvalidFilterError(
            f"Invalid export format: '{fmt}'. Valid values: {sorted(VALID_EXPORT_FORMATS)}"
        )
    return fmt


def validate_positive_int(value: Optional[int], param_name: str) -> Optional[int]:
    """Validate that an integer parameter is positive."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise InvalidFilterError(
                f"Invalid {param_name}: {value}. Must be a positive integer, not NaN/Infinity."
            )
    if not isinstance(value, int) or value < 1:
        raise InvalidFilterError(f"Invalid {param_name}: {value}. Must be a positive integer.")
    return value


def validate_numeric(value: Optional[float], param_name: str) -> Optional[float]:
    """Validate a numeric parameter is finite (not NaN or Infinity)."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and (math.isnan(float(value)) or math.isinf(float(value))):
        raise InvalidFilterError(
            f"Invalid {param_name}: {value}. Must be a finite number, not NaN/Infinity."
        )
    return value


def validate_sort_order(order: str) -> str:
    """Validate sort order parameter."""
    normalized = order.lower() if isinstance(order, str) else order
    if normalized not in VALID_SORT_ORDERS:
        raise InvalidFilterError(
            f"Invalid sort order: '{order}'. Valid values: {sorted(VALID_SORT_ORDERS)}"
        )
    return normalized


def validate_cost_basis_method(method: str) -> str:
    """Validate cost basis method parameter."""
    if method not in VALID_COST_BASIS_METHODS:
        raise InvalidFilterError(
            f"Invalid cost basis method: '{method}'. "
            f"Valid values: {sorted(VALID_COST_BASIS_METHODS)}"
        )
    return method


def validate_sort_field(field: str) -> str:
    """Validate sort field parameter."""
    if field not in VALID_SORT_FIELDS:
        raise InvalidFilterError(
            f"Invalid sort field: '{field}'. Valid values: {sorted(VALID_SORT_FIELDS)}"
        )
    return field


def validate_market_slug(slug: str, available_markets: Dict[str, str]) -> str:
    """Validate a market slug exists in the available markets.

    Args:
        slug: The market slug to validate.
        available_markets: Dict mapping slug -> title from get_unique_markets().

    Raises:
        MarketNotFoundError with the list of available slugs (max 20).
    """
    if slug not in available_markets:
        available = sorted(available_markets.keys())[:20]
        raise MarketNotFoundError(
            f"Market '{slug}' not found. "
            f"Available markets ({len(available_markets)} total): {available}"
        )
    return slug
