# tests/static_patterns/test_edge_cases.py
"""
Edge Case Tests

These tests verify that the codebase handles edge cases gracefully.
Edge cases often cause crashes or unexpected behavior when not handled.
"""
import pytest
from datetime import datetime, timezone
import numpy as np


class TestEmptyInputHandling:
    """Verify empty inputs are handled gracefully."""

    def test_calculate_pnl_empty_list(self):
        """calculate_pnl should handle empty list."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl([])
        assert len(result) == 0

    def test_calculate_global_pnl_summary_empty_list(self):
        """calculate_global_pnl_summary should handle empty list."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary([])
        assert result["total_trades"] == 0

    def test_calculate_market_pnl_empty_list(self):
        """calculate_market_pnl should handle empty list."""
        from prediction_analyzer.pnl import calculate_market_pnl

        result = calculate_market_pnl([])
        assert result == {}

    def test_filter_by_date_empty_list(self):
        """filter_by_date should handle empty list."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date([], start="2024-01-01")
        assert result == []

    def test_filter_by_trade_type_empty_list(self):
        """filter_by_trade_type should handle empty list."""
        from prediction_analyzer.filters import filter_by_trade_type

        result = filter_by_trade_type([], types=["Buy"])
        assert result == []


class TestSingleElementHandling:
    """Verify single-element lists are handled correctly."""

    def test_calculate_pnl_single_trade(self, sample_trade):
        """calculate_pnl should handle single trade."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl([sample_trade])
        assert len(result) == 1

    def test_calculate_global_pnl_summary_single_trade(self, sample_trade):
        """calculate_global_pnl_summary should handle single trade."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary([sample_trade])
        assert result["total_trades"] == 1

    def test_moving_average_single_value(self):
        """moving_average should handle single value."""
        from prediction_analyzer.utils.math_utils import moving_average

        result = moving_average([42.0], window=5)
        assert len(result) == 1


class TestZeroValueHandling:
    """Verify zero values are handled correctly."""

    def test_safe_divide_zero_denominator(self):
        """safe_divide should handle zero denominator."""
        from prediction_analyzer.utils.math_utils import safe_divide

        result = safe_divide(10.0, 0.0, default=-1.0)
        assert result == -1.0

    def test_calculate_roi_zero_investment(self):
        """calculate_roi should handle zero investment."""
        from prediction_analyzer.utils.math_utils import calculate_roi

        result = calculate_roi(100.0, 0.0)
        assert result == 0.0

    def test_trade_with_zero_values(self, sample_trade_factory):
        """Trade with zero values should be valid."""
        trade = sample_trade_factory(
            price=0.0,
            shares=0.0,
            cost=0.0,
            pnl=0.0
        )
        assert trade.price == 0.0
        assert trade.shares == 0.0

    def test_global_pnl_summary_zero_pnl_trades(self, breakeven_trades):
        """Global summary should handle all-zero PnL trades."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(breakeven_trades)
        assert result["total_pnl"] == 0.0
        assert result["winning_trades"] == 0
        assert result["losing_trades"] == 0


