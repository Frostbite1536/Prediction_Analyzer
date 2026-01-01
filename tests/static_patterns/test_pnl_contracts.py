# tests/static_patterns/test_pnl_contracts.py
"""
PnL Calculation Contract Tests

These tests verify that PnL calculation functions maintain their
behavior contracts. PnL calculations must be accurate and consistent.
"""
import pytest
import pandas as pd
from datetime import datetime


class TestCalculatePnLContracts:
    """Verify calculate_pnl behavior contracts."""

    def test_returns_dataframe(self, sample_trades_list):
        """calculate_pnl should return a DataFrame."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl(sample_trades_list)
        assert isinstance(result, pd.DataFrame)

    def test_empty_input_returns_empty_dataframe(self, empty_trades_list):
        """Empty input should return empty DataFrame."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl(empty_trades_list)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_dataframe_has_trade_pnl_column(self, sample_trades_list):
        """DataFrame should have trade_pnl column."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl(sample_trades_list)
        assert "trade_pnl" in result.columns

    def test_dataframe_has_cumulative_pnl_column(self, sample_trades_list):
        """DataFrame should have cumulative_pnl column."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl(sample_trades_list)
        assert "cumulative_pnl" in result.columns

    def test_dataframe_has_exposure_column(self, sample_trades_list):
        """DataFrame should have exposure column."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl(sample_trades_list)
        assert "exposure" in result.columns

    def test_dataframe_row_count_matches_input(self, sample_trades_list):
        """DataFrame should have same row count as input."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl(sample_trades_list)
        assert len(result) == len(sample_trades_list)

    def test_cumulative_pnl_is_cumsum_of_trade_pnl(self, sample_trades_list):
        """cumulative_pnl should be cumulative sum of trade_pnl."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl(sample_trades_list)
        expected_cumsum = result["trade_pnl"].cumsum()
        pd.testing.assert_series_equal(
            result["cumulative_pnl"],
            expected_cumsum,
            check_names=False
        )

    def test_sorted_by_timestamp(self, sample_trades_list):
        """Result should be sorted by timestamp."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl(sample_trades_list)
        timestamps = result["timestamp"].tolist()
        assert timestamps == sorted(timestamps)


class TestCalculateGlobalPnLSummaryContracts:
    """Verify calculate_global_pnl_summary behavior contracts."""

    def test_returns_dict(self, sample_trades_list):
        """calculate_global_pnl_summary should return a dict."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        assert isinstance(result, dict)

    def test_empty_input_returns_zeros(self, empty_trades_list):
        """Empty input should return dict with zero values."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(empty_trades_list)
        assert result["total_trades"] == 0
        assert result["total_pnl"] == 0.0

    def test_has_total_trades_key(self, sample_trades_list):
        """Result should have total_trades key."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        assert "total_trades" in result
        assert result["total_trades"] == len(sample_trades_list)

    def test_has_total_pnl_key(self, sample_trades_list):
        """Result should have total_pnl key."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        assert "total_pnl" in result

    def test_has_win_rate_key(self, sample_trades_list):
        """Result should have win_rate key."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        assert "win_rate" in result

    def test_has_winning_trades_key(self, sample_trades_list):
        """Result should have winning_trades key."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        assert "winning_trades" in result

    def test_has_losing_trades_key(self, sample_trades_list):
        """Result should have losing_trades key."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        assert "losing_trades" in result

    def test_total_pnl_is_sum(self, sample_trades_list):
        """total_pnl should equal sum of all trade PnLs."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        expected = sum(t.pnl for t in sample_trades_list)
        assert abs(result["total_pnl"] - expected) < 0.01

    def test_winning_plus_losing_plus_breakeven_equals_total(self, sample_trades_list):
        """Sum of win/lose/breakeven should equal total trades."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        count_sum = (
            result["winning_trades"] +
            result["losing_trades"] +
            result.get("breakeven_trades", 0)
        )
        assert count_sum == result["total_trades"]

    def test_all_winning_trades(self, winning_trades):
        """All winning trades should have 100% win rate (excl breakeven)."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(winning_trades)
        assert result["winning_trades"] == len(winning_trades)
        assert result["losing_trades"] == 0
        assert result["win_rate"] == 100.0

    def test_all_losing_trades(self, losing_trades):
        """All losing trades should have 0% win rate."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(losing_trades)
        assert result["losing_trades"] == len(losing_trades)
        assert result["winning_trades"] == 0
        assert result["win_rate"] == 0.0


class TestCalculateMarketPnLContracts:
    """Verify calculate_market_pnl behavior contracts."""

    def test_returns_dict(self, multi_market_trades):
        """calculate_market_pnl should return a dict."""
        from prediction_analyzer.pnl import calculate_market_pnl

        result = calculate_market_pnl(multi_market_trades)
        assert isinstance(result, dict)

    def test_empty_input_returns_empty_dict(self, empty_trades_list):
        """Empty input should return empty dict."""
        from prediction_analyzer.pnl import calculate_market_pnl

        result = calculate_market_pnl(empty_trades_list)
        assert result == {}

    def test_keys_are_market_slugs(self, multi_market_trades):
        """Dict keys should be market slugs."""
        from prediction_analyzer.pnl import calculate_market_pnl

        result = calculate_market_pnl(multi_market_trades)
        expected_slugs = {t.market_slug for t in multi_market_trades}
        assert set(result.keys()) == expected_slugs

    def test_market_stats_have_required_keys(self, multi_market_trades):
        """Each market's stats should have required keys."""
        from prediction_analyzer.pnl import calculate_market_pnl

        result = calculate_market_pnl(multi_market_trades)
        required_keys = {"market_name", "total_volume", "total_pnl", "trade_count"}

        for slug, stats in result.items():
            assert required_keys.issubset(set(stats.keys()))

    def test_trade_count_is_correct(self, multi_market_trades):
        """Trade count per market should be correct."""
        from prediction_analyzer.pnl import calculate_market_pnl

        result = calculate_market_pnl(multi_market_trades)

        for slug, stats in result.items():
            expected_count = len([
                t for t in multi_market_trades if t.market_slug == slug
            ])
            assert stats["trade_count"] == expected_count


