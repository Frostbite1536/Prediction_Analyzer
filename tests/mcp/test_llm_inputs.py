# tests/mcp/test_llm_inputs.py
"""
LLM-style input edge case tests.

Tests each tool with the kinds of inputs an LLM might realistically send:
- Wrong parameter names (e.g., 'market' instead of 'market_slug')
- Lowercase enum values (e.g., 'buy' instead of 'Buy')
- Missing required parameters
- Empty strings, null values
- NaN and Infinity as numeric inputs
"""
import json
import asyncio
import math

import pytest

from prediction_mcp.tools import (
    data_tools, analysis_tools, filter_tools,
    chart_tools, export_tools, portfolio_tools, tax_tools,
)
from prediction_mcp.state import session
from .conftest import make_trades


class TestWrongParameterNames:
    """LLMs sometimes use similar but incorrect parameter names."""

    def test_market_instead_of_market_slug(self, loaded_session):
        """LLM might say 'market' instead of 'market_slug'."""
        result = asyncio.run(data_tools.handle_tool("get_trade_details", {
            "market": "market-0",  # wrong key
        }))
        # Should return all trades (market param ignored, no market_slug filtering)
        data = json.loads(result[0].text)
        assert data["total"] == 10

    def test_path_instead_of_file_path(self):
        """LLM might say 'path' instead of 'file_path'."""
        result = asyncio.run(data_tools.handle_tool("load_trades", {
            "path": "/some/file.json",  # wrong key
        }))
        assert "file_path is required" in result[0].text

    def test_type_instead_of_chart_type(self, loaded_session):
        """LLM might say 'type' instead of 'chart_type'."""
        result = asyncio.run(chart_tools.handle_tool("generate_chart", {
            "market_slug": "market-0",
            "type": "simple",  # wrong key
        }))
        assert "chart_type" in result[0].text

    def test_year_instead_of_tax_year(self, loaded_session):
        """LLM might say 'year' instead of 'tax_year'."""
        result = asyncio.run(tax_tools.handle_tool("get_tax_report", {
            "year": 2024,  # wrong key
        }))
        assert "tax_year is required" in result[0].text

    def test_key_instead_of_api_key(self):
        """LLM might say 'key' instead of 'api_key'."""
        result = asyncio.run(data_tools.handle_tool("fetch_trades", {
            "key": "lmts_test_key",  # wrong key
        }))
        assert "api_key is required" in result[0].text


class TestLowercaseEnumValues:
    """LLMs often send lowercase versions of enum values."""

    def test_lowercase_trade_type(self, loaded_session):
        """LLM sends 'buy' instead of 'Buy'."""
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {
            "trade_types": ["buy"],
        }))
        assert "Invalid trade types" in result[0].text

    def test_lowercase_side(self, loaded_session):
        """LLM sends 'yes' instead of 'YES'."""
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {
            "sides": ["yes"],
        }))
        assert "Invalid sides" in result[0].text

    def test_uppercase_format(self, loaded_session):
        """LLM sends 'CSV' instead of 'csv'."""
        result = asyncio.run(export_tools.handle_tool("export_trades", {
            "format": "CSV",
            "output_path": "/tmp/test.csv",
        }))
        assert "Invalid export format" in result[0].text

    def test_uppercase_chart_type(self, loaded_session):
        """LLM sends 'Simple' instead of 'simple'."""
        result = asyncio.run(chart_tools.handle_tool("generate_chart", {
            "market_slug": "market-0",
            "chart_type": "Simple",
        }))
        assert "Invalid chart type" in result[0].text

    def test_uppercase_cost_basis(self, loaded_session):
        """LLM sends 'FIFO' instead of 'fifo'."""
        result = asyncio.run(tax_tools.handle_tool("get_tax_report", {
            "tax_year": 2024,
            "cost_basis_method": "FIFO",
        }))
        assert "Invalid cost basis method" in result[0].text

    def test_uppercase_sort_by(self, loaded_session):
        """LLM sends 'PNL' instead of 'pnl'."""
        result = asyncio.run(data_tools.handle_tool("get_trade_details", {
            "sort_by": "PNL",
        }))
        assert "Invalid sort field" in result[0].text


