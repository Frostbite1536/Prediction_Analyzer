# tests/mcp/test_tax_tools.py
"""Tests for MCP tax tools."""

import json
import asyncio

import pytest

from prediction_mcp.tools import tax_tools
from prediction_mcp.state import session


class TestTaxReport:
    def test_no_trades_error(self):
        result = asyncio.run(
            tax_tools.handle_tool(
                "get_tax_report",
                {
                    "tax_year": 2024,
                },
            )
        )
        assert "No trades loaded" in result[0].text

    def test_missing_tax_year(self, loaded_session):
        result = asyncio.run(tax_tools.handle_tool("get_tax_report", {}))
        assert "tax_year is required" in result[0].text

    def test_fifo_report(self, loaded_session):
        result = asyncio.run(
            tax_tools.handle_tool(
                "get_tax_report",
                {
                    "tax_year": 2024,
                    "cost_basis_method": "fifo",
                },
            )
        )
        data = json.loads(result[0].text)
        assert data["tax_year"] == 2024
        assert data["method"] == "fifo"
        assert "short_term_gains" in data
        assert "long_term_gains" in data
        assert "transactions" in data

    def test_lifo_report(self, loaded_session):
        result = asyncio.run(
            tax_tools.handle_tool(
                "get_tax_report",
                {
                    "tax_year": 2024,
                    "cost_basis_method": "lifo",
                },
            )
        )
        data = json.loads(result[0].text)
        assert data["method"] == "lifo"

    def test_average_report(self, loaded_session):
        result = asyncio.run(
            tax_tools.handle_tool(
                "get_tax_report",
                {
                    "tax_year": 2024,
                    "cost_basis_method": "average",
                },
            )
        )
        data = json.loads(result[0].text)
        assert data["method"] == "average"

    def test_default_method_is_fifo(self, loaded_session):
        result = asyncio.run(
            tax_tools.handle_tool(
                "get_tax_report",
                {
                    "tax_year": 2024,
                },
            )
        )
        data = json.loads(result[0].text)
        assert data["method"] == "fifo"

    def test_invalid_cost_basis_method(self, loaded_session):
        result = asyncio.run(
            tax_tools.handle_tool(
                "get_tax_report",
                {
                    "tax_year": 2024,
                    "cost_basis_method": "invalid",
                },
            )
        )
        assert "Invalid cost basis method" in result[0].text
