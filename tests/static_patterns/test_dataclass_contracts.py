# tests/static_patterns/test_dataclass_contracts.py
"""
Dataclass Contract Tests

These tests verify that the Trade dataclass maintains its structure
and behavior. Changes to the dataclass can break serialization,
PnL calculations, and other dependent code.
"""
import pytest
from dataclasses import fields, is_dataclass
from datetime import datetime
from typing import Optional


class TestTradeDataclassStructure:
    """Verify Trade dataclass structure is maintained."""

    def test_trade_is_dataclass(self):
        """Trade should be a dataclass."""
        from prediction_analyzer.trade_loader import Trade
        assert is_dataclass(Trade)

    def test_trade_required_fields(self):
        """Trade should have all required fields."""
        from prediction_analyzer.trade_loader import Trade

        field_names = {f.name for f in fields(Trade)}
        required_fields = {
            "market",
            "market_slug",
            "timestamp",
            "price",
            "shares",
            "cost",
            "type",
            "side",
        }
        assert required_fields.issubset(field_names), \
            f"Missing fields: {required_fields - field_names}"

    def test_trade_optional_fields(self):
        """Trade should have expected optional fields."""
        from prediction_analyzer.trade_loader import Trade

        field_names = {f.name for f in fields(Trade)}
        optional_fields = {"pnl", "tx_hash"}
        assert optional_fields.issubset(field_names), \
            f"Missing optional fields: {optional_fields - field_names}"

    def test_trade_field_count(self):
        """Trade should have exactly 10 fields."""
        from prediction_analyzer.trade_loader import Trade

        field_count = len(fields(Trade))
        assert field_count == 10, \
            f"Expected 10 fields, got {field_count}. Fields were added or removed."


class TestTradeFieldTypes:
    """Verify Trade field types are correct."""

    def test_market_is_string(self, sample_trade):
        """market field should be a string."""
        assert isinstance(sample_trade.market, str)

    def test_market_slug_is_string(self, sample_trade):
        """market_slug field should be a string."""
        assert isinstance(sample_trade.market_slug, str)

    def test_timestamp_is_datetime(self, sample_trade):
        """timestamp field should be a datetime."""
        assert isinstance(sample_trade.timestamp, datetime)

    def test_price_is_numeric(self, sample_trade):
        """price field should be numeric (float or int)."""
        assert isinstance(sample_trade.price, (int, float))

    def test_shares_is_numeric(self, sample_trade):
        """shares field should be numeric."""
        assert isinstance(sample_trade.shares, (int, float))

    def test_cost_is_numeric(self, sample_trade):
        """cost field should be numeric."""
        assert isinstance(sample_trade.cost, (int, float))

    def test_type_is_string(self, sample_trade):
        """type field should be a string."""
        assert isinstance(sample_trade.type, str)

    def test_side_is_string(self, sample_trade):
        """side field should be a string."""
        assert isinstance(sample_trade.side, str)

    def test_pnl_is_numeric(self, sample_trade):
        """pnl field should be numeric."""
        assert isinstance(sample_trade.pnl, (int, float))

    def test_tx_hash_is_string_or_none(self, sample_trade_factory):
        """tx_hash field should be string or None."""
        trade_with_hash = sample_trade_factory(tx_hash="0xabc123")
        trade_without_hash = sample_trade_factory(tx_hash=None)

        assert isinstance(trade_with_hash.tx_hash, str)
        assert trade_without_hash.tx_hash is None


class TestTradeDefaultValues:
    """Verify Trade default values are correct."""

    def test_pnl_default_is_zero(self):
        """pnl should default to 0.0."""
        from prediction_analyzer.trade_loader import Trade

        trade = Trade(
            market="Test",
            market_slug="test",
            timestamp=datetime.now(),
            price=50.0,
            shares=10.0,
            cost=5.0,
            type="Buy",
            side="YES"
        )
        assert trade.pnl == 0.0

    def test_tx_hash_default_is_none(self):
        """tx_hash should default to None."""
        from prediction_analyzer.trade_loader import Trade

        trade = Trade(
            market="Test",
            market_slug="test",
            timestamp=datetime.now(),
            price=50.0,
            shares=10.0,
            cost=5.0,
            type="Buy",
            side="YES"
        )
        assert trade.tx_hash is None


