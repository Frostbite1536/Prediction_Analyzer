# tests/test_bugfixes_audit2.py
"""
Regression tests for bugs identified in the second codebase audit.

Bug #1: export_tools path traversal check rejects valid absolute paths
Bug #2: _apply_filters silently returns empty list when min_pnl > max_pnl
Bug #3: filter_trades stores empty string/list values in active_filters
"""

import json
import math
import os
import asyncio
import tempfile

import pytest

from datetime import datetime
from prediction_analyzer.trade_loader import Trade
from prediction_analyzer.exceptions import InvalidFilterError
from prediction_mcp.state import session

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trade(**kwargs):
    """Create a Trade with sensible defaults, overriding with kwargs."""
    defaults = {
        "market": "Test Market",
        "market_slug": "test-market",
        "timestamp": datetime(2024, 6, 15, 12, 0, 0),
        "price": 0.55,
        "shares": 10.0,
        "cost": 5.5,
        "type": "Buy",
        "side": "YES",
        "pnl": 0.0,
        "pnl_is_set": False,
        "source": "limitless",
        "currency": "USD",
    }
    defaults.update(kwargs)
    return Trade(**defaults)


# ===========================================================================
# Bug #1: export_tools path traversal check rejects valid absolute paths
# ===========================================================================


class TestExportPathTraversal:
    """export_trades should allow valid absolute paths like /tmp/foo.csv."""

    @pytest.fixture(autouse=True)
    def _setup_session(self):
        session.clear()
        session.trades = [_make_trade()]
        session.filtered_trades = list(session.trades)
        session.source = "test"
        yield
        session.clear()

    def test_absolute_tmp_path_allowed(self):
        """Absolute paths outside CWD (e.g. /tmp) should not be rejected."""
        from prediction_mcp.tools import export_tools

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name

        try:
            result = asyncio.run(
                export_tools.handle_tool(
                    "export_trades",
                    {
                        "format": "csv",
                        "output_path": path,
                    },
                )
            )
            data = json.loads(result[0].text)
            assert data["trade_count"] == 1
            assert data["format"] == "csv"
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_dotdot_path_rejected(self):
        """Paths with '..' components should still be rejected."""
        from prediction_mcp.tools import export_tools

        result = asyncio.run(
            export_tools.handle_tool(
                "export_trades",
                {
                    "format": "csv",
                    "output_path": "/tmp/../etc/test.csv",
                },
            )
        )
        assert "'..' " in result[0].text or "error" in result[0].text.lower()

    def test_relative_path_allowed(self):
        """A simple relative path should be allowed."""
        from prediction_mcp.tools import export_tools

        path = os.path.join(tempfile.gettempdir(), "test_export_rel.json")
        try:
            result = asyncio.run(
                export_tools.handle_tool(
                    "export_trades",
                    {
                        "format": "json",
                        "output_path": path,
                    },
                )
            )
            data = json.loads(result[0].text)
            assert data["trade_count"] == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)


# ===========================================================================
# Bug #2: _apply_filters silently returns empty when min_pnl > max_pnl
# ===========================================================================


class TestApplyFiltersMinMaxPnl:
    """apply_filters should raise InvalidFilterError when min_pnl > max_pnl."""

    def test_min_pnl_greater_than_max_pnl_raises(self):
        """min_pnl=100 and max_pnl=10 should raise, not silently return empty."""
        from prediction_mcp._apply_filters import apply_filters

        trades = [_make_trade(pnl=50.0)]
        with pytest.raises(InvalidFilterError, match="min_pnl.*must not exceed.*max_pnl"):
            apply_filters(trades, {"min_pnl": 100, "max_pnl": 10})

    def test_equal_min_max_pnl_allowed(self):
        """min_pnl == max_pnl should be allowed (exact match filter)."""
        from prediction_mcp._apply_filters import apply_filters

        trades = [
            _make_trade(pnl=5.0),
            _make_trade(pnl=10.0),
        ]
        result = apply_filters(trades, {"min_pnl": 5.0, "max_pnl": 5.0})
        assert len(result) == 1
        assert result[0].pnl == 5.0

    def test_valid_min_max_range(self):
        """Normal min < max should work correctly."""
        from prediction_mcp._apply_filters import apply_filters

        trades = [
            _make_trade(pnl=-5.0),
            _make_trade(pnl=5.0),
            _make_trade(pnl=15.0),
        ]
        result = apply_filters(trades, {"min_pnl": 0, "max_pnl": 10})
        assert len(result) == 1
        assert result[0].pnl == 5.0

    def test_only_min_pnl(self):
        """Only min_pnl should not trigger the validation."""
        from prediction_mcp._apply_filters import apply_filters

        trades = [_make_trade(pnl=5.0), _make_trade(pnl=-1.0)]
        result = apply_filters(trades, {"min_pnl": 0})
        assert len(result) == 1

    def test_only_max_pnl(self):
        """Only max_pnl should not trigger the validation."""
        from prediction_mcp._apply_filters import apply_filters

        trades = [_make_trade(pnl=5.0), _make_trade(pnl=-1.0)]
        result = apply_filters(trades, {"max_pnl": 0})
        assert len(result) == 1


