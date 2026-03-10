# prediction_mcp/tools/data_tools.py
"""
Data loading and market listing tools.

Tools: load_trades, fetch_trades, list_markets, get_trade_details
"""
import json
import logging
import os
import tempfile

from mcp import types

from prediction_analyzer.trade_loader import load_trades as _load_trades
from prediction_analyzer.trade_filter import get_unique_markets, filter_trades_by_market_slug
from prediction_analyzer.utils.data import fetch_trade_history
from prediction_analyzer.exceptions import TradeLoadError, NoTradesError, MarketNotFoundError, InvalidFilterError

from ..state import session
from ..errors import error_result, safe_tool
from ..serializers import to_json_text, serialize_trades
from ..validators import validate_sort_field, validate_positive_int

logger = logging.getLogger(__name__)


def get_tool_definitions() -> list[types.Tool]:
    """Return tool definitions for data tools."""
    return [
        types.Tool(
            name="load_trades",
            description=(
                "Load prediction market trades from a file (JSON, CSV, or XLSX). "
                "The loaded trades are stored in session memory for subsequent analysis. "
                "Call this before using any analysis, chart, or export tools."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the trades file (JSON, CSV, or XLSX)",
                    },
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="fetch_trades",
            description=(
                "Fetch trades from Limitless Exchange API using an API key. "
                "Downloads full trade history and stores in session memory. "
                "API keys start with 'lmts_'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": 'Limitless API key (starts with "lmts_")',
                    },
                    "page_limit": {
                        "type": "integer",
                        "description": "Max trades per page (default 100)",
                        "default": 100,
                    },
                },
                "required": ["api_key"],
            },
        ),
        types.Tool(
            name="list_markets",
            description=(
                "List all unique prediction markets in the currently loaded trades. "
                "Returns market slugs, titles, and trade counts. "
                "Trades must be loaded first with 'load_trades' or 'fetch_trades'."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_trade_details",
            description=(
                "Get detailed information about individual trades, optionally filtered by market. "
                "Supports pagination and sorting by timestamp, pnl, or cost."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "market_slug": {
                        "type": "string",
                        "description": "Filter by market (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max trades to return (default 50)",
                        "default": 50,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Pagination offset (default 0)",
                        "default": 0,
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["timestamp", "pnl", "cost"],
                        "description": "Sort field (default timestamp)",
                        "default": "timestamp",
                    },
                    "sort_order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "description": "Sort order (default desc)",
                        "default": "desc",
                    },
                },
            },
        ),
    ]


async def handle_tool(name: str, arguments: dict):
    """Handle data tool calls. Returns content list or None if not handled."""
    if name == "load_trades":
        return await _handle_load_trades(arguments)
    elif name == "fetch_trades":
        return await _handle_fetch_trades(arguments)
    elif name == "list_markets":
        return await _handle_list_markets(arguments)
    elif name == "get_trade_details":
        return await _handle_get_trade_details(arguments)
    return None


@safe_tool
async def _handle_load_trades(arguments: dict):
    file_path = arguments.get("file_path")
    if not file_path:
        return error_result(ValueError("file_path is required")).content

    if not os.path.isfile(file_path):
        raise TradeLoadError(f"File not found: {file_path}")

    trades = _load_trades(file_path)
    session.trades = trades
    session.filtered_trades = list(trades)
    session.active_filters.clear()
    session.source = f"file:{file_path}"

    markets = get_unique_markets(trades)
    result = {
        "trade_count": len(trades),
        "markets": sorted(markets.values()),
        "source": session.source,
    }
    return [types.TextContent(type="text", text=to_json_text(result))]


@safe_tool
async def _handle_fetch_trades(arguments: dict):
    api_key = arguments.get("api_key", "")
    page_limit = arguments.get("page_limit", 100)

    if not api_key:
        return error_result(ValueError("api_key is required")).content

    raw_trades = fetch_trade_history(api_key, page_limit=page_limit)

    if not raw_trades:
        raise TradeLoadError("No trades returned from API")

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(raw_trades, tmp, default=str)
    tmp.close()

    try:
        trades = _load_trades(tmp.name)
    finally:
        os.unlink(tmp.name)

    session.trades = trades
    session.filtered_trades = list(trades)
    session.active_filters.clear()
    key_prefix = api_key[:8] + "..." if len(api_key) > 8 else api_key
    session.source = f"api:{key_prefix}"

    markets = get_unique_markets(trades)
    result = {
        "trade_count": len(trades),
        "markets": sorted(markets.values()),
        "source": session.source,
    }
    return [types.TextContent(type="text", text=to_json_text(result))]


@safe_tool
async def _handle_list_markets(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    markets = get_unique_markets(session.trades)

    result = []
    for slug, title in sorted(markets.items()):
        trade_count = len(filter_trades_by_market_slug(session.trades, slug))
        result.append({
            "slug": slug,
            "title": title,
            "trade_count": trade_count,
        })

    return [types.TextContent(type="text", text=to_json_text(result))]


@safe_tool
async def _handle_get_trade_details(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    market_slug = arguments.get("market_slug")
    limit = validate_positive_int(arguments.get("limit", 50), "limit") or 50
    offset = arguments.get("offset", 0)
    if offset is not None and (not isinstance(offset, int) or offset < 0):
        raise InvalidFilterError(f"Invalid offset: {offset}. Must be a non-negative integer.")
    sort_by = validate_sort_field(arguments.get("sort_by", "timestamp"))
    sort_order = arguments.get("sort_order", "desc")

    trades = session.filtered_trades
    if market_slug:
        trades = filter_trades_by_market_slug(trades, market_slug)
        if not trades:
            raise MarketNotFoundError(f"No trades found for market: {market_slug}")

    reverse = sort_order == "desc"
    trades = sorted(trades, key=lambda t: getattr(t, sort_by, 0), reverse=reverse)

    total = len(trades)
    trades = trades[offset:offset + limit]

    result = {
        "trades": serialize_trades(trades),
        "total": total,
        "limit": limit,
        "offset": offset,
    }
    return [types.TextContent(type="text", text=to_json_text(result))]
