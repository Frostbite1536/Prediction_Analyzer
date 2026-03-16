# tests/mcp/test_portfolio_tools.py
"""Tests for MCP portfolio tools."""

import json
import asyncio


from prediction_mcp.tools import portfolio_tools


class TestOpenPositions:
    def test_no_trades_error(self):
        result = asyncio.run(portfolio_tools.handle_tool("get_open_positions", {}))
        assert "No trades loaded" in result[0].text

    def test_positions_returned(self, loaded_session):
        result = asyncio.run(portfolio_tools.handle_tool("get_open_positions", {}))
        data = json.loads(result[0].text)
        assert isinstance(data, list)


class TestConcentrationRisk:
    def test_no_trades_error(self):
        result = asyncio.run(portfolio_tools.handle_tool("get_concentration_risk", {}))
        assert "No trades loaded" in result[0].text

    def test_concentration_returned(self, loaded_session):
        result = asyncio.run(portfolio_tools.handle_tool("get_concentration_risk", {}))
        data = json.loads(result[0].text)
        assert "total_markets" in data
        assert "herfindahl_index" in data
        assert "top_3_concentration_pct" in data
        assert "markets" in data


class TestDrawdownAnalysis:
    def test_no_trades_error(self):
        result = asyncio.run(portfolio_tools.handle_tool("get_drawdown_analysis", {}))
        assert "No trades loaded" in result[0].text

    def test_drawdown_returned(self, loaded_session):
        result = asyncio.run(portfolio_tools.handle_tool("get_drawdown_analysis", {}))
        data = json.loads(result[0].text)
        assert "max_drawdown_amount" in data
        assert "is_in_drawdown" in data
        assert "drawdown_periods" in data


class TestComparePeriods:
    def test_no_trades_error(self):
        result = asyncio.run(
            portfolio_tools.handle_tool(
                "compare_periods",
                {
                    "period_1_start": "2024-01-01",
                    "period_1_end": "2024-01-05",
                    "period_2_start": "2024-01-06",
                    "period_2_end": "2024-01-10",
                },
            )
        )
        assert "No trades loaded" in result[0].text

    def test_comparison_returned(self, loaded_session):
        result = asyncio.run(
            portfolio_tools.handle_tool(
                "compare_periods",
                {
                    "period_1_start": "2024-01-01",
                    "period_1_end": "2024-01-05",
                    "period_2_start": "2024-01-06",
                    "period_2_end": "2024-01-10",
                },
            )
        )
        data = json.loads(result[0].text)
        assert "period_1" in data
        assert "period_2" in data
        assert "changes" in data

    def test_missing_dates_error(self, loaded_session):
        result = asyncio.run(
            portfolio_tools.handle_tool(
                "compare_periods",
                {
                    "period_1_start": "2024-01-01",
                },
            )
        )
        assert "required" in result[0].text

    def test_invalid_date_format(self, loaded_session):
        result = asyncio.run(
            portfolio_tools.handle_tool(
                "compare_periods",
                {
                    "period_1_start": "bad-date",
                    "period_1_end": "2024-01-05",
                    "period_2_start": "2024-01-06",
                    "period_2_end": "2024-01-10",
                },
            )
        )
        assert "YYYY-MM-DD" in result[0].text
