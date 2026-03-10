# prediction_mcp/tools/portfolio_tools.py
"""
Portfolio analysis tools (new features).

Tools: get_open_positions, get_concentration_risk, get_drawdown_analysis, compare_periods
"""
import logging

from mcp import types

from prediction_analyzer.positions import calculate_open_positions, calculate_concentration_risk
from prediction_analyzer.drawdown import analyze_drawdowns
from prediction_analyzer.comparison import compare_periods as _compare_periods
from prediction_analyzer.exceptions import NoTradesError

from ..state import session
from ..errors import error_result, safe_tool
from ..serializers import to_json_text, sanitize_dict
from ..validators import validate_date

logger = logging.getLogger(__name__)


def get_tool_definitions() -> list[types.Tool]:
    """Return tool definitions for portfolio tools."""
    return [
        types.Tool(
            name="get_open_positions",
            description=(
                "Calculate current open positions with unrealized PnL. "
                "Fetches current market prices when available. "
                "Optionally limited to a specific market."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "market_slug": {
                        "type": "string",
                        "description": "Check specific market only (optional)",
                    },
                },
            },
        ),
        types.Tool(
            name="get_concentration_risk",
            description=(
                "Analyze portfolio concentration and diversification across markets. "
                "Returns per-market exposure, Herfindahl-Hirschman Index, and top-3 concentration."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_drawdown_analysis",
            description=(
                "Analyze maximum drawdown periods including duration, recovery, and all drawdown events. "
                "Optionally limited to a specific market."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "market_slug": {
                        "type": "string",
                        "description": "Limit to specific market (optional)",
                    },
                },
            },
        ),
        types.Tool(
            name="compare_periods",
            description=(
                "Compare trading performance between two time periods. "
                "Returns PnL, win rate, Sharpe ratio for each period and the changes between them."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "period_1_start": {
                        "type": "string",
                        "description": "Start date for period 1 (YYYY-MM-DD)",
                    },
                    "period_1_end": {
                        "type": "string",
                        "description": "End date for period 1 (YYYY-MM-DD)",
                    },
                    "period_2_start": {
                        "type": "string",
                        "description": "Start date for period 2 (YYYY-MM-DD)",
                    },
                    "period_2_end": {
                        "type": "string",
                        "description": "End date for period 2 (YYYY-MM-DD)",
                    },
                },
                "required": ["period_1_start", "period_1_end", "period_2_start", "period_2_end"],
            },
        ),
    ]


async def handle_tool(name: str, arguments: dict):
    """Handle portfolio tool calls. Returns content list or None if not handled."""
    if name == "get_open_positions":
        return await _handle_open_positions(arguments)
    elif name == "get_concentration_risk":
        return await _handle_concentration_risk(arguments)
    elif name == "get_drawdown_analysis":
        return await _handle_drawdown_analysis(arguments)
    elif name == "compare_periods":
        return await _handle_compare_periods(arguments)
    return None


@safe_tool
async def _handle_open_positions(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    market_slug = arguments.get("market_slug")
    positions = calculate_open_positions(session.trades, market_slug=market_slug)
    return [types.TextContent(type="text", text=to_json_text(positions))]


@safe_tool
async def _handle_concentration_risk(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    result = calculate_concentration_risk(session.trades)
    return [types.TextContent(type="text", text=to_json_text(result))]


@safe_tool
async def _handle_drawdown_analysis(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    market_slug = arguments.get("market_slug")
    result = analyze_drawdowns(session.trades, market_slug=market_slug)
    return [types.TextContent(type="text", text=to_json_text(result))]


@safe_tool
async def _handle_compare_periods(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    p1_start = validate_date(arguments.get("period_1_start"), "period_1_start")
    p1_end = validate_date(arguments.get("period_1_end"), "period_1_end")
    p2_start = validate_date(arguments.get("period_2_start"), "period_2_start")
    p2_end = validate_date(arguments.get("period_2_end"), "period_2_end")

    if not all([p1_start, p1_end, p2_start, p2_end]):
        raise ValueError("All four date parameters are required")

    result = _compare_periods(session.trades, p1_start, p1_end, p2_start, p2_end)
    return [types.TextContent(type="text", text=to_json_text(result))]
