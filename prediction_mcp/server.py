# prediction_mcp/server.py
"""
MCP Server entry point for Prediction Analyzer.

Supports stdio transport (primary, for Claude Code) and can be
extended to HTTP/SSE for web agents.

Usage:
    python -m prediction_mcp
"""
import sys
import logging
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# Configure ALL logging to stderr (critical for stdio transport)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)

# Import tool modules
from .tools import (
    data_tools, analysis_tools, filter_tools, chart_tools,
    export_tools, portfolio_tools, tax_tools,
)

# Collect all tool modules for dispatch
_TOOL_MODULES = [
    data_tools, analysis_tools, filter_tools, chart_tools,
    export_tools, portfolio_tools, tax_tools,
]

# Create the MCP server instance
app = Server(
    "prediction-analyzer",
    version="1.0.0",
    instructions=(
        "Prediction Analyzer MCP Server. "
        "Load prediction market trades from files or the Limitless Exchange API, "
        "then run PnL analyses, generate charts, filter trades, and export data. "
        "Start by loading trades with 'load_trades' or 'fetch_trades'."
    ),
)


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """Aggregate tool definitions from all tool modules."""
    tools = []
    for module in _TOOL_MODULES:
        tools.extend(module.get_tool_definitions())
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Route tool calls to the appropriate module handler."""
    for module in _TOOL_MODULES:
        result = await module.handle_tool(name, arguments)
        if result is not None:
            return result

    return [types.TextContent(
        type="text",
        text=f"Unknown tool: {name}",
    )]


async def run_stdio():
    """Run the MCP server over stdio transport."""
    logger.info("Starting Prediction Analyzer MCP server (stdio)")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
    logger.info("MCP server stopped")


def main():
    """Entry point for the MCP server."""
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
