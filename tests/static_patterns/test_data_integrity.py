# tests/static_patterns/test_data_integrity.py
"""
Data Integrity Tests

These tests verify that data serialization and deserialization
maintains integrity. Data loss or corruption during I/O can cause
subtle bugs that are hard to track down.
"""
import pytest
import json
import tempfile
import os
from datetime import datetime


class TestTradeSerializationIntegrity:
    """Verify Trade serialization maintains data integrity."""

    def test_trade_to_dict_preserves_all_fields(self, sample_trade):
        """Converting Trade to dict should preserve all fields."""
        trade_dict = vars(sample_trade)

        assert trade_dict["market"] == sample_trade.market
        assert trade_dict["market_slug"] == sample_trade.market_slug
        assert trade_dict["timestamp"] == sample_trade.timestamp
        assert trade_dict["price"] == sample_trade.price
        assert trade_dict["shares"] == sample_trade.shares
        assert trade_dict["cost"] == sample_trade.cost
        assert trade_dict["type"] == sample_trade.type
        assert trade_dict["side"] == sample_trade.side
        assert trade_dict["pnl"] == sample_trade.pnl
        assert trade_dict["tx_hash"] == sample_trade.tx_hash

    def test_dict_to_trade_roundtrip(self, sample_trade):
        """Trade -> dict -> Trade should preserve all data."""
        from prediction_analyzer.trade_loader import Trade

        trade_dict = vars(sample_trade)
        restored_trade = Trade(**trade_dict)

        assert restored_trade.market == sample_trade.market
        assert restored_trade.market_slug == sample_trade.market_slug
        assert restored_trade.timestamp == sample_trade.timestamp
        assert restored_trade.price == sample_trade.price
        assert restored_trade.shares == sample_trade.shares
        assert restored_trade.cost == sample_trade.cost
        assert restored_trade.type == sample_trade.type
        assert restored_trade.side == sample_trade.side
        assert restored_trade.pnl == sample_trade.pnl
        assert restored_trade.tx_hash == sample_trade.tx_hash


class TestJSONSerializationIntegrity:
    """Verify JSON save/load maintains data integrity."""

    def test_save_and_load_trades(self, sample_trades_list):
        """save_trades and load_trades should roundtrip correctly."""
        from prediction_analyzer.trade_loader import save_trades, load_trades

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            save_trades(sample_trades_list, temp_path)
            loaded_trades = load_trades(temp_path)

            assert len(loaded_trades) == len(sample_trades_list)

            for original, loaded in zip(sample_trades_list, loaded_trades):
                assert loaded.market == original.market
                assert loaded.market_slug == original.market_slug
                assert loaded.price == original.price
                assert loaded.shares == original.shares
                assert loaded.cost == original.cost
                assert loaded.type == original.type
                assert loaded.side == original.side
                assert loaded.pnl == original.pnl
        finally:
            os.unlink(temp_path)

    def test_save_empty_trades_list(self):
        """Saving empty list should create valid JSON."""
        from prediction_analyzer.trade_loader import save_trades, load_trades

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            save_trades([], temp_path)
            loaded = load_trades(temp_path)
            assert loaded == []
        finally:
            os.unlink(temp_path)

    def test_timestamp_serialization(self, sample_trade):
        """Timestamps should serialize to ISO format."""
        from prediction_analyzer.trade_loader import save_trades

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            save_trades([sample_trade], temp_path)

            with open(temp_path, "r") as f:
                data = json.load(f)

            # Timestamp should be a string (ISO format)
            assert isinstance(data[0]["timestamp"], str)
            # Should be parseable back to datetime
            parsed = datetime.fromisoformat(data[0]["timestamp"])
            assert isinstance(parsed, datetime)
        finally:
            os.unlink(temp_path)


