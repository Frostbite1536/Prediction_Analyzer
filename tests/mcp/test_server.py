# tests/mcp/test_server.py
"""Tests for MCP server dispatch logic."""
import asyncio

import pytest
from mcp import types

from prediction_mcp.server import _TOOL_MODULES, list_tools, call_tool
from prediction_mcp.state import session
from .conftest import make_trades


class TestToolAggregation:
    def test_all_modules_registered(self):
        assert len(_TOOL_MODULES) == 7

    def test_list_tools_returns_all(self):
        tools = asyncio.run(list_tools())
        assert len(tools) == 17
        names = [t.name for t in tools]
        assert "load_trades" in names
        assert "get_tax_report" in names
        assert "generate_chart" in names

    def test_each_tool_has_schema(self):
        tools = asyncio.run(list_tools())
        for tool in tools:
            assert isinstance(tool, types.Tool)
            assert tool.inputSchema is not None


class TestToolDispatch:
    def test_unknown_tool(self):
        result = asyncio.run(call_tool("nonexistent_tool", {}))
        assert "Unknown tool" in result[0].text

    def test_dispatch_to_correct_module(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        result = asyncio.run(call_tool("list_markets", {}))
        assert result is not None
        assert len(result) > 0
