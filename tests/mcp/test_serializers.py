# tests/mcp/test_serializers.py
"""Tests for MCP serializers."""

import math
import json
from datetime import datetime

import pytest

from prediction_analyzer.trade_loader import Trade
from prediction_mcp.serializers import (
    serialize_trades,
    sanitize_dict,
    to_json_text,
    _sanitize_value,
)


class TestSanitizeValue:
    def test_nan_becomes_zero(self):
        assert _sanitize_value(float("nan")) == 0.0

    def test_positive_inf_capped(self):
        assert _sanitize_value(float("inf")) == 999999.99

    def test_negative_inf_capped(self):
        assert _sanitize_value(float("-inf")) == -999999.99

    def test_normal_float_unchanged(self):
        assert _sanitize_value(3.14) == 3.14

    def test_int_unchanged(self):
        assert _sanitize_value(42) == 42

    def test_string_unchanged(self):
        assert _sanitize_value("hello") == "hello"

    def test_none_unchanged(self):
        assert _sanitize_value(None) is None

    def test_datetime_to_isoformat(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert _sanitize_value(dt) == "2024-01-15T10:30:00"

    def test_list_recursion(self):
        result = _sanitize_value([1.0, float("nan"), "ok"])
        assert result == [1.0, 0.0, "ok"]

    def test_dict_recursion(self):
        result = _sanitize_value({"a": float("inf"), "b": "ok"})
        assert result == {"a": 999999.99, "b": "ok"}


class TestSanitizeDict:
    def test_basic_dict(self):
        d = {"val": 1.0, "name": "test"}
        assert sanitize_dict(d) == {"val": 1.0, "name": "test"}

    def test_nan_in_dict(self):
        d = {"val": float("nan")}
        result = sanitize_dict(d)
        assert result["val"] == 0.0

    def test_nested_dict(self):
        d = {"outer": {"inner": float("inf")}}
        result = sanitize_dict(d)
        assert result["outer"]["inner"] == 999999.99


class TestSerializeTrades:
    def test_empty_list(self):
        assert serialize_trades([]) == []

    def test_single_trade(self):
        trade = Trade(
            market="Test",
            market_slug="test",
            timestamp=datetime(2024, 1, 1),
            price=0.5,
            shares=10.0,
            cost=5.0,
            type="Buy",
            side="YES",
            pnl=1.0,
        )
        result = serialize_trades([trade])
        assert len(result) == 1
        assert result[0]["market"] == "Test"
        assert result[0]["timestamp"] == "2024-01-01T00:00:00"
        assert result[0]["pnl"] == 1.0

    def test_nan_pnl_sanitized(self):
        trade = Trade(
            market="Test",
            market_slug="test",
            timestamp=datetime(2024, 1, 1),
            price=0.5,
            shares=10.0,
            cost=5.0,
            type="Buy",
            side="YES",
            pnl=float("nan"),
        )
        result = serialize_trades([trade])
        assert result[0]["pnl"] == 0.0


class TestToJsonText:
    def test_dict_output_is_json(self):
        result = to_json_text({"a": 1, "b": 2})
        parsed = json.loads(result)
        assert parsed["a"] == 1

    def test_list_output_is_json(self):
        result = to_json_text([1, 2, 3])
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_nan_sanitized_in_json(self):
        result = to_json_text({"val": float("nan")})
        parsed = json.loads(result)
        assert parsed["val"] == 0.0
