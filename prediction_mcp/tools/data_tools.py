from __future__ import annotations

# prediction_mcp/tools/data_tools.py
"""
Data loading and market listing tools.

Tools: load_trades, fetch_trades, list_markets, get_trade_details
"""
import logging
import os

from mcp import types

from prediction_analyzer.trade_loader import load_trades as _load_trades
from prediction_analyzer.trade_filter import get_unique_markets, filter_trades_by_market_slug
from prediction_analyzer.exceptions import TradeLoadError, NoTradesError, InvalidFilterError

from ..state import session
from ..errors import error_result, safe_tool
from ..serializers import to_json_text, serialize_trades
from ..validators import validate_sort_field, validate_sort_order, validate_positive_int, validate_market_slug

logger = logging.getLogger(__name__)


def get_tool_definitions() -> list[types.Tool]:
    """Return tool definitions for data tools."""
    return [
        types.Tool(
            name="load_trades",
            description=(
                "Load prediction market trades from a file (JSON, CSV, or XLSX). "
                "Auto-detects provider format (Limitless, Polymarket, Kalshi, Manifold). "
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
                "Fetch trades from a prediction market API. "
                "Supports Limitless (lmts_...), Polymarket (0x...), "
                "Kalshi (kalshi_...), and Manifold (manifold_...). "
                "Provider is auto-detected from key format, or specify explicitly."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": (
                            "API key or credential. Format varies by provider: "
                            "Limitless: lmts_..., Polymarket: 0x... (wallet address), "
                            "Kalshi: kalshi_<KEY_ID>:<PEM_PATH>, Manifold: manifold_..."
                        ),
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["auto", "limitless", "polymarket", "kalshi", "manifold"],
                        "description": "Provider name or 'auto' to detect from key format (default: auto)",
                        "default": "auto",
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
                "Returns market slugs, titles, trade counts, and source providers. "
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
                "Supports pagination and sorting by timestamp, pnl, or cost. "
                "Returns {trades: [...], total: int, limit: int, offset: int}."
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

    # Detect sources from loaded trades
    loaded_sources = list({t.source for t in trades})
    for src in loaded_sources:
        if src not in session.sources:
            session.sources.append(src)

    markets = get_unique_markets(trades)
    result = {
        "trade_count": len(trades),
        "markets": sorted(markets.values()),
        "sources": session.sources,
    }
    return [types.TextContent(type="text", text=to_json_text(result))]


@safe_tool
async def _handle_fetch_trades(arguments: dict):
    api_key = arguments.get("api_key", "")
    provider_name = arguments.get("provider", "auto")
    page_limit = arguments.get("page_limit", 100)

    if not api_key:
        return error_result(ValueError("api_key is required")).content

    from prediction_analyzer.providers import ProviderRegistry

    # Resolve provider
    if provider_name == "auto":
        provider = ProviderRegistry.detect_from_key(api_key)
        if not provider:
            # Fall back to legacy Limitless path
            provider = ProviderRegistry.get("limitless")
    else:
        provider = ProviderRegistry.get(provider_name)

    # Use provider to fetch trades directly (no temp file needed)
    trades = provider.fetch_trades(api_key, page_limit=page_limit)

    if not trades:
        raise TradeLoadError(f"No trades returned from {provider.display_name} API")

    # Apply PnL computation for providers that don't supply it
    if provider.name in ("kalshi", "manifold", "polymarket"):
        from prediction_analyzer.providers.pnl_calculator import compute_realized_pnl
        trades = compute_realized_pnl(trades)

    # Deduplicate by tx_hash to prevent inflation on repeated fetches
    existing_hashes = {t.tx_hash for t in session.trades if t.tx_hash}
    new_trades = [t for t in trades if not t.tx_hash or t.tx_hash not in existing_hashes]
    session.trades.extend(new_trades)
    session.filtered_trades = list(session.trades)
    session.active_filters.clear()
    if provider.name not in session.sources:
        session.sources.append(provider.name)

    key_prefix = api_key[:10] + "..." if len(api_key) > 10 else api_key
    session.source = f"api:{provider.name}:{key_prefix}"

    markets = get_unique_markets(trades)
    result = {
        "trade_count": len(trades),
        "total_session_trades": len(session.trades),
        "markets": sorted(markets.values()),
        "provider": provider.name,
        "sources": session.sources,
    }
    return [types.TextContent(type="text", text=to_json_text(result))]


@safe_tool
async def _handle_list_markets(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    markets = get_unique_markets(session.trades)

    result = []
    for slug, title in sorted(markets.items()):
        market_trades = filter_trades_by_market_slug(session.trades, slug)
        sources = list({t.source for t in market_trades})
        result.append({
            "slug": slug,
            "title": title,
            "trade_count": len(market_trades),
            "sources": sources,
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
    sort_order = validate_sort_order(arguments.get("sort_order", "desc"))

    trades = session.filtered_trades
    if market_slug:
        validate_market_slug(market_slug, get_unique_markets(session.trades))
        trades = filter_trades_by_market_slug(trades, market_slug)

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
