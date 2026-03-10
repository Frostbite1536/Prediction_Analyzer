from __future__ import annotations

# prediction_mcp/tools/export_tools.py
"""
Data export tools.

Tools: export_trades
"""
import logging
import os

from mcp import types

from prediction_analyzer.reporting.report_data import export_to_csv, export_to_excel, export_to_json
from prediction_analyzer.trade_filter import filter_trades_by_market_slug, get_unique_markets
from prediction_analyzer.exceptions import NoTradesError

from ..state import session
from ..errors import safe_tool
from ..serializers import to_json_text
from ..validators import validate_export_format, validate_market_slug

logger = logging.getLogger(__name__)

_EXPORTERS = {
    "csv": export_to_csv,
    "xlsx": export_to_excel,
    "json": export_to_json,
}


def get_tool_definitions() -> list[types.Tool]:
    """Return tool definitions for export tools."""
    return [
        types.Tool(
            name="export_trades",
            description=(
                "Export trades to CSV, Excel, or JSON format. "
                "Optionally export only trades for a specific market. "
                "Returns {file_path: str, trade_count: int, format: str}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["csv", "xlsx", "json"],
                        "description": "Output format",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Full output file path",
                    },
                    "market_slug": {
                        "type": "string",
                        "description": "Export only trades for this market (optional)",
                    },
                },
                "required": ["format", "output_path"],
            },
        ),
    ]


async def handle_tool(name: str, arguments: dict):
    """Handle export tool calls. Returns content list or None if not handled."""
    if name == "export_trades":
        return await _handle_export_trades(arguments)
    return None


@safe_tool
async def _handle_export_trades(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    fmt = arguments.get("format")
    output_path = arguments.get("output_path")
    market_slug = arguments.get("market_slug")

    if not fmt:
        raise ValueError("format is required")
    if not output_path:
        raise ValueError("output_path is required")

    # Prevent path traversal — reject paths containing ".." components
    # which could escape the intended directory.  Absolute paths are
    # allowed (the user explicitly chose where to write).
    # Check the raw path (before normpath resolves ..) to catch traversal.
    if ".." in output_path.replace("\\", "/").split("/"):
        raise ValueError(
            f"output_path must not contain '..': {output_path}"
        )

    validate_export_format(fmt)

    trades = session.trades
    if market_slug:
        validate_market_slug(market_slug, get_unique_markets(session.trades))
        trades = filter_trades_by_market_slug(trades, market_slug)

    exporter = _EXPORTERS[fmt]
    exporter(trades, output_path)

    result = {
        "file_path": output_path,
        "trade_count": len(trades),
        "format": fmt,
    }
    return [types.TextContent(type="text", text=to_json_text(result))]
