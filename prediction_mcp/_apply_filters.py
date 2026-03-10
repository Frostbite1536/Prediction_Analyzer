# prediction_mcp/_apply_filters.py
"""
Shared filter application helper for MCP tool handlers.

Extracts common filter parameters from tool arguments and applies
them using the core library filter functions.
"""
from typing import List, Dict, Any

from prediction_analyzer.trade_loader import Trade
from prediction_analyzer.exceptions import InvalidFilterError
from prediction_analyzer.filters import filter_by_date, filter_by_trade_type, filter_by_side, filter_by_pnl
from prediction_analyzer.trade_filter import filter_trades_by_market_slug

from .validators import validate_date, validate_trade_types, validate_sides, validate_numeric


def apply_filters(trades: List[Trade], arguments: Dict[str, Any]) -> List[Trade]:
    """
    Apply filter parameters from tool arguments to a list of trades.

    Supported argument keys:
        start_date, end_date, trade_types, sides, min_pnl, max_pnl, market_slug

    Args:
        trades: List of Trade objects to filter
        arguments: Tool arguments dictionary

    Returns:
        Filtered list of Trade objects
    """
    result = trades

    # Market filter
    market_slug = arguments.get("market_slug")
    if market_slug:
        result = filter_trades_by_market_slug(result, market_slug)

    # Date filter
    start_date = validate_date(arguments.get("start_date"), "start_date")
    end_date = validate_date(arguments.get("end_date"), "end_date")
    if start_date or end_date:
        result = filter_by_date(result, start=start_date, end=end_date)

    # Trade type filter
    trade_types = validate_trade_types(arguments.get("trade_types"))
    if trade_types:
        result = filter_by_trade_type(result, types=trade_types)

    # Side filter
    sides = validate_sides(arguments.get("sides"))
    if sides:
        result = filter_by_side(result, sides=sides)

    # PnL filter (guard against NaN/Infinity — comparisons with NaN are always
    # False, which would silently return all trades instead of filtering)
    min_pnl = validate_numeric(arguments.get("min_pnl"), "min_pnl")
    max_pnl = validate_numeric(arguments.get("max_pnl"), "max_pnl")
    if min_pnl is not None and max_pnl is not None and min_pnl > max_pnl:
        raise InvalidFilterError(
            f"min_pnl ({min_pnl}) must not exceed max_pnl ({max_pnl})"
        )
    if min_pnl is not None or max_pnl is not None:
        result = filter_by_pnl(result, min_pnl=min_pnl, max_pnl=max_pnl)

    return result
