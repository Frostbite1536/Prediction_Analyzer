# prediction_mcp/errors.py
"""
Structured error responses for MCP tools.

Converts internal exceptions into user-friendly error messages
with recovery hints that help the LLM agent self-correct.
"""
import functools
import logging

from mcp import types

from prediction_analyzer.exceptions import (
    PredictionAnalyzerError,
    NoTradesError,
    TradeLoadError,
    InvalidFilterError,
    MarketNotFoundError,
    ExportError,
    ChartError,
)

logger = logging.getLogger(__name__)


# Maps exception types to recovery hints
_RECOVERY_HINTS = {
    NoTradesError: "Load trades first using the 'load_trades' or 'fetch_trades' tool.",
    TradeLoadError: "Check the file path and format. Supported formats: JSON, CSV, XLSX.",
    InvalidFilterError: "Check filter parameter values. Dates should be 'YYYY-MM-DD' format.",
    MarketNotFoundError: "Use 'list_markets' to see available market slugs.",
    ExportError: "Check the output path is writable and the format is supported.",
    ChartError: "Ensure trades are loaded and the chart type is valid.",
}


def error_result(error: Exception) -> types.CallToolResult:
    """
    Convert an exception into a structured MCP error response.

    Args:
        error: The exception that occurred.

    Returns:
        A CallToolResult with isError=True and a helpful message.
    """
    if isinstance(error, PredictionAnalyzerError):
        hint = _RECOVERY_HINTS.get(type(error), "")
        message = str(error)
        if hint:
            message = f"{message}\n\nRecovery hint: {hint}"
    else:
        message = f"Unexpected error: {error}"

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        isError=True,
    )


def safe_tool(func):
    """
    Decorator that wraps MCP tool handlers to catch exceptions
    and return structured error responses with recovery hints.

    Eliminates try/except boilerplate from individual handlers.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except PredictionAnalyzerError as e:
            return error_result(e).content
        except Exception as e:
            logger.exception("Unhandled error in MCP tool %s", func.__name__)
            return error_result(e).content
    return wrapper
