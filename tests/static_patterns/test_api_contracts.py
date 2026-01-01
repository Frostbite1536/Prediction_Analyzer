# tests/static_patterns/test_api_contracts.py
"""
API Contract Tests

These tests verify that public function signatures and return types
remain stable. This helps catch breaking changes to the API.
"""
import pytest
import inspect
from typing import get_type_hints, List, Dict, Optional
from datetime import datetime


class TestTradeLoaderAPIContracts:
    """Verify trade_loader module API contracts."""

    def test_load_trades_signature(self):
        """load_trades should accept file_path and return List[Trade]."""
        from prediction_analyzer.trade_loader import load_trades
        sig = inspect.signature(load_trades)
        params = list(sig.parameters.keys())

        assert "file_path" in params
        assert len(params) == 1  # Only file_path parameter

    def test_save_trades_signature(self):
        """save_trades should accept trades and file_path."""
        from prediction_analyzer.trade_loader import save_trades
        sig = inspect.signature(save_trades)
        params = list(sig.parameters.keys())

        assert "trades" in params
        assert "file_path" in params

    def test_parse_timestamp_exists(self):
        """_parse_timestamp helper should exist."""
        from prediction_analyzer.trade_loader import _parse_timestamp
        assert callable(_parse_timestamp)

    def test_sanitize_filename_exists(self):
        """_sanitize_filename helper should exist."""
        from prediction_analyzer.trade_loader import _sanitize_filename
        assert callable(_sanitize_filename)


