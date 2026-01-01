# tests/static_patterns/test_filter_contracts.py
"""
Filter Contract Tests

These tests verify that filter functions maintain their behavior contracts.
Filters should always:
1. Return a list (possibly empty)
2. Return a subset of input trades
3. Not modify the original trades
4. Handle edge cases gracefully
"""
import pytest
from datetime import datetime, timedelta


class TestFilterByDateContracts:
    """Verify filter_by_date behavior contracts."""

    def test_returns_list(self, sample_trades_list):
        """filter_by_date should always return a list."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(sample_trades_list, start="2024-01-01")
        assert isinstance(result, list)

    def test_returns_subset_of_input(self, sample_trades_list):
        """Filtered trades should be a subset of input."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(sample_trades_list, start="2024-06-01")
        for trade in result:
            assert trade in sample_trades_list

    def test_does_not_modify_original(self, sample_trades_list):
        """Original trades should not be modified."""
        from prediction_analyzer.filters import filter_by_date

        original_count = len(sample_trades_list)
        filter_by_date(sample_trades_list, start="2024-06-01")

        assert len(sample_trades_list) == original_count

    def test_no_filters_returns_all(self, sample_trades_list):
        """No start/end filters should return all trades."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(sample_trades_list)
        assert len(result) == len(sample_trades_list)

    def test_empty_input_returns_empty(self, empty_trades_list):
        """Empty input should return empty list."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(empty_trades_list, start="2024-01-01")
        assert result == []

    def test_start_date_filtering(self, trades_spanning_year):
        """Start date should exclude earlier trades."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(trades_spanning_year, start="2024-06-01")
        for trade in result:
            assert trade.timestamp >= datetime(2024, 6, 1)

    def test_end_date_filtering(self, trades_spanning_year):
        """End date should exclude later trades."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(trades_spanning_year, end="2024-06-30")
        for trade in result:
            assert trade.timestamp <= datetime(2024, 6, 30, 23, 59, 59)

    def test_date_range_filtering(self, trades_spanning_year):
        """Date range should filter to trades within range."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(
            trades_spanning_year,
            start="2024-03-01",
            end="2024-08-31"
        )
        for trade in result:
            assert trade.timestamp >= datetime(2024, 3, 1)
            assert trade.timestamp <= datetime(2024, 8, 31, 23, 59, 59)


class TestFilterByTradeTypeContracts:
    """Verify filter_by_trade_type behavior contracts."""

    def test_returns_list(self, sample_trades_list):
        """filter_by_trade_type should always return a list."""
        from prediction_analyzer.filters import filter_by_trade_type

        result = filter_by_trade_type(sample_trades_list, types=["Buy"])
        assert isinstance(result, list)

    def test_returns_subset_of_input(self, sample_trades_list):
        """Filtered trades should be a subset of input."""
        from prediction_analyzer.filters import filter_by_trade_type

        result = filter_by_trade_type(sample_trades_list, types=["Buy"])
        for trade in result:
            assert trade in sample_trades_list

    def test_does_not_modify_original(self, sample_trades_list):
        """Original trades should not be modified."""
        from prediction_analyzer.filters import filter_by_trade_type

        original_count = len(sample_trades_list)
        filter_by_trade_type(sample_trades_list, types=["Buy"])

        assert len(sample_trades_list) == original_count

    def test_no_filter_returns_all(self, sample_trades_list):
        """No types filter should return all trades."""
        from prediction_analyzer.filters import filter_by_trade_type

        result = filter_by_trade_type(sample_trades_list)
        assert len(result) == len(sample_trades_list)

    def test_empty_input_returns_empty(self, empty_trades_list):
        """Empty input should return empty list."""
        from prediction_analyzer.filters import filter_by_trade_type

        result = filter_by_trade_type(empty_trades_list, types=["Buy"])
        assert result == []

    def test_single_type_filter(self, all_trade_types):
        """Single type filter should only return matching trades."""
        from prediction_analyzer.filters import filter_by_trade_type

        result = filter_by_trade_type(all_trade_types, types=["Buy"])
        for trade in result:
            assert trade.type == "Buy"

    def test_multiple_types_filter(self, all_trade_types):
        """Multiple types filter should return all matching."""
        from prediction_analyzer.filters import filter_by_trade_type

        types = ["Buy", "Sell", "Market Buy"]
        result = filter_by_trade_type(all_trade_types, types=types)
        for trade in result:
            assert trade.type in types

    def test_nonexistent_type_returns_empty(self, sample_trades_list):
        """Non-existent type should return empty list."""
        from prediction_analyzer.filters import filter_by_trade_type

        result = filter_by_trade_type(
            sample_trades_list,
            types=["NonExistentType"]
        )
        assert result == []


class TestFilterBySideContracts:
    """Verify filter_by_side behavior contracts."""

    def test_returns_list(self, sample_trades_list):
        """filter_by_side should always return a list."""
        from prediction_analyzer.filters import filter_by_side

        result = filter_by_side(sample_trades_list, sides=["YES"])
        assert isinstance(result, list)

    def test_returns_subset_of_input(self, sample_trades_list):
        """Filtered trades should be a subset of input."""
        from prediction_analyzer.filters import filter_by_side

        result = filter_by_side(sample_trades_list, sides=["YES"])
        for trade in result:
            assert trade in sample_trades_list

    def test_does_not_modify_original(self, sample_trades_list):
        """Original trades should not be modified."""
        from prediction_analyzer.filters import filter_by_side

        original_count = len(sample_trades_list)
        filter_by_side(sample_trades_list, sides=["YES"])

        assert len(sample_trades_list) == original_count

    def test_no_filter_returns_all(self, sample_trades_list):
        """No sides filter should return all trades."""
        from prediction_analyzer.filters import filter_by_side

        result = filter_by_side(sample_trades_list)
        assert len(result) == len(sample_trades_list)

    def test_empty_input_returns_empty(self, empty_trades_list):
        """Empty input should return empty list."""
        from prediction_analyzer.filters import filter_by_side

        result = filter_by_side(empty_trades_list, sides=["YES"])
        assert result == []

    def test_yes_side_filter(self, both_sides_trades):
        """YES filter should only return YES trades."""
        from prediction_analyzer.filters import filter_by_side

        result = filter_by_side(both_sides_trades, sides=["YES"])
        for trade in result:
            assert trade.side == "YES"

    def test_no_side_filter(self, both_sides_trades):
        """NO filter should only return NO trades."""
        from prediction_analyzer.filters import filter_by_side

        result = filter_by_side(both_sides_trades, sides=["NO"])
        for trade in result:
            assert trade.side == "NO"

    def test_both_sides_filter(self, both_sides_trades):
        """Both sides filter should return all trades."""
        from prediction_analyzer.filters import filter_by_side

        result = filter_by_side(both_sides_trades, sides=["YES", "NO"])
        assert len(result) == len(both_sides_trades)


class TestFilterByPnLContracts:
    """Verify filter_by_pnl behavior contracts."""

    def test_returns_list(self, sample_trades_list):
        """filter_by_pnl should always return a list."""
        from prediction_analyzer.filters import filter_by_pnl

        result = filter_by_pnl(sample_trades_list, min_pnl=0.0)
        assert isinstance(result, list)

    def test_returns_subset_of_input(self, sample_trades_list):
        """Filtered trades should be a subset of input."""
        from prediction_analyzer.filters import filter_by_pnl

        result = filter_by_pnl(sample_trades_list, min_pnl=0.0)
        for trade in result:
            assert trade in sample_trades_list

    def test_does_not_modify_original(self, sample_trades_list):
        """Original trades should not be modified."""
        from prediction_analyzer.filters import filter_by_pnl

        original_count = len(sample_trades_list)
        filter_by_pnl(sample_trades_list, min_pnl=0.0)

        assert len(sample_trades_list) == original_count

    def test_no_filter_returns_all(self, sample_trades_list):
        """No pnl filter should return all trades."""
        from prediction_analyzer.filters import filter_by_pnl

        result = filter_by_pnl(sample_trades_list)
        assert len(result) == len(sample_trades_list)

    def test_empty_input_returns_empty(self, empty_trades_list):
        """Empty input should return empty list."""
        from prediction_analyzer.filters import filter_by_pnl

        result = filter_by_pnl(empty_trades_list, min_pnl=0.0)
        assert result == []

    def test_min_pnl_filter(self, sample_trades_list):
        """min_pnl filter should exclude lower PnL trades."""
        from prediction_analyzer.filters import filter_by_pnl

        result = filter_by_pnl(sample_trades_list, min_pnl=0.0)
        for trade in result:
            assert trade.pnl >= 0.0

    def test_max_pnl_filter(self, sample_trades_list):
        """max_pnl filter should exclude higher PnL trades."""
        from prediction_analyzer.filters import filter_by_pnl

        result = filter_by_pnl(sample_trades_list, max_pnl=10.0)
        for trade in result:
            assert trade.pnl <= 10.0

    def test_pnl_range_filter(self, sample_trades_list):
        """PnL range should filter to trades within range."""
        from prediction_analyzer.filters import filter_by_pnl

        result = filter_by_pnl(sample_trades_list, min_pnl=-5.0, max_pnl=10.0)
        for trade in result:
            assert -5.0 <= trade.pnl <= 10.0


class TestFilterChaining:
    """Verify filters can be chained correctly."""

    def test_chained_filters(self, sample_trades_list):
        """Filters should be chainable."""
        from prediction_analyzer.filters import (
            filter_by_date,
            filter_by_trade_type,
            filter_by_side,
            filter_by_pnl
        )

        result = sample_trades_list
        result = filter_by_date(result, start="2024-01-01")
        result = filter_by_trade_type(result, types=["Buy", "Market Buy"])
        result = filter_by_side(result, sides=["YES"])
        result = filter_by_pnl(result, min_pnl=-10.0)

        assert isinstance(result, list)
        # Result should be subset
        for trade in result:
            assert trade in sample_trades_list