# ===========================================================================
# Bug #3: filter_trades stores empty string/list values in active_filters
# ===========================================================================


class TestActiveFiltersNoEmpty:
    """filter_trades should not store empty strings or empty lists as active filters."""

    @pytest.fixture(autouse=True)
    def _setup_session(self):
        session.clear()
        session.trades = [_make_trade() for _ in range(5)]
        session.filtered_trades = list(session.trades)
        session.source = "test"
        yield
        session.clear()

    def test_empty_string_not_stored(self):
        """Empty string filter values should not appear in active_filters."""
        from prediction_mcp.tools import filter_tools

        result = asyncio.run(
            filter_tools.handle_tool(
                "filter_trades",
                {
                    "market_slug": "",
                    "start_date": "",
                },
            )
        )
        data = json.loads(result[0].text)
        assert "market_slug" not in data["active_filters"]
        assert "start_date" not in data["active_filters"]

    def test_empty_list_not_stored(self):
        """Empty list filter values should not appear in active_filters."""
        from prediction_mcp.tools import filter_tools

        result = asyncio.run(
            filter_tools.handle_tool(
                "filter_trades",
                {
                    "trade_types": [],
                    "sides": [],
                },
            )
        )
        data = json.loads(result[0].text)
        assert "trade_types" not in data["active_filters"]
        assert "sides" not in data["active_filters"]

    def test_valid_values_still_stored(self):
        """Non-empty filter values should still be stored."""
        from prediction_mcp.tools import filter_tools

        result = asyncio.run(
            filter_tools.handle_tool(
                "filter_trades",
                {
                    "sides": ["YES"],
                    "min_pnl": 0.0,
                },
            )
        )
        data = json.loads(result[0].text)
        assert "sides" in data["active_filters"]
        # 0.0 is a valid filter value (not empty)
        assert "min_pnl" in data["active_filters"]


# ===========================================================================
# Additional: _apply_filters combined filter tests (coverage gap)
# ===========================================================================


class TestApplyFiltersCombined:
    """Test multiple filters applied simultaneously."""

    def test_date_and_side_combined(self):
        """Date filter + side filter should work together."""
        from prediction_mcp._apply_filters import apply_filters

        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), side="YES"),
            _make_trade(timestamp=datetime(2024, 1, 5), side="NO"),
            _make_trade(timestamp=datetime(2024, 1, 10), side="YES"),
            _make_trade(timestamp=datetime(2024, 2, 1), side="YES"),
        ]
        result = apply_filters(
            trades,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-15",
                "sides": ["YES"],
            },
        )
        assert len(result) == 2

    def test_all_filters_at_once(self):
        """All filters applied at once should narrow correctly."""
        from prediction_mcp._apply_filters import apply_filters

        trades = [
            _make_trade(
                market_slug="m1",
                timestamp=datetime(2024, 3, 1),
                type="Buy",
                side="YES",
                pnl=5.0,
            ),
            _make_trade(
                market_slug="m1",
                timestamp=datetime(2024, 3, 2),
                type="Sell",
                side="YES",
                pnl=-2.0,
            ),
            _make_trade(
                market_slug="m2",
                timestamp=datetime(2024, 3, 1),
                type="Buy",
                side="NO",
                pnl=10.0,
            ),
        ]
        result = apply_filters(
            trades,
            {
                "market_slug": "m1",
                "start_date": "2024-03-01",
                "end_date": "2024-03-03",
                "trade_types": ["Buy"],
                "sides": ["YES"],
                "min_pnl": 0,
            },
        )
        assert len(result) == 1
        assert result[0].pnl == 5.0

    def test_no_filters_returns_all(self):
        """Empty arguments dict should return all trades."""
        from prediction_mcp._apply_filters import apply_filters

        trades = [_make_trade() for _ in range(5)]
        result = apply_filters(trades, {})
        assert len(result) == 5

    def test_filters_on_empty_trades(self):
        """Filtering empty trades list should return empty."""
        from prediction_mcp._apply_filters import apply_filters

        result = apply_filters([], {"sides": ["YES"]})
        assert result == []


