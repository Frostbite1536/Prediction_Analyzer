from __future__ import annotations

# prediction_mcp/tools/tax_tools.py
"""
Tax reporting tools (new feature).

Tools: get_tax_report
"""
import logging

from mcp import types

from prediction_analyzer.tax import calculate_capital_gains
from prediction_analyzer.exceptions import NoTradesError

from ..state import session
from ..errors import safe_tool
from ..serializers import to_json_text
from ..validators import validate_cost_basis_method

logger = logging.getLogger(__name__)


def get_tool_definitions() -> list[types.Tool]:
    """Return tool definitions for tax tools."""
    return [
        types.Tool(
            name="get_tax_report",
            description=(
                "Generate capital gains/losses report for tax purposes. "
                "Supports FIFO, LIFO, and average cost basis methods. "
                "Classifies gains as short-term or long-term based on 1-year holding period."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tax_year": {
                        "type": "integer",
                        "description": "Tax year (e.g. 2025)",
                    },
                    "cost_basis_method": {
                        "type": "string",
                        "enum": ["fifo", "lifo", "average"],
                        "description": "Cost basis method (default fifo)",
                        "default": "fifo",
                    },
                },
                "required": ["tax_year"],
            },
        ),
    ]


async def handle_tool(name: str, arguments: dict):
    """Handle tax tool calls. Returns content list or None if not handled."""
    if name == "get_tax_report":
        return await _handle_tax_report(arguments)
    return None


@safe_tool
async def _handle_tax_report(arguments: dict):
    if not session.has_trades:
        raise NoTradesError("No trades loaded")

    tax_year = arguments.get("tax_year")
    if not tax_year:
        raise ValueError("tax_year is required")

    method = validate_cost_basis_method(arguments.get("cost_basis_method", "fifo"))
    result = calculate_capital_gains(session.trades, tax_year=tax_year, cost_basis_method=method)
    return [types.TextContent(type="text", text=to_json_text(result))]
