# tests/mcp/test_errors.py
"""Tests for MCP error handling."""

import pytest
import asyncio

from prediction_analyzer.exceptions import (
    NoTradesError,
    TradeLoadError,
    InvalidFilterError,
    MarketNotFoundError,
    ExportError,
    ChartError,
)
from prediction_mcp.errors import error_result, safe_tool


class TestErrorResult:
    def test_no_trades_error(self):
        result = error_result(NoTradesError("No trades"))
        assert result.isError is True
        assert "No trades" in result.content[0].text
        assert "Recovery hint" in result.content[0].text
        assert "load_trades" in result.content[0].text

    def test_trade_load_error(self):
        result = error_result(TradeLoadError("Bad file"))
        assert result.isError is True
        assert "Bad file" in result.content[0].text
        assert "JSON, CSV, XLSX" in result.content[0].text

    def test_invalid_filter_error(self):
        result = error_result(InvalidFilterError("Bad date"))
        assert result.isError is True
        assert "YYYY-MM-DD" in result.content[0].text

    def test_market_not_found_error(self):
        result = error_result(MarketNotFoundError("unknown-market"))
        assert result.isError is True
        assert "list_markets" in result.content[0].text

    def test_export_error(self):
        result = error_result(ExportError("Write failed"))
        assert result.isError is True
        assert "writable" in result.content[0].text

    def test_chart_error(self):
        result = error_result(ChartError("Chart fail"))
        assert result.isError is True
        assert "chart type" in result.content[0].text

    def test_generic_exception(self):
        result = error_result(ValueError("something wrong"))
        assert result.isError is True
        assert "Unexpected error" in result.content[0].text


class TestSafeTool:
    def test_successful_call(self):
        @safe_tool
        async def good_handler(args):
            return [{"text": "ok"}]

        result = asyncio.run(good_handler({}))
        assert result == [{"text": "ok"}]

    def test_catches_prediction_error(self):
        @safe_tool
        async def bad_handler(args):
            raise NoTradesError("No trades loaded")

        result = asyncio.run(bad_handler({}))
        assert "No trades loaded" in result[0].text
        assert "Recovery hint" in result[0].text

    def test_catches_generic_exception(self):
        @safe_tool
        async def crash_handler(args):
            raise RuntimeError("unexpected crash")

        result = asyncio.run(crash_handler({}))
        assert "unexpected crash" in result[0].text
