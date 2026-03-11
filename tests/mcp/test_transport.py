# tests/mcp/test_transport.py
"""Tests for MCP transport safety — no stdout pollution."""

import io
import sys
import json
import asyncio
import contextlib

import pytest

from prediction_mcp.tools import (
    data_tools,
    analysis_tools,
    filter_tools,
    export_tools,
    portfolio_tools,
    tax_tools,
)
from prediction_mcp.state import session
from .conftest import make_trades, EXAMPLE_TRADES_PATH


class TestNoStdoutWrites:
    """Verify no tool writes to stdout (would corrupt stdio transport)."""

    def _run_tool(self, module, name, args):
        """Run a tool and capture stdout."""
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            result = asyncio.run(module.handle_tool(name, args))
        stdout_output = stdout_capture.getvalue()
        assert stdout_output == "", f"Tool '{name}' wrote to stdout: {stdout_output!r}"
        return result

    def test_load_trades_no_stdout(self):
        self._run_tool(
            data_tools,
            "load_trades",
            {
                "file_path": EXAMPLE_TRADES_PATH,
            },
        )

    def test_list_markets_no_stdout(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        self._run_tool(data_tools, "list_markets", {})

    def test_global_summary_no_stdout(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        self._run_tool(analysis_tools, "get_global_summary", {})

    def test_filter_trades_no_stdout(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        self._run_tool(filter_tools, "filter_trades", {"sides": ["YES"]})

    def test_get_trade_details_no_stdout(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        self._run_tool(data_tools, "get_trade_details", {"limit": 2})

    def test_advanced_metrics_no_stdout(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        self._run_tool(analysis_tools, "get_advanced_metrics", {})

    def test_market_breakdown_no_stdout(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        self._run_tool(analysis_tools, "get_market_breakdown", {})

    def test_concentration_risk_no_stdout(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        self._run_tool(portfolio_tools, "get_concentration_risk", {})

    def test_drawdown_analysis_no_stdout(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        self._run_tool(portfolio_tools, "get_drawdown_analysis", {})

    def test_tax_report_no_stdout(self):
        session.trades = make_trades(5)
        session.filtered_trades = list(session.trades)
        self._run_tool(tax_tools, "get_tax_report", {"tax_year": 2024})

    def test_error_responses_no_stdout(self):
        """Error responses should not write to stdout either."""
        self._run_tool(data_tools, "list_markets", {})  # no trades loaded
        self._run_tool(analysis_tools, "get_global_summary", {})
        self._run_tool(filter_tools, "filter_trades", {})
