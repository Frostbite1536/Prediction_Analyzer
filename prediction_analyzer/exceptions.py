# prediction_analyzer/exceptions.py
"""
Custom exception classes for the prediction analyzer.

These provide structured error handling that MCP tool wrappers
can catch and convert into recovery-friendly error responses.
"""


class PredictionAnalyzerError(Exception):
    """Base exception for all prediction analyzer errors."""

    pass


class NoTradesError(PredictionAnalyzerError):
    """Raised when an operation requires trades but none are loaded."""

    pass


class TradeLoadError(PredictionAnalyzerError):
    """Raised when trade data cannot be loaded from a file or API."""

    pass


class InvalidFilterError(PredictionAnalyzerError):
    """Raised when filter parameters are invalid."""

    pass


class MarketNotFoundError(PredictionAnalyzerError):
    """Raised when a market slug doesn't match any loaded trades."""

    pass


class ExportError(PredictionAnalyzerError):
    """Raised when data export fails."""

    pass


class ChartError(PredictionAnalyzerError):
    """Raised when chart generation fails."""

    pass