class TestCalculateMarketPnLSummaryContracts:
    """Verify calculate_market_pnl_summary behavior contracts."""

    def test_returns_dict(self, sample_trades_list):
        """calculate_market_pnl_summary should return a dict."""
        from prediction_analyzer.pnl import calculate_market_pnl_summary

        result = calculate_market_pnl_summary(sample_trades_list)
        assert isinstance(result, dict)

    def test_empty_input_returns_defaults(self, empty_trades_list):
        """Empty input should return dict with default values."""
        from prediction_analyzer.pnl import calculate_market_pnl_summary

        result = calculate_market_pnl_summary(empty_trades_list)
        assert result["total_trades"] == 0
        assert result["total_pnl"] == 0.0

    def test_has_market_title(self, sample_trades_list):
        """Result should have market_title."""
        from prediction_analyzer.pnl import calculate_market_pnl_summary

        result = calculate_market_pnl_summary(sample_trades_list)
        assert "market_title" in result

    def test_has_required_keys(self, sample_trades_list):
        """Result should have all required keys."""
        from prediction_analyzer.pnl import calculate_market_pnl_summary

        result = calculate_market_pnl_summary(sample_trades_list)
        required_keys = {
            "market_title", "total_trades", "total_pnl",
            "avg_pnl", "winning_trades", "losing_trades", "win_rate"
        }
        assert required_keys.issubset(set(result.keys()))


class TestPnLCalculationAccuracy:
    """Verify PnL calculations are mathematically correct."""

    def test_simple_pnl_sum(self, sample_trade_factory):
        """Simple case: PnL should sum correctly."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        trades = [
            sample_trade_factory(pnl=10.0),
            sample_trade_factory(pnl=20.0),
            sample_trade_factory(pnl=-5.0),
        ]

        result = calculate_global_pnl_summary(trades)
        assert result["total_pnl"] == 25.0

    def test_average_pnl(self, sample_trade_factory):
        """Average PnL should be correctly calculated."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        trades = [
            sample_trade_factory(pnl=10.0),
            sample_trade_factory(pnl=20.0),
            sample_trade_factory(pnl=30.0),
        ]

        result = calculate_global_pnl_summary(trades)
        assert result["avg_pnl"] == 20.0

    def test_win_rate_calculation(self, sample_trade_factory):
        """Win rate should be correctly calculated."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        # 2 wins, 2 losses = 50% win rate
        trades = [
            sample_trade_factory(pnl=10.0),
            sample_trade_factory(pnl=20.0),
            sample_trade_factory(pnl=-5.0),
            sample_trade_factory(pnl=-15.0),
        ]

        result = calculate_global_pnl_summary(trades)
        assert result["win_rate"] == 50.0

    def test_roi_calculation(self, sample_trade_factory):
        """ROI should be correctly calculated."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        # Buy trades with costs, resulting in positive PnL
        trades = [
            sample_trade_factory(type="Buy", cost=100.0, pnl=20.0),
            sample_trade_factory(type="Buy", cost=100.0, pnl=30.0),
        ]

        result = calculate_global_pnl_summary(trades)
        # Total invested: 200, Total PnL: 50, ROI: 25%
        assert result["roi"] == 25.0
