# tests/mcp/test_analysis_tools.py
"""Tests for MCP analysis tools."""
import json
import asyncio

import pytest

from prediction_mcp.tools import analysis_tools
from prediction_mcp.state import session


class TestGlobalSummary:
    def test_no_trades_error(self):
        result = asyncio.run(analysis_tools.handle_tool("get_global_summary", {}))
        assert "No trades loaded" in result[0].text

    def test_summary_with_trades(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_global_summary", {}))
        data = json.loads(result[0].text)
        assert "total_trades" in data
        assert data["total_trades"] == 10
        assert "total_pnl" in data
        assert "win_rate" in data

    def test_summary_with_date_filter(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_global_summary", {
            "start_date": "2024-01-03",
            "end_date": "2024-01-06",
        }))
        data = json.loads(result[0].text)
        assert data["total_trades"] < 10


class TestMarketSummary:
    def test_no_trades_error(self):
        result = asyncio.run(analysis_tools.handle_tool("get_market_summary", {
            "market_slug": "test",
        }))
        assert "No trades loaded" in result[0].text

    def test_missing_market_slug(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_market_summary", {}))
        assert "market_slug is required" in result[0].text

    def test_market_not_found(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_market_summary", {
            "market_slug": "nonexistent-market",
        }))
        assert "No trades found" in result[0].text

    def test_valid_market_summary(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_market_summary", {
            "market_slug": "market-0",
        }))
        data = json.loads(result[0].text)
        assert "market_title" in data
        assert data["total_trades"] > 0


class TestAdvancedMetrics:
    def test_no_trades_error(self):
        result = asyncio.run(analysis_tools.handle_tool("get_advanced_metrics", {}))
        assert "No trades loaded" in result[0].text

    def test_metrics_returned(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_advanced_metrics", {}))
        data = json.loads(result[0].text)
        assert "sharpe_ratio" in data
        assert "sortino_ratio" in data
        assert "max_drawdown" in data
        assert "profit_factor" in data

    def test_metrics_for_specific_market(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_advanced_metrics", {
            "market_slug": "market-0",
        }))
        data = json.loads(result[0].text)
        assert "sharpe_ratio" in data


class TestMarketBreakdown:
    def test_no_trades_error(self):
        result = asyncio.run(analysis_tools.handle_tool("get_market_breakdown", {}))
        assert "No trades loaded" in result[0].text

    def test_breakdown_returns_list(self, loaded_session):
        result = asyncio.run(analysis_tools.handle_tool("get_market_breakdown", {}))
        data = json.loads(result[0].text)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "market_slug" in data[0]
        assert "pnl" in data[0]
        assert "trade_count" in data[0]
