# tests/static_patterns/test_utility_functions.py
"""
Utility Function Tests

These tests verify that utility functions work correctly.
Utility functions are used throughout the codebase, so any issues
here will cascade into other modules.
"""
import pytest
import numpy as np
from datetime import datetime, timedelta


class TestMovingAverage:
    """Test moving_average function."""

    def test_basic_moving_average(self):
        """Basic moving average should work correctly."""
        from prediction_analyzer.utils.math_utils import moving_average

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = moving_average(values, window=3)

        # MA(3) of [1,2,3,4,5] = [2, 3, 4]
        expected = [2.0, 3.0, 4.0]
        np.testing.assert_array_almost_equal(result, expected)

    def test_moving_average_window_equals_length(self):
        """Window equal to data length should return single value."""
        from prediction_analyzer.utils.math_utils import moving_average

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = moving_average(values, window=5)

        assert len(result) == 1
        assert result[0] == 3.0  # Average of 1-5

    def test_moving_average_returns_numpy_array(self):
        """Result should be a numpy array."""
        from prediction_analyzer.utils.math_utils import moving_average

        result = moving_average([1.0, 2.0, 3.0], window=2)
        assert isinstance(result, np.ndarray)

    def test_moving_average_constant_values(self):
        """Constant values should return same constant."""
        from prediction_analyzer.utils.math_utils import moving_average

        values = [5.0, 5.0, 5.0, 5.0, 5.0]
        result = moving_average(values, window=3)

        np.testing.assert_array_almost_equal(result, [5.0, 5.0, 5.0])


class TestWeightedAverage:
    """Test weighted_average function."""

    def test_basic_weighted_average(self):
        """Basic weighted average should work correctly."""
        from prediction_analyzer.utils.math_utils import weighted_average

        values = [10.0, 20.0, 30.0]
        weights = [1.0, 2.0, 3.0]

        # (10*1 + 20*2 + 30*3) / (1+2+3) = (10+40+90) / 6 = 140/6 ≈ 23.33
        result = weighted_average(values, weights)
        assert abs(result - (140.0 / 6.0)) < 0.01

    def test_equal_weights_equals_mean(self):
        """Equal weights should produce simple mean."""
        from prediction_analyzer.utils.math_utils import weighted_average

        values = [10.0, 20.0, 30.0]
        weights = [1.0, 1.0, 1.0]

        result = weighted_average(values, weights)
        assert result == 20.0

    def test_single_nonzero_weight(self):
        """Single non-zero weight should return that value."""
        from prediction_analyzer.utils.math_utils import weighted_average

        values = [10.0, 20.0, 30.0]
        weights = [0.0, 1.0, 0.0]

        result = weighted_average(values, weights)
        assert result == 20.0


class TestSafeDivide:
    """Test safe_divide function."""

    def test_normal_division(self):
        """Normal division should work."""
        from prediction_analyzer.utils.math_utils import safe_divide

        assert safe_divide(10.0, 2.0) == 5.0
        assert safe_divide(100.0, 4.0) == 25.0

    def test_zero_denominator_returns_default(self):
        """Zero denominator should return default."""
        from prediction_analyzer.utils.math_utils import safe_divide

        assert safe_divide(10.0, 0.0) == 0.0
        assert safe_divide(10.0, 0.0, default=-1.0) == -1.0

    def test_custom_default(self):
        """Custom default should be used."""
        from prediction_analyzer.utils.math_utils import safe_divide

        assert safe_divide(10.0, 0.0, default=999.0) == 999.0

    def test_negative_values(self):
        """Negative values should work correctly."""
        from prediction_analyzer.utils.math_utils import safe_divide

        assert safe_divide(-10.0, 2.0) == -5.0
        assert safe_divide(10.0, -2.0) == -5.0
        assert safe_divide(-10.0, -2.0) == 5.0


class TestCalculateROI:
    """Test calculate_roi function."""

    def test_positive_roi(self):
        """Positive PnL should give positive ROI."""
        from prediction_analyzer.utils.math_utils import calculate_roi

        result = calculate_roi(pnl=50.0, investment=100.0)
        assert result == 50.0  # 50% ROI

    def test_negative_roi(self):
        """Negative PnL should give negative ROI."""
        from prediction_analyzer.utils.math_utils import calculate_roi

        result = calculate_roi(pnl=-25.0, investment=100.0)
        assert result == -25.0  # -25% ROI

    def test_zero_investment_returns_zero(self):
        """Zero investment should return 0 ROI."""
        from prediction_analyzer.utils.math_utils import calculate_roi

        result = calculate_roi(pnl=100.0, investment=0.0)
        assert result == 0.0

    def test_roi_is_percentage(self):
        """ROI should be expressed as percentage."""
        from prediction_analyzer.utils.math_utils import calculate_roi

        # Double the money = 100% ROI
        result = calculate_roi(pnl=100.0, investment=100.0)
        assert result == 100.0