# ===========================================================================
# Additional: Kalshi normalize_trade regression tests
# ===========================================================================


class TestKalshiNormalizeTrade:
    """Kalshi normalize_trade should handle both new and legacy price fields."""

    def _provider(self):
        from prediction_analyzer.providers.kalshi import KalshiProvider

        return KalshiProvider()

    def test_fixed_price_field_used_when_present(self):
        """yes_price_fixed (dollar string) should be used as-is."""
        p = self._provider()
        raw = {
            "ticker": "KX-TEST",
            "side": "yes",
            "yes_price_fixed": "0.5600",
            "yes_price": 56,
            "count_fp": "10.00",
            "action": "buy",
            "created_time": "2024-06-01T00:00:00Z",
            "fill_id": "f1",
        }
        trade = p.normalize_trade(raw)
        assert trade.price == 0.56
        assert trade.shares == 10.0

    def test_legacy_cents_field_divided_by_100(self):
        """When _fixed fields are absent, legacy integer cents should be /100."""
        p = self._provider()
        raw = {
            "ticker": "KX-TEST",
            "side": "yes",
            "yes_price": 56,
            "count": 10,
            "action": "buy",
            "created_time": "2024-06-01T00:00:00Z",
            "fill_id": "f2",
        }
        trade = p.normalize_trade(raw)
        assert trade.price == 0.56
        assert trade.shares == 10.0

    def test_no_side_defaults_to_yes(self):
        """Missing side field should default to YES."""
        p = self._provider()
        raw = {
            "ticker": "KX-TEST",
            "yes_price_fixed": "0.50",
            "count_fp": "5.00",
            "action": "buy",
            "created_time": 0,
            "fill_id": "f3",
        }
        trade = p.normalize_trade(raw)
        assert trade.side == "YES"

    def test_no_side_defaults_to_no(self):
        """Explicit 'no' side should result in NO."""
        p = self._provider()
        raw = {
            "ticker": "KX-TEST",
            "side": "no",
            "no_price_fixed": "0.40",
            "count_fp": "5.00",
            "action": "sell",
            "created_time": 0,
            "fill_id": "f4",
        }
        trade = p.normalize_trade(raw)
        assert trade.side == "NO"
        assert trade.price == 0.40

    def test_sell_cost_subtracts_fee(self):
        """For sell trades, cost = price*count - fee."""
        p = self._provider()
        raw = {
            "ticker": "KX-TEST",
            "side": "yes",
            "yes_price_fixed": "0.60",
            "count_fp": "100.00",
            "fee_cost": "2.00",
            "action": "sell",
            "created_time": 0,
            "fill_id": "f5",
        }
        trade = p.normalize_trade(raw)
        # 0.60 * 100 - 2.00 = 58.0
        assert abs(trade.cost - 58.0) < 0.01

    def test_buy_cost_adds_fee(self):
        """For buy trades, cost = price*count + fee."""
        p = self._provider()
        raw = {
            "ticker": "KX-TEST",
            "side": "yes",
            "yes_price_fixed": "0.60",
            "count_fp": "100.00",
            "fee_cost": "2.00",
            "action": "buy",
            "created_time": 0,
            "fill_id": "f6",
        }
        trade = p.normalize_trade(raw)
        # 0.60 * 100 + 2.00 = 62.0
        assert abs(trade.cost - 62.0) < 0.01

    def test_empty_fixed_falls_back_to_legacy(self):
        """Empty string in yes_price_fixed should fall back to yes_price."""
        p = self._provider()
        raw = {
            "ticker": "KX-TEST",
            "side": "yes",
            "yes_price_fixed": "",
            "yes_price": 60,
            "count_fp": "10.00",
            "action": "buy",
            "created_time": 0,
            "fill_id": "f7",
        }
        trade = p.normalize_trade(raw)
        assert trade.price == 0.60

    def test_whitespace_fixed_falls_back_to_legacy(self):
        """Whitespace-only yes_price_fixed should fall back to yes_price."""
        p = self._provider()
        raw = {
            "ticker": "KX-TEST",
            "side": "yes",
            "yes_price_fixed": "  ",
            "yes_price": 45,
            "count_fp": "10.00",
            "action": "buy",
            "created_time": 0,
            "fill_id": "f8",
        }
        trade = p.normalize_trade(raw)
        assert trade.price == 0.45

    def test_invalid_fixed_falls_back_to_legacy(self):
        """Non-numeric yes_price_fixed should fall back to yes_price."""
        p = self._provider()
        raw = {
            "ticker": "KX-TEST",
            "side": "yes",
            "yes_price_fixed": "N/A",
            "yes_price": 70,
            "count_fp": "10.00",
            "action": "buy",
            "created_time": 0,
            "fill_id": "f9",
        }
        trade = p.normalize_trade(raw)
        assert trade.price == 0.70