class TestTimestampEdgeCases:
    """Verify timestamp edge cases are handled."""

    def test_parse_timestamp_unix_epoch(self):
        """_parse_timestamp should handle Unix epoch timestamps."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        # Standard Unix timestamp (seconds)
        result = _parse_timestamp(1704067200)  # 2024-01-01 00:00:00 UTC
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_parse_timestamp_milliseconds(self):
        """_parse_timestamp should handle millisecond timestamps."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        # Millisecond timestamp
        result = _parse_timestamp(1704067200000)
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_parse_timestamp_iso_string(self):
        """_parse_timestamp should handle ISO 8601 strings."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        result = _parse_timestamp("2024-06-15T12:00:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 6

    def test_parse_timestamp_none(self):
        """_parse_timestamp should handle None."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        result = _parse_timestamp(None)
        assert isinstance(result, datetime)
        assert result.year == 1970  # epoch fallback

    def test_parse_timestamp_zero(self):
        """_parse_timestamp should handle zero."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        result = _parse_timestamp(0)
        assert isinstance(result, datetime)
        assert result.year == 1970


class TestFilenameEdgeCases:
    """Verify filename sanitization handles edge cases."""

    def test_sanitize_empty_string(self):
        """_sanitize_filename should handle empty string."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        result = _sanitize_filename("")
        assert result == "unnamed"

    def test_sanitize_special_characters(self):
        """_sanitize_filename should remove special characters."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        result = _sanitize_filename('file<>:"/\\|?*name')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "\\" not in result
        assert "/" not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    def test_sanitize_long_name(self):
        """_sanitize_filename should truncate long names."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        long_name = "a" * 100
        result = _sanitize_filename(long_name, max_length=50)
        assert len(result) <= 50

    def test_sanitize_unicode(self):
        """_sanitize_filename should handle unicode."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        result = _sanitize_filename("test_with_emoji_🎉_name")
        assert isinstance(result, str)
        assert len(result) > 0


class TestMathEdgeCases:
    """Verify math utility edge cases."""

    def test_moving_average_window_larger_than_data(self):
        """moving_average should handle window > data length."""
        from prediction_analyzer.utils.math_utils import moving_average

        result = moving_average([1.0, 2.0, 3.0], window=10)
        assert len(result) > 0

    def test_weighted_average_mismatched_lengths(self):
        """weighted_average should raise on mismatched lengths."""
        from prediction_analyzer.utils.math_utils import weighted_average

        with pytest.raises(ValueError):
            weighted_average([1.0, 2.0], [1.0])

    def test_weighted_average_empty_lists(self):
        """weighted_average should handle empty lists."""
        from prediction_analyzer.utils.math_utils import weighted_average

        # numpy raises ZeroDivisionError or similar for empty
        with pytest.raises((ValueError, ZeroDivisionError)):
            weighted_average([], [])


class TestDateParsingEdgeCases:
    """Verify date parsing handles edge cases."""

    def test_parse_date_hyphen_format(self):
        """parse_date should handle YYYY-MM-DD format."""
        from prediction_analyzer.utils.time_utils import parse_date

        result = parse_date("2024-06-15")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_parse_date_slash_format(self):
        """parse_date should handle YYYY/MM/DD format."""
        from prediction_analyzer.utils.time_utils import parse_date

        result = parse_date("2024/06/15")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_parse_date_invalid_format(self):
        """parse_date should raise on invalid format."""
        from prediction_analyzer.utils.time_utils import parse_date

        with pytest.raises(ValueError):
            parse_date("not-a-date")


class TestExtremeValueHandling:
    """Verify extreme values are handled."""

    def test_very_large_pnl_values(self, sample_trade_factory):
        """Should handle very large PnL values."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        trades = [
            sample_trade_factory(pnl=1e15),
            sample_trade_factory(pnl=-1e15),
        ]

        result = calculate_global_pnl_summary(trades)
        assert "total_pnl" in result
        # Should be close to 0 due to cancellation
        assert abs(result["total_pnl"]) < 1e10

    def test_very_small_pnl_values(self, sample_trade_factory):
        """Should handle very small PnL values."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        trades = [
            sample_trade_factory(pnl=1e-15),
            sample_trade_factory(pnl=2e-15),
        ]

        result = calculate_global_pnl_summary(trades)
        assert result["total_pnl"] >= 0  # Should be positive, even if tiny


class TestNoneValueHandling:
    """Verify None values don't cause crashes."""

    def test_filter_by_date_none_start(self, sample_trades_list):
        """filter_by_date should handle None start."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(sample_trades_list, start=None, end="2024-12-31")
        assert isinstance(result, list)

    def test_filter_by_date_none_end(self, sample_trades_list):
        """filter_by_date should handle None end."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(sample_trades_list, start="2024-01-01", end=None)
        assert isinstance(result, list)

    def test_filter_by_trade_type_none_types(self, sample_trades_list):
        """filter_by_trade_type should handle None types."""
        from prediction_analyzer.filters import filter_by_trade_type

        result = filter_by_trade_type(sample_trades_list, types=None)
        assert len(result) == len(sample_trades_list)

    def test_filter_by_pnl_none_thresholds(self, sample_trades_list):
        """filter_by_pnl should handle None thresholds."""
        from prediction_analyzer.filters import filter_by_pnl

        result = filter_by_pnl(sample_trades_list, min_pnl=None, max_pnl=None)
        assert len(result) == len(sample_trades_list)
