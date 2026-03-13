from __future__ import annotations

# prediction_mcp/tools/chart_tools.py
"""
Chart generation tools.

Tools: generate_chart, generate_dashboard
"""
import logging

from mcp import types

from prediction_analyzer.charts.simple import generate_simple_chart
from prediction_analyzer.charts.pro import generate_pro_chart
from prediction_analyzer.charts.enhanced import generate_enhanced_chart
from prediction_analyzer.charts.global_chart import generate_global_dashboard
from prediction_analyzer.trade_filter import (
    filter_trades_by_market_slug,
    group_trades_by_market,
    get_unique_markets,
)
from prediction_analyzer.exceptions import NoTradesError

from ..state import get_session
from ..errors import safe_tool
from ..serializers import to_json_text
from ..validators import validate_chart_type, validate_market_slug
from prediction_analyzer.exceptions import ChartError

logger = logging.getLogger(__name__)

_CHART_GENERATORS = {
    "simple": generate_simple_chart,
    "pro": generate_pro_chart,
    "enhanced": generate_enhanced_chart,
}


def get_tool_definitions() -> list[types.Tool]:
    """Return tool definitions for chart tools."""
    return [
        types.Tool(
            name="generate_chart",
            description=(
                "Generate a chart image or interactive HTML for a specific market. "
                "Chart types: 'simple' (PNG, quick view), 'pro' (HTML, interactive), "
                "'enhanced' (HTML, battlefield view). Does NOT open in browser. "
                "Returns {file_path: str, chart_type: str, market: str, trade_count: int}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "market_slug": {
                        "type": "string",
                        "description": "Market to chart (from list_markets)",
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["simple", "pro", "enhanced"],
                        "description": "Chart style to generate",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory for chart output (optional)",
                    },
                },
                "required": ["market_slug", "chart_type"],
            },
        ),
        types.Tool(
            name="generate_dashboard",
            description=(
                "Generate a multi-market PnL dashboard as interactive HTML. "
                "Shows cumulative PnL for all markets plus total portfolio. "
                "Trades must be loaded first. "
                "Returns {file_path: str, market_count: int, total_trades: int}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "output_dir": {
                        "type": "string",
                        "description": "Directory for output (optional)",
                    },
                },
            },
        ),
    ]


async def handle_tool(name: str, arguments: dict):
    """Handle chart tool calls. Returns content list or None if not handled."""
    if name == "generate_chart":
        return await _handle_generate_chart(arguments)
    elif name == "generate_dashboard":
        return await _handle_generate_dashboard(arguments)
    return None


@safe_tool
async def _handle_generate_chart(arguments: dict):
    session = get_session()
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    market_slug = arguments.get("market_slug")
    chart_type = arguments.get("chart_type")
    output_dir = arguments.get("output_dir")

    if not market_slug:
        raise ValueError("market_slug is required")
    if not chart_type:
        raise ValueError("chart_type is required")

    validate_chart_type(chart_type)
    if chart_type not in _CHART_GENERATORS:
        raise ChartError(
            f"Chart type '{chart_type}' is not supported for single-market charts. "
            f"Use 'generate_dashboard' for global charts, or choose from: "
            f"{sorted(_CHART_GENERATORS.keys())}"
        )
    validate_market_slug(market_slug, get_unique_markets(session.trades))

    trades = filter_trades_by_market_slug(session.trades, market_slug)
    if not trades:
        raise NoTradesError(f"No trades found for market '{market_slug}'")

    market_name = trades[0].market
    generator = _CHART_GENERATORS[chart_type]

    kwargs = {"show": False}
    if output_dir:
        kwargs["output_dir"] = output_dir

    file_path = generator(trades, market_name, **kwargs)

    result = {
        "file_path": str(file_path),
        "chart_type": chart_type,
        "market": market_name,
        "trade_count": len(trades),
    }
    return [types.TextContent(type="text", text=to_json_text(result))]


@safe_tool
async def _handle_generate_dashboard(arguments: dict):
    session = get_session()
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    output_dir = arguments.get("output_dir")
    trades_by_market = group_trades_by_market(session.trades)

    kwargs = {"show": False}
    if output_dir:
        kwargs["output_dir"] = output_dir

    file_path = generate_global_dashboard(trades_by_market, **kwargs)

    result = {
        "file_path": str(file_path),
        "market_count": len(trades_by_market),
        "total_trades": len(session.trades),
    }
    return [types.TextContent(type="text", text=to_json_text(result))]