# ===========================================================================
# Additional: PnL calculator FIFO tests
# ===========================================================================


class TestPnlCalculatorFifo:
    """compute_realized_pnl FIFO matching correctness."""

    def test_basic_buy_sell_pair(self):
        """Simple buy then sell should compute correct PnL."""
        from prediction_analyzer.providers.pnl_calculator import compute_realized_pnl

        trades = [
            _make_trade(
                type="Buy", price=0.40, shares=10, cost=4.0, timestamp=datetime(2024, 1, 1)
            ),
            _make_trade(
                type="Sell", price=0.60, shares=10, cost=6.0, timestamp=datetime(2024, 1, 2)
            ),
        ]
        result = compute_realized_pnl(trades)
        sell = [t for t in result if t.type == "Sell"][0]
        # PnL = sell_revenue - buy_cost = 10*0.60 - 10*0.40 = 2.0
        assert abs(sell.pnl - 2.0) < 0.001
        assert sell.pnl_is_set is True

    def test_fifo_order_matters(self):
        """FIFO should match first buy against first sell."""
        from prediction_analyzer.providers.pnl_calculator import compute_realized_pnl

        trades = [
            _make_trade(type="Buy", price=0.30, shares=5, cost=1.5, timestamp=datetime(2024, 1, 1)),
            _make_trade(type="Buy", price=0.50, shares=5, cost=2.5, timestamp=datetime(2024, 1, 2)),
            _make_trade(
                type="Sell", price=0.60, shares=5, cost=3.0, timestamp=datetime(2024, 1, 3)
            ),
        ]
        result = compute_realized_pnl(trades)
        sell = [t for t in result if t.type == "Sell"][0]
        # FIFO: sell matches first buy at 0.30
        # PnL = 5*0.60 - 5*0.30 = 1.5
        assert abs(sell.pnl - 1.5) < 0.001

    def test_provider_pnl_not_overwritten(self):
        """Trades with pnl_is_set=True should keep their original PnL."""
        from prediction_analyzer.providers.pnl_calculator import compute_realized_pnl

        trades = [
            _make_trade(
                type="Buy", price=0.40, shares=10, cost=4.0, timestamp=datetime(2024, 1, 1)
            ),
            _make_trade(
                type="Sell",
                price=0.60,
                shares=10,
                cost=6.0,
                pnl=99.0,
                pnl_is_set=True,
                timestamp=datetime(2024, 1, 2),
            ),
        ]
        result = compute_realized_pnl(trades)
        sell = [t for t in result if t.type == "Sell"][0]
        assert sell.pnl == 99.0  # Not overwritten

    def test_empty_trades_returns_empty(self):
        """Empty input should return empty."""
        from prediction_analyzer.providers.pnl_calculator import compute_realized_pnl

        result = compute_realized_pnl([])
        assert result == []