class TestPnLAPIContracts:
    """Verify pnl module API contracts."""

    def test_calculate_pnl_signature(self):
        """calculate_pnl should accept trades and return DataFrame."""
        from prediction_analyzer.pnl import calculate_pnl
        import pandas as pd

        sig = inspect.signature(calculate_pnl)
        params = list(sig.parameters.keys())

        assert "trades" in params

    def test_calculate_pnl_returns_dataframe(self, sample_trades_list):
        """calculate_pnl should return a pandas DataFrame."""
        from prediction_analyzer.pnl import calculate_pnl
        import pandas as pd

        result = calculate_pnl(sample_trades_list)
        assert isinstance(result, pd.DataFrame)

    def test_calculate_pnl_dataframe_columns(self, sample_trades_list):
        """calculate_pnl DataFrame should have expected columns."""
        from prediction_analyzer.pnl import calculate_pnl

        result = calculate_pnl(sample_trades_list)
        expected_columns = {"trade_pnl", "cumulative_pnl", "exposure"}
        assert expected_columns.issubset(set(result.columns))

    def test_calculate_global_pnl_summary_signature(self):
        """calculate_global_pnl_summary should accept trades."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        sig = inspect.signature(calculate_global_pnl_summary)
        params = list(sig.parameters.keys())

        assert "trades" in params

    def test_calculate_global_pnl_summary_returns_dict(self, sample_trades_list):
        """calculate_global_pnl_summary should return a dict."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        assert isinstance(result, dict)

    def test_calculate_global_pnl_summary_keys(self, sample_trades_list):
        """calculate_global_pnl_summary should have expected keys."""
        from prediction_analyzer.pnl import calculate_global_pnl_summary

        result = calculate_global_pnl_summary(sample_trades_list)
        expected_keys = {
            "total_trades", "total_pnl", "win_rate",
            "winning_trades", "losing_trades"
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_calculate_market_pnl_signature(self):
        """calculate_market_pnl should accept trades."""
        from prediction_analyzer.pnl import calculate_market_pnl

        sig = inspect.signature(calculate_market_pnl)
        params = list(sig.parameters.keys())

        assert "trades" in params

    def test_calculate_market_pnl_returns_dict(self, multi_market_trades):
        """calculate_market_pnl should return a dict."""
        from prediction_analyzer.pnl import calculate_market_pnl

        result = calculate_market_pnl(multi_market_trades)
        assert isinstance(result, dict)

    def test_calculate_market_pnl_summary_signature(self):
        """calculate_market_pnl_summary should accept trades."""
        from prediction_analyzer.pnl import calculate_market_pnl_summary

        sig = inspect.signature(calculate_market_pnl_summary)
        params = list(sig.parameters.keys())

        assert "trades" in params


class TestFiltersAPIContracts:
    """Verify filters module API contracts."""

    def test_filter_by_date_signature(self):
        """filter_by_date should accept trades, start, end."""
        from prediction_analyzer.filters import filter_by_date

        sig = inspect.signature(filter_by_date)
        params = list(sig.parameters.keys())

        assert "trades" in params
        assert "start" in params
        assert "end" in params

    def test_filter_by_date_returns_list(self, sample_trades_list):
        """filter_by_date should return a list."""
        from prediction_analyzer.filters import filter_by_date

        result = filter_by_date(sample_trades_list, start="2024-01-01")
        assert isinstance(result, list)

    def test_filter_by_trade_type_signature(self):
        """filter_by_trade_type should accept trades and types."""
        from prediction_analyzer.filters import filter_by_trade_type

        sig = inspect.signature(filter_by_trade_type)
        params = list(sig.parameters.keys())

        assert "trades" in params
        assert "types" in params

    def test_filter_by_trade_type_returns_list(self, sample_trades_list):
        """filter_by_trade_type should return a list."""
        from prediction_analyzer.filters import filter_by_trade_type

        result = filter_by_trade_type(sample_trades_list, types=["Buy"])
        assert isinstance(result, list)

    def test_filter_by_side_signature(self):
        """filter_by_side should accept trades and sides."""
        from prediction_analyzer.filters import filter_by_side

        sig = inspect.signature(filter_by_side)
        params = list(sig.parameters.keys())

        assert "trades" in params
        assert "sides" in params

    def test_filter_by_side_returns_list(self, sample_trades_list):
        """filter_by_side should return a list."""
        from prediction_analyzer.filters import filter_by_side

        result = filter_by_side(sample_trades_list, sides=["YES"])
        assert isinstance(result, list)

    def test_filter_by_pnl_signature(self):
        """filter_by_pnl should accept trades, min_pnl, max_pnl."""
        from prediction_analyzer.filters import filter_by_pnl

        sig = inspect.signature(filter_by_pnl)
        params = list(sig.parameters.keys())

        assert "trades" in params
        assert "min_pnl" in params
        assert "max_pnl" in params

    def test_filter_by_pnl_returns_list(self, sample_trades_list):
        """filter_by_pnl should return a list."""
        from prediction_analyzer.filters import filter_by_pnl

        result = filter_by_pnl(sample_trades_list, min_pnl=-10.0)
        assert isinstance(result, list)


class TestConfigAPIContracts:
    """Verify config module API contracts."""

    def test_get_trade_style_signature(self):
        """get_trade_style should accept trade_type and side."""
        from prediction_analyzer.config import get_trade_style

        sig = inspect.signature(get_trade_style)
        params = list(sig.parameters.keys())

        assert "trade_type" in params
        assert "side" in params

    def test_get_trade_style_returns_tuple(self):
        """get_trade_style should return a tuple of (color, marker, label)."""
        from prediction_analyzer.config import get_trade_style

        result = get_trade_style("Buy", "YES")
        assert isinstance(result, tuple)
        assert len(result) == 3


class TestReportingAPIContracts:
    """Verify reporting module API contracts."""

    def test_export_to_csv_signature(self):
        """export_to_csv should accept trades and filename."""
        from prediction_analyzer.reporting.report_data import export_to_csv

        sig = inspect.signature(export_to_csv)
        params = list(sig.parameters.keys())

        assert "trades" in params
        assert "filename" in params

    def test_export_to_excel_signature(self):
        """export_to_excel should accept trades and filename."""
        from prediction_analyzer.reporting.report_data import export_to_excel

        sig = inspect.signature(export_to_excel)
        params = list(sig.parameters.keys())

        assert "trades" in params
        assert "filename" in params

    def test_export_to_json_signature(self):
        """export_to_json should accept trades and filename."""
        from prediction_analyzer.reporting.report_data import export_to_json

        sig = inspect.signature(export_to_json)
        params = list(sig.parameters.keys())

        assert "trades" in params
        assert "filename" in params


class TestMathUtilsAPIContracts:
    """Verify math_utils module API contracts."""

    def test_moving_average_signature(self):
        """moving_average should accept values and window."""
        from prediction_analyzer.utils.math_utils import moving_average

        sig = inspect.signature(moving_average)
        params = list(sig.parameters.keys())

        assert "values" in params
        assert "window" in params

    def test_weighted_average_signature(self):
        """weighted_average should accept values and weights."""
        from prediction_analyzer.utils.math_utils import weighted_average

        sig = inspect.signature(weighted_average)
        params = list(sig.parameters.keys())

        assert "values" in params
        assert "weights" in params

    def test_safe_divide_signature(self):
        """safe_divide should accept numerator, denominator, default."""
        from prediction_analyzer.utils.math_utils import safe_divide

        sig = inspect.signature(safe_divide)
        params = list(sig.parameters.keys())

        assert "numerator" in params
        assert "denominator" in params
        assert "default" in params

    def test_calculate_roi_signature(self):
        """calculate_roi should accept pnl and investment."""
        from prediction_analyzer.utils.math_utils import calculate_roi

        sig = inspect.signature(calculate_roi)
        params = list(sig.parameters.keys())

        assert "pnl" in params
        assert "investment" in params


class TestTimeUtilsAPIContracts:
    """Verify time_utils module API contracts."""

    def test_parse_date_signature(self):
        """parse_date should accept date_str."""
        from prediction_analyzer.utils.time_utils import parse_date

        sig = inspect.signature(parse_date)
        params = list(sig.parameters.keys())

        assert "date_str" in params

    def test_format_timestamp_signature(self):
        """format_timestamp should accept timestamp and fmt."""
        from prediction_analyzer.utils.time_utils import format_timestamp

        sig = inspect.signature(format_timestamp)
        params = list(sig.parameters.keys())

        assert "timestamp" in params
        assert "fmt" in params

    def test_get_date_range_signature(self):
        """get_date_range should accept days_back."""
        from prediction_analyzer.utils.time_utils import get_date_range

        sig = inspect.signature(get_date_range)
        params = list(sig.parameters.keys())

        assert "days_back" in params


class TestChartsAPIContracts:
    """Verify chart module API contracts."""

    def test_generate_simple_chart_signature(self):
        """generate_simple_chart should accept trades, market_name, resolved_outcome."""
        from prediction_analyzer.charts.simple import generate_simple_chart

        sig = inspect.signature(generate_simple_chart)
        params = list(sig.parameters.keys())

        assert "trades" in params
        assert "market_name" in params
        assert "resolved_outcome" in params