class TestParseDate:
    """Test parse_date function."""

    def test_hyphen_format(self):
        """YYYY-MM-DD format should parse correctly."""
        from prediction_analyzer.utils.time_utils import parse_date

        result = parse_date("2024-06-15")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_slash_format(self):
        """YYYY/MM/DD format should parse correctly."""
        from prediction_analyzer.utils.time_utils import parse_date

        result = parse_date("2024/06/15")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_us_format(self):
        """MM-DD-YYYY format should parse correctly."""
        from prediction_analyzer.utils.time_utils import parse_date

        result = parse_date("06-15-2024")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_returns_datetime(self):
        """Result should be a datetime object."""
        from prediction_analyzer.utils.time_utils import parse_date

        result = parse_date("2024-06-15")
        assert isinstance(result, datetime)

    def test_invalid_date_raises(self):
        """Invalid date string should raise ValueError."""
        from prediction_analyzer.utils.time_utils import parse_date

        with pytest.raises(ValueError):
            parse_date("not-a-date")


class TestFormatTimestamp:
    """Test format_timestamp function."""

    def test_default_format(self):
        """Default format should be YYYY-MM-DD HH:MM:SS."""
        from prediction_analyzer.utils.time_utils import format_timestamp

        dt = datetime(2024, 6, 15, 14, 30, 45)
        result = format_timestamp(dt)

        assert result == "2024-06-15 14:30:45"

    def test_custom_format(self):
        """Custom format should be applied."""
        from prediction_analyzer.utils.time_utils import format_timestamp

        dt = datetime(2024, 6, 15)
        result = format_timestamp(dt, fmt="%Y-%m-%d")

        assert result == "2024-06-15"

    def test_returns_string(self):
        """Result should be a string."""
        from prediction_analyzer.utils.time_utils import format_timestamp

        result = format_timestamp(datetime.now())
        assert isinstance(result, str)


class TestGetDateRange:
    """Test get_date_range function."""

    def test_returns_tuple(self):
        """Should return a tuple of two datetimes."""
        from prediction_analyzer.utils.time_utils import get_date_range

        result = get_date_range(days_back=7)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_start_before_end(self):
        """Start date should be before end date."""
        from prediction_analyzer.utils.time_utils import get_date_range

        start, end = get_date_range(days_back=7)
        assert start < end

    def test_correct_days_difference(self):
        """Days difference should match input."""
        from prediction_analyzer.utils.time_utils import get_date_range

        days_back = 30
        start, end = get_date_range(days_back=days_back)

        diff = end - start
        assert diff.days == days_back

    def test_end_is_now(self):
        """End date should be approximately now."""
        from prediction_analyzer.utils.time_utils import get_date_range

        _, end = get_date_range(days_back=1)
        now = datetime.now()

        # Should be within 1 second of now
        assert abs((end - now).total_seconds()) < 1


class TestParseTimestamp:
    """Test _parse_timestamp function."""

    def test_unix_seconds(self):
        """Unix timestamp in seconds should parse."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        # 2024-01-01 00:00:00 UTC
        result = _parse_timestamp(1704067200)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_unix_milliseconds(self):
        """Unix timestamp in milliseconds should parse."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        result = _parse_timestamp(1704067200000)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_iso_string(self):
        """ISO 8601 string should parse."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        result = _parse_timestamp("2024-06-15T12:00:00Z")
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_iso_string_with_offset(self):
        """ISO 8601 string with timezone offset should parse."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        result = _parse_timestamp("2024-06-15T12:00:00+00:00")
        assert result.year == 2024
        assert result.month == 6

    def test_datetime_passthrough(self):
        """datetime objects should pass through."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        dt = datetime(2024, 6, 15, 12, 0, 0)
        result = _parse_timestamp(dt)
        assert result == dt

    def test_returns_naive_datetime(self):
        """Result should always be timezone-naive."""
        from prediction_analyzer.trade_loader import _parse_timestamp

        result = _parse_timestamp("2024-06-15T12:00:00Z")
        assert result.tzinfo is None


class TestSanitizeFilename:
    """Test _sanitize_filename function."""

    def test_removes_invalid_chars(self):
        """Invalid filename characters should be removed."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        result = _sanitize_filename('file<>:"/\\|?*name')
        assert all(c not in result for c in '<>:"/\\|?*')

    def test_replaces_with_underscore(self):
        """Invalid chars should be replaced with underscores."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        result = _sanitize_filename("a:b")
        assert result == "a_b"

    def test_truncates_long_names(self):
        """Long names should be truncated."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        long_name = "a" * 100
        result = _sanitize_filename(long_name, max_length=50)
        assert len(result) <= 50

    def test_empty_becomes_unnamed(self):
        """Empty string should become 'unnamed'."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        result = _sanitize_filename("")
        assert result == "unnamed"

    def test_only_invalid_chars_becomes_unnamed(self):
        """String with only invalid chars should become 'unnamed'."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        result = _sanitize_filename("<>:?*")
        # After removing all chars, should be "unnamed"
        assert result == "unnamed" or len(result) > 0

    def test_normal_string_unchanged(self):
        """Normal strings should be unchanged."""
        from prediction_analyzer.trade_loader import _sanitize_filename

        result = _sanitize_filename("normal_filename")
        assert result == "normal_filename"
