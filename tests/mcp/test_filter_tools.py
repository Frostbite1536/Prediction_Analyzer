# tests/mcp/test_filter_tools.py
"""Tests for MCP filter tools."""
import json
import asyncio

import pytest

from prediction_mcp.tools import filter_tools
from prediction_mcp.state import session


class TestFilterTrades:
    def test_no_trades_error(self):
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {}))
        assert "No trades loaded" in result[0].text

    def test_filter_by_side(self, loaded_session):
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {
            "sides": ["YES"],
        }))
        data = json.loads(result[0].text)
        assert data["original_count"] == 10
        assert data["filtered_count"] < 10

    def test_filter_by_trade_type(self, loaded_session):
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {
            "trade_types": ["Buy"],
        }))
        data = json.loads(result[0].text)
        assert data["filtered_count"] == 5  # half are buys

    def test_filter_by_date(self, loaded_session):
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {
            "start_date": "2024-01-05",
        }))
        data = json.loads(result[0].text)
        assert data["filtered_count"] < 10

    def test_clear_filters(self, loaded_session):
        # Apply a filter
        asyncio.run(filter_tools.handle_tool("filter_trades", {
            "trade_types": ["Buy"],
        }))
        assert len(session.filtered_trades) == 5

        # Clear
        result = asyncio.run(filter_tools.handle_tool("filter_trades", {
            "clear": True,
        }))
        data = json.loads(result[0].text)
        assert data["filtered_count"] == 10
        assert session.active_filters == {}

    def test_active_filters_tracked(self, loaded_session):
        asyncio.run(filter_tools.handle_tool("filter_trades", {
            "sides": ["YES"],
            "min_pnl": 0.5,
        }))
        data = json.loads(asyncio.run(filter_tools.handle_tool("filter_trades", {
            "sides": ["YES"],
        }))[0].text)
        assert "sides" in data["active_filters"]
