# tests/mcp/test_chart_tools.py
"""Tests for MCP chart tools."""

import asyncio


from prediction_mcp.tools import chart_tools


class TestGenerateChart:
    def test_no_trades_error(self):
        result = asyncio.run(
            chart_tools.handle_tool(
                "generate_chart",
                {
                    "market_slug": "market-0",
                    "chart_type": "simple",
                },
            )
        )
        assert "No trades loaded" in result[0].text

    def test_missing_market_slug(self, loaded_session):
        result = asyncio.run(
            chart_tools.handle_tool(
                "generate_chart",
                {
                    "chart_type": "simple",
                },
            )
        )
        assert "market_slug" in result[0].text

    def test_missing_chart_type(self, loaded_session):
        result = asyncio.run(
            chart_tools.handle_tool(
                "generate_chart",
                {
                    "market_slug": "market-0",
                },
            )
        )
        assert "chart_type" in result[0].text

    def test_invalid_chart_type(self, loaded_session):
        result = asyncio.run(
            chart_tools.handle_tool(
                "generate_chart",
                {
                    "market_slug": "market-0",
                    "chart_type": "invalid",
                },
            )
        )
        assert "Invalid chart type" in result[0].text

    def test_unknown_market(self, loaded_session):
        result = asyncio.run(
            chart_tools.handle_tool(
                "generate_chart",
                {
                    "market_slug": "nonexistent-market",
                    "chart_type": "simple",
                },
            )
        )
        assert "not found" in result[0].text


class TestGenerateDashboard:
    def test_no_trades_error(self):
        result = asyncio.run(chart_tools.handle_tool("generate_dashboard", {}))
        assert "No trades loaded" in result[0].text

    def test_unhandled_tool(self):
        result = asyncio.run(chart_tools.handle_tool("nonexistent", {}))
        assert result is None