class TestEmptyAndNullValues:
    """LLMs sometimes send empty strings or null/None values."""

    def test_empty_string_file_path(self):
        result = asyncio.run(data_tools.handle_tool("load_trades", {
            "file_path": "",
        }))
        assert "file_path is required" in result[0].text

    def test_empty_string_api_key(self):
        result = asyncio.run(data_tools.handle_tool("fetch_trades", {
            "api_key": "",
        }))
        assert "api_key is required" in result[0].text

    def test_empty_string_market_slug(self, loaded_session):
        """Empty string market_slug should not filter (treated as falsy)."""
        result = asyncio.run(data_tools.handle_tool("get_trade_details", {
            "market_slug": "",
        }))
        data = json.loads(result[0].text)
        assert data["total"] == 10

    def test_null_format(self, loaded_session):
        result = asyncio.run(export_tools.handle_tool("export_trades", {
            "format": None,
            "output_path": "/tmp/test.csv",
        }))
        assert "format is required" in result[0].text

    def test_empty_arguments(self, loaded_session):
        """Empty dict should be handled gracefully by every tool."""
        # These should return error messages, not crash
        result = asyncio.run(data_tools.handle_tool("load_trades", {}))
        assert result is not None

        result = asyncio.run(chart_tools.handle_tool("generate_chart", {}))
        assert result is not None

        result = asyncio.run(export_tools.handle_tool("export_trades", {}))
        assert result is not None

    def test_none_tax_year(self, loaded_session):
        result = asyncio.run(tax_tools.handle_tool("get_tax_report", {
            "tax_year": None,
        }))
        assert "tax_year is required" in result[0].text


class TestNaNAndInfinityInputs:
    """LLMs might send NaN or Infinity as numeric parameters."""

    def test_nan_min_pnl(self, loaded_session):
        """NaN as a filter threshold should not crash."""
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {
            "min_pnl": float("nan"),
        }))
        # Should not crash — either filters nothing or returns error
        assert result is not None

    def test_infinity_max_pnl(self, loaded_session):
        """Infinity as max_pnl should not crash."""
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {
            "max_pnl": float("inf"),
        }))
        assert result is not None

    def test_negative_infinity_min_pnl(self, loaded_session):
        """Negative infinity as min_pnl should not crash."""
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {
            "min_pnl": float("-inf"),
        }))
        assert result is not None

    def test_nan_limit(self, loaded_session):
        """NaN as limit should be caught by validation."""
        result = asyncio.run(data_tools.handle_tool("get_trade_details", {
            "limit": float("nan"),
        }))
        assert "Invalid limit" in result[0].text

    def test_infinity_limit(self, loaded_session):
        """Infinity as limit should be caught by validation."""
        result = asyncio.run(data_tools.handle_tool("get_trade_details", {
            "limit": float("inf"),
        }))
        assert "Invalid limit" in result[0].text


class TestMissingRequiredParams:
    """Ensure all tools with required params return clear errors."""

    def test_generate_chart_no_params(self, loaded_session):
        result = asyncio.run(chart_tools.handle_tool("generate_chart", {}))
        assert "market_slug" in result[0].text or "required" in result[0].text

    def test_export_no_format(self, loaded_session):
        result = asyncio.run(export_tools.handle_tool("export_trades", {
            "output_path": "/tmp/test.csv",
        }))
        assert "format is required" in result[0].text

    def test_export_no_output_path(self, loaded_session):
        result = asyncio.run(export_tools.handle_tool("export_trades", {
            "format": "csv",
        }))
        assert "output_path is required" in result[0].text

    def test_compare_periods_partial(self, loaded_session):
        result = asyncio.run(portfolio_tools.handle_tool("compare_periods", {
            "period_1_start": "2024-01-01",
        }))
        assert "required" in result[0].text

    def test_market_summary_no_slug(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_market_summary", {}))
        assert "market_slug is required" in result[0].text


class TestAvailableMarketsInError:
    """Verify that market-not-found errors include available slugs."""

    def test_unknown_market_shows_available(self, loaded_session):
        result = asyncio.run(data_tools.handle_tool("get_trade_details", {
            "market_slug": "nonexistent-market",
        }))
        text = result[0].text
        assert "not found" in text
        assert "market-0" in text  # should list available slugs

    def test_unknown_market_in_analysis(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_market_summary", {
            "market_slug": "fake-market",
        }))
        text = result[0].text
        assert "not found" in text
        assert "market-0" in text
