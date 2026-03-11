from __future__ import annotations

# prediction_mcp/tools/analysis_tools.py
"""
Analysis tools for PnL summaries and metrics.

Tools: get_global_summary, get_market_summary, get_advanced_metrics, get_market_breakdown
"""
import logging

from mcp import types

from prediction_analyzer.pnl import (
    calculate_global_pnl_summary,
    calculate_market_pnl_summary,
    calculate_market_pnl,
)
from prediction_analyzer.metrics import calculate_advanced_metrics
from prediction_analyzer.trade_filter import filter_trades_by_market_slug, get_unique_markets
from prediction_analyzer.exceptions import NoTradesError

from ..state import session
from ..errors import safe_tool
from ..serializers import to_json_text, sanitize_dict
from .._apply_filters import apply_filters
from ..validators import validate_market_slug

logger = logging.getLogger(__name__)

_FILTER_PROPERTIES = {
    "start_date": {
        "type": "string",
        "description": "Filter start date (YYYY-MM-DD)",
    },
    "end_date": {
        "type": "string",
        "description": "Filter end date (YYYY-MM-DD)",
    },
    "trade_types": {
        "type": "array",
        "items": {"type": "string", "enum": ["Buy", "Sell"]},
        "description": "Filter by trade type",
    },
    "sides": {
        "type": "array",
        "items": {"type": "string", "enum": ["YES", "NO"]},
        "description": "Filter by side",
    },
    "min_pnl": {
        "type": "number",
        "description": "Minimum PnL threshold",
    },
    "max_pnl": {
        "type": "number",
        "description": "Maximum PnL threshold",
    },
}


def get_tool_definitions() -> list[types.Tool]:
    """Return tool definitions for analysis tools."""
    return [
        types.Tool(
            name="get_global_summary",
            description=(
                "Calculate overall PnL summary across all loaded trades. "
                "Returns total trades, total PnL, win rate, ROI, and more. "
                "Optional filters can narrow the analysis."
            ),
            inputSchema={
                "type": "object",
                "properties": _FILTER_PROPERTIES,
            },
        ),
        types.Tool(
            name="get_market_summary",
            description=(
                "Calculate PnL summary for a specific prediction market. "
                "Returns market-specific stats including title, outcome, and ROI. "
                "Use 'list_markets' first to get available market slugs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "market_slug": {
                        "type": "string",
                        "description": "Market identifier slug (from list_markets)",
                    },
                    **_FILTER_PROPERTIES,
                },
                "required": ["market_slug"],
            },
        ),
        types.Tool(
            name="get_advanced_metrics",
            description=(
                "Calculate risk-adjusted trading metrics: Sharpe ratio, Sortino ratio, "
                "max drawdown, profit factor, expectancy, win/loss streaks, and volume stats. "
                "Optionally limited to a specific market."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "market_slug": {
                        "type": "string",
                        "description": "Limit to specific market (optional)",
                    },
                    **_FILTER_PROPERTIES,
                },
            },
        ),
        types.Tool(
            name="get_market_breakdown",
            description=(
                "Get PnL breakdown by market showing which markets are profitable. "
                "Returns per-market trade count, PnL, and volume."
            ),
            inputSchema={
                "type": "object",
                "properties": _FILTER_PROPERTIES,
            },
        ),
        types.Tool(
            name="get_provider_breakdown",
            description=(
                "Get PnL breakdown by prediction market provider. "
                "Shows per-provider trade count, total PnL, and currency. "
                "Useful when trades from multiple providers are loaded."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


async def handle_tool(name: str, arguments: dict):
    """Handle analysis tool calls. Returns content list or None if not handled."""
    if name == "get_global_summary":
        return await _handle_global_summary(arguments)
    elif name == "get_market_summary":
        return await _handle_market_summary(arguments)
    elif name == "get_advanced_metrics":
        return await _handle_advanced_metrics(arguments)
    elif name == "get_market_breakdown":
        return await _handle_market_breakdown(arguments)
    elif name == "get_provider_breakdown":
        return await _handle_provider_breakdown(arguments)
    return None


@safe_tool
async def _handle_global_summary(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    trades = apply_filters(session.trades, arguments)
    summary = calculate_global_pnl_summary(trades)
    return [types.TextContent(type="text", text=to_json_text(sanitize_dict(summary)))]


@safe_tool
async def _handle_market_summary(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    market_slug = arguments.get("market_slug")
    if not market_slug:
        raise ValueError("market_slug is required")

    validate_market_slug(market_slug, get_unique_markets(session.trades))
    market_trades = filter_trades_by_market_slug(session.trades, market_slug)

    trades = apply_filters(market_trades, arguments)
    if not trades:
        raise NoTradesError("No trades match the applied filters")

    summary = calculate_market_pnl_summary(trades)
    return [types.TextContent(type="text", text=to_json_text(sanitize_dict(summary)))]


@safe_tool
async def _handle_advanced_metrics(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    trades = session.trades
    market_slug = arguments.get("market_slug")
    if market_slug:
        validate_market_slug(market_slug, get_unique_markets(session.trades))
        trades = filter_trades_by_market_slug(trades, market_slug)

    trades = apply_filters(trades, arguments)
    metrics = calculate_advanced_metrics(trades)
    return [types.TextContent(type="text", text=to_json_text(sanitize_dict(metrics)))]


@safe_tool
async def _handle_market_breakdown(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    trades = apply_filters(session.trades, arguments)
    breakdown = calculate_market_pnl(trades)

    result = []
    for slug, stats in sorted(breakdown.items(), key=lambda x: x[1]["total_pnl"], reverse=True):
        result.append(
            {
                "market_slug": slug,
                "market": stats["market_name"],
                "trade_count": stats["trade_count"],
                "pnl": stats["total_pnl"],
                "volume": stats["total_volume"],
            }
        )

    return [types.TextContent(type="text", text=to_json_text(result))]


@safe_tool
async def _handle_provider_breakdown(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    from prediction_analyzer.config import PROVIDER_CONFIGS

    sources = {}
    for trade in session.trades:
        src = getattr(trade, "source", "limitless")
        if src not in sources:
            sources[src] = {
                "total_trades": 0,
                "total_pnl": 0.0,
                "total_volume": 0.0,
                "currency": getattr(trade, "currency", "USD"),
            }
        sources[src]["total_trades"] += 1
        sources[src]["total_pnl"] += trade.pnl
        sources[src]["total_volume"] += trade.cost

    result = []
    for src, stats in sorted(sources.items(), key=lambda x: x[1]["total_pnl"], reverse=True):
        cfg = PROVIDER_CONFIGS.get(src, {})
        result.append(
            {
                "provider": src,
                "display_name": cfg.get("display_name", src.title()),
                "total_trades": stats["total_trades"],
                "total_pnl": stats["total_pnl"],
                "total_volume": stats["total_volume"],
                "currency": stats["currency"],
            }
        )

    return [types.TextContent(type="text", text=to_json_text(result))]
