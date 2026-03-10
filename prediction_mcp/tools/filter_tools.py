from __future__ import annotations

# prediction_mcp/tools/filter_tools.py
"""
Trade filtering tools.

Tools: filter_trades
"""
import logging

from mcp import types

from prediction_analyzer.exceptions import NoTradesError

from ..state import session
from ..errors import safe_tool
from ..serializers import to_json_text
from .._apply_filters import apply_filters

logger = logging.getLogger(__name__)


def get_tool_definitions() -> list[types.Tool]:
    """Return tool definitions for filter tools."""
    return [
        types.Tool(
            name="filter_trades",
            description=(
                "Apply filters to the loaded trades and store the filtered result. "
                "Subsequent analysis tools can operate on either all trades or filtered trades. "
                "Use clear=true to reset all filters."
            ),
            inputSchema={
                "type": "object",
                "properties": {
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
                    "market_slug": {
                        "type": "string",
                        "description": "Limit to specific market",
                    },
                    "clear": {
                        "type": "boolean",
                        "description": "Clear all filters and reset to full dataset",
                        "default": False,
                    },
                },
            },
        ),
    ]


async def handle_tool(name: str, arguments: dict):
    """Handle filter tool calls. Returns content list or None if not handled."""
    if name == "filter_trades":
        return await _handle_filter_trades(arguments)
    return None


@safe_tool
async def _handle_filter_trades(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    if arguments.get("clear", False):
        session.filtered_trades = list(session.trades)
        session.active_filters.clear()
    else:
        filtered = apply_filters(session.trades, arguments)
        session.filtered_trades = filtered

        session.active_filters = {
            k: v for k, v in arguments.items()
            if v is not None and k != "clear"
        }

    result = {
        "original_count": len(session.trades),
        "filtered_count": len(session.filtered_trades),
        "active_filters": session.active_filters,
    }
    return [types.TextContent(type="text", text=to_json_text(result))]
