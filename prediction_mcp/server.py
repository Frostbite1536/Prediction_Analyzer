from __future__ import annotations

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
    data_tools,
    analysis_tools,
    filter_tools,
    chart_tools,
    export_tools,
    portfolio_tools,
    tax_tools,
)

# Collect all tool modules for dispatch
_TOOL_MODULES = [
    data_tools,
    analysis_tools,
    filter_tools,
    chart_tools,
    export_tools,
    portfolio_tools,
    tax_tools,
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


# ---------------------------------------------------------------------------
# MCP Resources — expose session data for direct LLM reading
# ---------------------------------------------------------------------------


@app.list_resources()
async def list_resources() -> list[types.Resource]:
    """List available resources based on current session state."""
    from .state import get_session
    session = get_session()

    resources: list[types.Resource] = []

    if session.has_trades:
        resources.append(
            types.Resource(
                uri="prediction://trades/summary",
                name="Trade Summary",
                description=(
                    f"Summary of {session.trade_count} loaded trades "
                    f"from {', '.join(session.sources) or 'unknown'} providers."
                ),
                mimeType="application/json",
            )
        )
        resources.append(
            types.Resource(
                uri="prediction://trades/markets",
                name="Market List",
                description="List of all unique markets in the current session.",
                mimeType="application/json",
            )
        )
        if session.active_filters:
            resources.append(
                types.Resource(
                    uri="prediction://trades/filters",
                    name="Active Filters",
                    description="Currently applied trade filters.",
                    mimeType="application/json",
                )
            )

    return resources


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    from .state import get_session
    session = get_session()
    from .serializers import to_json_text, sanitize_dict
    from prediction_analyzer.trade_filter import get_unique_markets, filter_trades_by_market_slug
    from prediction_analyzer.pnl import calculate_global_pnl_summary

    if uri == "prediction://trades/summary":
        if not session.has_trades:
            return to_json_text({"error": "No trades loaded"})
        summary = calculate_global_pnl_summary(session.trades)
        return to_json_text(sanitize_dict(summary))

    elif uri == "prediction://trades/markets":
        if not session.has_trades:
            return to_json_text({"error": "No trades loaded"})
        markets = get_unique_markets(session.trades)
        result = []
        for slug, title in sorted(markets.items()):
            market_trades = filter_trades_by_market_slug(session.trades, slug)
            result.append(
                {
                    "slug": slug,
                    "title": title,
                    "trade_count": len(market_trades),
                    "sources": list({t.source for t in market_trades}),
                }
            )
        return to_json_text(result)

    elif uri == "prediction://trades/filters":
        return to_json_text(session.active_filters or {})

    raise ValueError(f"Unknown resource URI: {uri}")


# ---------------------------------------------------------------------------
# MCP Prompts — pre-built templates for common analysis workflows
# ---------------------------------------------------------------------------


@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    """List available prompt templates."""
    return [
        types.Prompt(
            name="analyze_portfolio",
            description=(
                "Comprehensive portfolio analysis: global summary, "
                "top/bottom markets, risk metrics, and actionable insights."
            ),
            arguments=[
                types.PromptArgument(
                    name="focus",
                    description="Optional focus area: 'risk', 'performance', or 'tax'",
                    required=False,
                ),
            ],
        ),
        types.Prompt(
            name="compare_periods",
            description=(
                "Compare trading performance between two date ranges. "
                "Useful for month-over-month or pre/post strategy change analysis."
            ),
            arguments=[
                types.PromptArgument(
                    name="period1_start",
                    description="Start date of first period (YYYY-MM-DD)",
                    required=True,
                ),
                types.PromptArgument(
                    name="period1_end",
                    description="End date of first period (YYYY-MM-DD)",
                    required=True,
                ),
                types.PromptArgument(
                    name="period2_start",
                    description="Start date of second period (YYYY-MM-DD)",
                    required=True,
                ),
                types.PromptArgument(
                    name="period2_end",
                    description="End date of second period (YYYY-MM-DD)",
                    required=True,
                ),
            ],
        ),
        types.Prompt(
            name="daily_report",
            description="Generate a daily trading summary for today or a specific date.",
            arguments=[
                types.PromptArgument(
                    name="date",
                    description="Date to report on (YYYY-MM-DD). Defaults to today.",
                    required=False,
                ),
            ],
        ),
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> types.GetPromptResult:
    """Return a prompt template with user arguments filled in."""
    args = arguments or {}

    if name == "analyze_portfolio":
        focus = args.get("focus", "performance")
        focus_instructions = {
            "risk": (
                "Focus on risk analysis: run get_advanced_metrics for Sharpe ratio, max drawdown, "
                "and Sortino ratio. Then run get_concentration_risk and get_drawdown_analysis. "
                "Flag any markets with outsized position sizes or unrealized losses."
            ),
            "tax": (
                "Focus on tax implications: run get_tax_report with FIFO method. "
                "Summarize short-term vs long-term gains. Note any wash sale concerns "
                "and suggest tax-loss harvesting opportunities."
            ),
            "performance": (
                "Focus on trading performance: run get_global_summary for overall stats, "
                "then get_market_breakdown to find best/worst markets. Run get_advanced_metrics "
                "for risk-adjusted returns. Provide actionable recommendations."
            ),
        }
        return types.GetPromptResult(
            description=f"Portfolio analysis focused on {focus}",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            "Analyze my prediction market portfolio. "
                            f"{focus_instructions.get(focus, focus_instructions['performance'])}\n\n"
                            "Structure your response with:\n"
                            "1. Executive Summary (2-3 sentences)\n"
                            "2. Key Metrics table\n"
                            "3. Top 3 and Bottom 3 markets\n"
                            "4. Risk Assessment\n"
                            "5. Recommendations"
                        ),
                    ),
                ),
            ],
        )

    elif name == "compare_periods":
        return types.GetPromptResult(
            description="Period comparison analysis",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"Compare my trading performance between two periods:\n"
                            f"- Period 1: {args['period1_start']} to {args['period1_end']}\n"
                            f"- Period 2: {args['period2_start']} to {args['period2_end']}\n\n"
                            "For each period, run get_global_summary with the date filters, "
                            "then get_advanced_metrics. Compare win rate, total PnL, ROI, "
                            "Sharpe ratio, and max drawdown.\n\n"
                            "Present results in a side-by-side comparison table and explain "
                            "what changed between the periods."
                        ),
                    ),
                ),
            ],
        )

    elif name == "daily_report":
        date = args.get("date", "today")
        return types.GetPromptResult(
            description=f"Daily trading report for {date}",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"Generate a daily trading report for {date}.\n\n"
                            "1. Use get_global_summary with start_date and end_date set to "
                            f"'{date}' to get the day's stats\n"
                            "2. Use get_trade_details to list individual trades from that day\n"
                            "3. Summarize: trades executed, net PnL, win rate\n"
                            "4. Note any notable wins or losses"
                        ),
                    ),
                ),
            ],
        )

    raise ValueError(f"Unknown prompt: {name}")


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
                    from .state import get_session

                    _session_store.save(get_session())
                except Exception:
                    logger.exception("Failed to persist session after %s", name)
            return result

    return [
        types.TextContent(
            type="text",
            text=f"Unknown tool: {name}",
        )
    ]


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
        """Handle SSE connection — long-lived event stream.

        Each SSE client gets its own SessionState so concurrent clients
        don't corrupt each other's loaded trades and filters.
        """
        from .state import SessionState, _session_var

        conn_session = SessionState()
        token = _session_var.set(conn_session)
        try:
            async with sse_transport.connect_sse(request.scope, request.receive, request._send) as (
                read_stream,
                write_stream,
            ):
                await app.run(read_stream, write_stream, app.create_initialization_options())
        finally:
            _session_var.reset(token)

    async def handle_messages(request):
        """Handle client-to-server JSON-RPC messages."""
        await sse_transport.handle_post_message(request.scope, request.receive, request._send)

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
    from .state import get_session

    _session_store = SessionStore(db_path)
    restored = _session_store.restore(get_session())
    if restored:
        logger.info("Restored %d trades from %s", get_session().trade_count, db_path)


def main():
    """Entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="Prediction Analyzer MCP Server")
    parser.add_argument(
        "--sse",
        action="store_true",
        help="Use HTTP/SSE transport instead of stdio",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind SSE server (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE server (default: 8000)",
    )
    parser.add_argument(
        "--persist",
        metavar="DB_PATH",
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
