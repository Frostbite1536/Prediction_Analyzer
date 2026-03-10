# prediction_mcp/server.py
"""
MCP Server entry point for Prediction Analyzer.

Supports two transports:
  - stdio (primary, for Claude Code / Claude Desktop)
  - HTTP/SSE (secondary, for web agents)

Usage:
    python -m prediction_mcp                        # stdio (default)
    python -m prediction_mcp --sse                  # HTTP/SSE on port 8000
    python -m prediction_mcp --sse --port 3000
    python -m prediction_mcp --persist session.db   # enable SQLite persistence
"""
import os
import sys
import logging
import asyncio
import argparse

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
        "Load prediction market trades from files or APIs "
        "(Limitless Exchange, Polymarket, Kalshi, Manifold Markets), "
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


# Optional session store for SQLite persistence (set by main())
_session_store = None

# Tools that modify session state and should trigger a save
_STATE_MODIFYING_TOOLS = {"load_trades", "fetch_trades", "filter_trades"}


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Route tool calls to the appropriate module handler."""
    for module in _TOOL_MODULES:
        result = await module.handle_tool(name, arguments)
        if result is not None:
            # Auto-save session after state-modifying tools
            if _session_store and name in _STATE_MODIFYING_TOOLS:
                try:
                    from .state import session
                    _session_store.save(session)
                except Exception:
                    logger.exception("Failed to persist session after %s", name)
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


def create_sse_app(sse_path: str = "/sse", message_path: str = "/messages"):
    """Create a Starlette ASGI app that serves MCP over SSE.

    Args:
        sse_path: Path for SSE connection endpoint.
        message_path: Path for client-to-server message posting.

    Returns:
        A Starlette application instance.
    """
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse

    sse_transport = SseServerTransport(message_path)

    async def handle_sse(request):
        """Handle SSE connection — long-lived event stream."""
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    async def handle_messages(request):
        """Handle client-to-server JSON-RPC messages."""
        await sse_transport.handle_post_message(
            request.scope, request.receive, request._send
        )

    async def health(request):
        return JSONResponse({"status": "ok", "server": "prediction-analyzer", "version": "1.0.0"})

    starlette_app = Starlette(
        routes=[
            Route("/health", health),
            Route(sse_path, handle_sse),
            Route(message_path, handle_messages, methods=["POST"]),
        ],
    )
    return starlette_app


def run_sse(host: str = "0.0.0.0", port: int = 8000):
    """Run the MCP server over HTTP/SSE transport."""
    import uvicorn
    logger.info("Starting Prediction Analyzer MCP server (SSE) on %s:%d", host, port)
    starlette_app = create_sse_app()
    uvicorn.run(starlette_app, host=host, port=port, log_level="info")


def _setup_persistence(db_path: str) -> None:
    """Initialize SQLite session persistence."""
    global _session_store
    from .persistence import SessionStore
    from .state import session

    _session_store = SessionStore(db_path)
    restored = _session_store.restore(session)
    if restored:
        logger.info("Restored %d trades from %s", session.trade_count, db_path)


def main():
    """Entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="Prediction Analyzer MCP Server")
    parser.add_argument(
        "--sse", action="store_true",
        help="Use HTTP/SSE transport instead of stdio",
    )
    parser.add_argument(
        "--host", default="0.0.0.0",
        help="Host to bind SSE server (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Port for SSE server (default: 8000)",
    )
    parser.add_argument(
        "--persist", metavar="DB_PATH",
        default=os.environ.get("PREDICTION_MCP_DB"),
        help="SQLite database path for session persistence (or set PREDICTION_MCP_DB env var)",
    )
    args = parser.parse_args()

    if args.persist:
        _setup_persistence(args.persist)

    if args.sse:
        run_sse(host=args.host, port=args.port)
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