class TestTradeInstantiation:
    """Verify Trade can be instantiated correctly."""

    def test_trade_with_all_fields(self):
        """Trade should accept all fields."""
        from prediction_analyzer.trade_loader import Trade

        trade = Trade(
            market="Full Test Market",
            market_slug="full-test-market",
            timestamp=datetime(2024, 6, 15, 12, 0, 0),
            price=65.5,
            shares=100.0,
            cost=65.5,
            type="Market Buy",
            side="NO",
            pnl=10.25,
            tx_hash="0xdeadbeef"
        )

        assert trade.market == "Full Test Market"
        assert trade.market_slug == "full-test-market"
        assert trade.timestamp == datetime(2024, 6, 15, 12, 0, 0)
        assert trade.price == 65.5
        assert trade.shares == 100.0
        assert trade.cost == 65.5
        assert trade.type == "Market Buy"
        assert trade.side == "NO"
        assert trade.pnl == 10.25
        assert trade.tx_hash == "0xdeadbeef"

    def test_trade_with_minimum_fields(self):
        """Trade should work with only required fields."""
        from prediction_analyzer.trade_loader import Trade

        trade = Trade(
            market="Min Market",
            market_slug="min-market",
            timestamp=datetime.now(),
            price=50.0,
            shares=10.0,
            cost=5.0,
            type="Buy",
            side="YES"
        )

        assert trade.market == "Min Market"
        assert trade.pnl == 0.0  # default
        assert trade.tx_hash is None  # default


class TestTradeConversions:
    """Verify Trade can be converted to/from dict."""

    def test_trade_to_dict_via_vars(self, sample_trade):
        """Trade should be convertible to dict via vars()."""
        trade_dict = vars(sample_trade)

        assert isinstance(trade_dict, dict)
        assert "market" in trade_dict
        assert "price" in trade_dict
        assert "pnl" in trade_dict

    def test_trade_dict_has_all_fields(self, sample_trade):
        """Trade dict should have all field values."""
        from prediction_analyzer.trade_loader import Trade
        from dataclasses import fields

        trade_dict = vars(sample_trade)
        field_names = {f.name for f in fields(Trade)}

        assert set(trade_dict.keys()) == field_names

    def test_trade_dict_roundtrip(self, sample_trade):
        """Trade should roundtrip through dict conversion."""
        from prediction_analyzer.trade_loader import Trade

        trade_dict = vars(sample_trade)
        new_trade = Trade(**trade_dict)

        assert new_trade.market == sample_trade.market
        assert new_trade.price == sample_trade.price
        assert new_trade.timestamp == sample_trade.timestamp
        assert new_trade.pnl == sample_trade.pnl


class TestTradeEquality:
    """Verify Trade equality behavior."""

    def test_identical_trades_are_equal(self, sample_trade_factory):
        """Two trades with same values should be equal."""
        trade1 = sample_trade_factory(
            timestamp=datetime(2024, 1, 1),
            price=50.0,
            pnl=10.0
        )
        trade2 = sample_trade_factory(
            timestamp=datetime(2024, 1, 1),
            price=50.0,
            pnl=10.0
        )

        assert trade1 == trade2

    def test_different_trades_are_not_equal(self, sample_trade_factory):
        """Two trades with different values should not be equal."""
        trade1 = sample_trade_factory(price=50.0)
        trade2 = sample_trade_factory(price=60.0)

        assert trade1 != trade2


class TestTradeTypeValues:
    """Verify expected Trade type and side values."""

    def test_valid_trade_types(self, sample_trade_factory):
        """All valid trade types should be instantiable."""
        valid_types = [
            "Buy", "Sell",
            "Market Buy", "Market Sell",
            "Limit Buy", "Limit Sell"
        ]

        for trade_type in valid_types:
            trade = sample_trade_factory(type=trade_type)
            assert trade.type == trade_type

    def test_valid_sides(self, sample_trade_factory):
        """YES and NO sides should be instantiable."""
        for side in ["YES", "NO"]:
            trade = sample_trade_factory(side=side)
            assert trade.side == side
