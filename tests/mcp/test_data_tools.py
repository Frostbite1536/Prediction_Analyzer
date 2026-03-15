# tests/mcp/test_data_tools.py
"""Tests for MCP data tools."""

import json
import asyncio


from prediction_mcp.tools import data_tools
from prediction_mcp.state import session
from .conftest import EXAMPLE_TRADES_PATH


class TestLoadTrades:
    def test_load_from_file(self):
        result = asyncio.run(
            data_tools.handle_tool(
                "load_trades",
                {
                    "file_path": EXAMPLE_TRADES_PATH,
                },
            )
        )
        assert result is not None
        data = json.loads(result[0].text)
        assert data["trade_count"] > 0
        assert "markets" in data
        assert session.has_trades

    def test_missing_file_path(self):
        result = asyncio.run(data_tools.handle_tool("load_trades", {}))
        assert "file_path is required" in result[0].text

    def test_nonexistent_file(self):
        result = asyncio.run(
            data_tools.handle_tool(
                "load_trades",
                {
                    "file_path": "/nonexistent/file.json",
                },
            )
        )
        assert "File not found" in result[0].text

    def test_session_updated_after_load(self):
        asyncio.run(
            data_tools.handle_tool(
                "load_trades",
                {
                    "file_path": EXAMPLE_TRADES_PATH,
                },
            )
        )
        assert session.has_trades
        # Sources should contain provider names (e.g. "limitless"), not file paths
        assert len(session.sources) > 0
        assert all(not s.startswith("file:") for s in session.sources)
        assert len(session.filtered_trades) == len(session.trades)


class TestListMarkets:
    def test_no_trades_error(self):
        result = asyncio.run(data_tools.handle_tool("list_markets", {}))
        assert "No trades loaded" in result[0].text

    def test_list_markets_after_load(self):
        asyncio.run(
            data_tools.handle_tool(
                "load_trades",
                {
                    "file_path": EXAMPLE_TRADES_PATH,
                },
            )
        )
        result = asyncio.run(data_tools.handle_tool("list_markets", {}))
        data = json.loads(result[0].text)
        assert len(data) > 0
        assert "slug" in data[0]
        assert "title" in data[0]
        assert "trade_count" in data[0]


class TestGetTradeDetails:
    def test_no_trades_error(self):
        result = asyncio.run(data_tools.handle_tool("get_trade_details", {}))
        assert "No trades loaded" in result[0].text

    def test_basic_trade_details(self, loaded_session):
        result = asyncio.run(
            data_tools.handle_tool(
                "get_trade_details",
                {
                    "limit": 3,
                },
            )
        )
        data = json.loads(result[0].text)
        assert data["total"] == 10
        assert len(data["trades"]) == 3

    def test_pagination(self, loaded_session):
        result = asyncio.run(
            data_tools.handle_tool(
                "get_trade_details",
                {
                    "limit": 2,
                    "offset": 5,
                },
            )
        )
        data = json.loads(result[0].text)
        assert len(data["trades"]) == 2
        assert data["offset"] == 5

    def test_sort_by_pnl(self, loaded_session):
        result = asyncio.run(
            data_tools.handle_tool(
                "get_trade_details",
                {
                    "sort_by": "pnl",
                    "sort_order": "desc",
                    "limit": 3,
                },
            )
        )
        data = json.loads(result[0].text)
        pnls = [t["pnl"] for t in data["trades"]]
        assert pnls == sorted(pnls, reverse=True)

    def test_filter_by_market(self, loaded_session):
        result = asyncio.run(
            data_tools.handle_tool(
                "get_trade_details",
                {
                    "market_slug": "market-0",
                },
            )
        )
        data = json.loads(result[0].text)
        assert all(t["market_slug"] == "market-0" for t in data["trades"])


class TestInputValidation:
    def test_invalid_sort_field(self, loaded_session):
        result = asyncio.run(
            data_tools.handle_tool(
                "get_trade_details",
                {
                    "sort_by": "invalid_field",
                },
            )
        )
        assert "Invalid sort field" in result[0].text

    def test_negative_limit(self, loaded_session):
        result = asyncio.run(
            data_tools.handle_tool(
                "get_trade_details",
                {
                    "limit": -1,
                },
            )
        )
        assert "Invalid limit" in result[0].text

    def test_negative_offset(self, loaded_session):
        result = asyncio.run(
            data_tools.handle_tool(
                "get_trade_details",
                {
                    "offset": -5,
                },
            )
        )
        assert "Invalid offset" in result[0].text


class TestUnknownTool:
    def test_unknown_tool_returns_none(self):
        result = asyncio.run(data_tools.handle_tool("nonexistent_tool", {}))
        assert result is None