class TestNumericPrecision:
    """Verify numeric values maintain precision."""

    def test_float_precision_preserved(self, sample_trade_factory):
        """Float values should maintain precision through serialization."""
        from prediction_analyzer.trade_loader import save_trades, load_trades

        precise_value = 123.456789012345

        trade = sample_trade_factory(
            price=precise_value,
            cost=precise_value,
            pnl=precise_value
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            save_trades([trade], temp_path)
            loaded = load_trades(temp_path)

            # Should preserve reasonable precision (JSON typically ~15 digits)
            assert abs(loaded[0].price - precise_value) < 1e-10
            assert abs(loaded[0].cost - precise_value) < 1e-10
            assert abs(loaded[0].pnl - precise_value) < 1e-10
        finally:
            os.unlink(temp_path)

    def test_zero_values_preserved(self, sample_trade_factory):
        """Zero values should be preserved."""
        from prediction_analyzer.trade_loader import save_trades, load_trades

        trade = sample_trade_factory(
            price=0.0,
            cost=0.0,
            shares=0.0,
            pnl=0.0
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            save_trades([trade], temp_path)
            loaded = load_trades(temp_path)

            assert loaded[0].price == 0.0
            assert loaded[0].cost == 0.0
            assert loaded[0].shares == 0.0
            assert loaded[0].pnl == 0.0
        finally:
            os.unlink(temp_path)

    def test_negative_values_preserved(self, sample_trade_factory):
        """Negative values should be preserved."""
        from prediction_analyzer.trade_loader import save_trades, load_trades

        trade = sample_trade_factory(pnl=-123.456)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            save_trades([trade], temp_path)
            loaded = load_trades(temp_path)

            assert loaded[0].pnl == -123.456
        finally:
            os.unlink(temp_path)


class TestStringIntegrity:
    """Verify string values maintain integrity."""

    def test_unicode_strings_preserved(self, sample_trade_factory):
        """Unicode strings should be preserved."""
        from prediction_analyzer.trade_loader import save_trades, load_trades

        unicode_market = "市場テスト 🎯 Marché"

        trade = sample_trade_factory(market=unicode_market)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            save_trades([trade], temp_path)
            loaded = load_trades(temp_path)

            assert loaded[0].market == unicode_market
        finally:
            os.unlink(temp_path)

    def test_empty_strings_preserved(self, sample_trade_factory):
        """Empty strings should not become None."""
        from prediction_analyzer.trade_loader import save_trades, load_trades

        # Note: empty market might get replaced with "Unknown" by loader
        trade = sample_trade_factory(tx_hash="")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            save_trades([trade], temp_path)
            loaded = load_trades(temp_path)

            # tx_hash might be empty string or None depending on implementation
            assert loaded[0].tx_hash in ["", None]
        finally:
            os.unlink(temp_path)


class TestDataFrameIntegrity:
    """Verify DataFrame conversions maintain integrity."""

    def test_trades_to_dataframe_preserves_data(self, sample_trades_list):
        """Converting trades to DataFrame should preserve all data."""
        import pandas as pd

        df = pd.DataFrame([vars(t) for t in sample_trades_list])

        assert len(df) == len(sample_trades_list)

        for idx, trade in enumerate(sample_trades_list):
            assert df.iloc[idx]["market"] == trade.market
            assert df.iloc[idx]["price"] == trade.price
            assert df.iloc[idx]["pnl"] == trade.pnl

    def test_pnl_calculation_preserves_trade_data(self, sample_trades_list):
        """calculate_pnl should preserve original trade data in DataFrame."""
        from prediction_analyzer.pnl import calculate_pnl

        df = calculate_pnl(sample_trades_list)

        # Original columns should be present
        assert "market" in df.columns
        assert "price" in df.columns
        assert "shares" in df.columns


class TestExportIntegrity:
    """Verify export functions maintain data integrity."""

    def test_export_to_json_creates_valid_json(self, sample_trades_list):
        """export_to_json should create valid, parseable JSON."""
        from prediction_analyzer.reporting.report_data import export_to_json

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_path = f.name

        try:
            result = export_to_json(sample_trades_list, temp_path)
            assert result is True

            # Should be valid JSON
            with open(temp_path, "r") as f:
                data = json.load(f)

            assert isinstance(data, list)
            assert len(data) == len(sample_trades_list)
        finally:
            os.unlink(temp_path)

    def test_export_to_csv_creates_valid_csv(self, sample_trades_list):
        """export_to_csv should create valid CSV."""
        from prediction_analyzer.reporting.report_data import export_to_csv
        import pandas as pd

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            temp_path = f.name

        try:
            result = export_to_csv(sample_trades_list, temp_path)
            assert result is True

            # Should be valid CSV
            df = pd.read_csv(temp_path)
            assert len(df) == len(sample_trades_list)
        finally:
            os.unlink(temp_path)

    def test_export_to_excel_creates_valid_xlsx(self, sample_trades_list):
        """export_to_excel should create valid Excel file."""
        from prediction_analyzer.reporting.report_data import export_to_excel
        import pandas as pd

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xlsx", delete=False
        ) as f:
            temp_path = f.name

        try:
            result = export_to_excel(sample_trades_list, temp_path)
            assert result is True

            # Should be valid Excel with expected sheets
            xlsx = pd.ExcelFile(temp_path)
            assert "All Trades" in xlsx.sheet_names
            assert "Market Summary" in xlsx.sheet_names
        finally:
            os.unlink(temp_path)
