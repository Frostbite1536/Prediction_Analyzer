# tests/mcp/test_validators.py
"""Tests for MCP input validators."""
import pytest

from prediction_analyzer.exceptions import InvalidFilterError, MarketNotFoundError
from prediction_mcp.validators import (
    validate_date,
    validate_trade_types,
    validate_sides,
    validate_chart_type,
    validate_export_format,
    validate_positive_int,
    validate_cost_basis_method,
    validate_sort_field,
    validate_market_slug,
)


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("2024-01-15", "test") == "2024-01-15"

    def test_none_returns_none(self):
        assert validate_date(None, "test") is None

    def test_invalid_format_raises(self):
        with pytest.raises(InvalidFilterError, match="YYYY-MM-DD"):
            validate_date("01-15-2024", "test")

    def test_invalid_date_raises(self):
        with pytest.raises(InvalidFilterError):
            validate_date("not-a-date", "test")

    def test_empty_string_raises(self):
        with pytest.raises(InvalidFilterError):
            validate_date("", "test")


class TestValidateTradeTypes:
    def test_valid_types(self):
        assert validate_trade_types(["Buy", "Sell"]) == ["Buy", "Sell"]

    def test_none_returns_none(self):
        assert validate_trade_types(None) is None

    def test_invalid_type_raises(self):
        with pytest.raises(InvalidFilterError, match="Invalid trade types"):
            validate_trade_types(["Buy", "Hold"])


class TestValidateSides:
    def test_valid_sides(self):
        assert validate_sides(["YES", "NO"]) == ["YES", "NO"]

    def test_none_returns_none(self):
        assert validate_sides(None) is None

    def test_invalid_side_raises(self):
        with pytest.raises(InvalidFilterError, match="Invalid sides"):
            validate_sides(["MAYBE"])


class TestValidateChartType:
    def test_valid_types(self):
        for ct in ["simple", "pro", "enhanced"]:
            assert validate_chart_type(ct) == ct

    def test_invalid_type_raises(self):
        with pytest.raises(InvalidFilterError, match="Invalid chart type"):
            validate_chart_type("scatter")


class TestValidateExportFormat:
    def test_valid_formats(self):
        for fmt in ["csv", "xlsx", "json"]:
            assert validate_export_format(fmt) == fmt

    def test_invalid_format_raises(self):
        with pytest.raises(InvalidFilterError, match="Invalid export format"):
            validate_export_format("pdf")


class TestValidatePositiveInt:
    def test_valid_positive_int(self):
        assert validate_positive_int(10, "test") == 10

    def test_none_returns_none(self):
        assert validate_positive_int(None, "test") is None

    def test_zero_raises(self):
        with pytest.raises(InvalidFilterError):
            validate_positive_int(0, "test")

    def test_negative_raises(self):
        with pytest.raises(InvalidFilterError):
            validate_positive_int(-1, "test")


class TestValidateCostBasisMethod:
    def test_valid_methods(self):
        for m in ["fifo", "lifo", "average"]:
            assert validate_cost_basis_method(m) == m

    def test_invalid_raises(self):
        with pytest.raises(InvalidFilterError):
            validate_cost_basis_method("weighted")


class TestValidateSortField:
    def test_valid_fields(self):
        for f in ["timestamp", "pnl", "cost"]:
            assert validate_sort_field(f) == f

    def test_invalid_raises(self):
        with pytest.raises(InvalidFilterError):
            validate_sort_field("market")


class TestValidateMarketSlug:
    def test_valid_slug(self):
        markets = {"market-0": "Market 0", "market-1": "Market 1"}
        assert validate_market_slug("market-0", markets) == "market-0"

    def test_invalid_slug_raises_with_available(self):
        markets = {"market-0": "Market 0", "market-1": "Market 1"}
        with pytest.raises(MarketNotFoundError, match="not found") as exc_info:
            validate_market_slug("nonexistent", markets)
        assert "market-0" in str(exc_info.value)
        assert "market-1" in str(exc_info.value)

    def test_empty_markets(self):
        with pytest.raises(MarketNotFoundError, match="0 total"):
            validate_market_slug("anything", {})
