# tests/test_trader_critical.py
"""
Regression tests for issues critical to high-value traders:
- CSV/Excel export data integrity
- Tax coverage of all trade types (Claim/Won/Loss)
- Timestamp parsing failure visibility
- Tax report diagnostics for unrecognized trade types
"""

import json
import math
import pytest
from datetime import datetime
from unittest.mock import patch

from prediction_analyzer.trade_loader import Trade, _parse_timestamp


def _make_trade(**kwargs):
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
        "source": "kalshi",
        "currency": "USD",
    }
    defaults.update(kwargs)
    return Trade(**defaults)


# ===========================================================================
# CSV/Excel exports: NaN/Inf sanitization (previously used vars(t))
# ===========================================================================


class TestCsvExportSanitization:
    """CSV export should sanitize NaN/Inf values via to_dict()."""

    def test_nan_pnl_in_csv(self, tmp_path):
        from prediction_analyzer.reporting.report_data import export_to_csv
        import pandas as pd

        trades = [_make_trade(pnl=float("nan"), pnl_is_set=True)]
        outfile = str(tmp_path / "test.csv")
        export_to_csv(trades, filename=outfile)

        df = pd.read_csv(outfile)
        # NaN should have been sanitized to 0.0 by to_dict()
        assert df["pnl"].iloc[0] == 0.0

    def test_inf_cost_in_csv(self, tmp_path):
        from prediction_analyzer.reporting.report_data import export_to_csv
        import pandas as pd

        trades = [_make_trade(cost=float("inf"))]
        outfile = str(tmp_path / "test.csv")
        export_to_csv(trades, filename=outfile)

        df = pd.read_csv(outfile)
        assert math.isfinite(df["cost"].iloc[0])


class TestExcelExportSanitization:
    """Excel export should sanitize NaN/Inf values via to_dict()."""

    def test_nan_pnl_in_excel(self, tmp_path):
        from prediction_analyzer.reporting.report_data import export_to_excel
        import pandas as pd

        trades = [_make_trade(pnl=float("nan"), pnl_is_set=True)]
        outfile = str(tmp_path / "test.xlsx")
        export_to_excel(trades, filename=outfile)

        df = pd.read_excel(outfile, sheet_name="All Trades")
        assert df["pnl"].iloc[0] == 0.0


# ===========================================================================
# Tax: Claim/Won/Loss trade types are taxable settlement events
# ===========================================================================


class TestTaxClaimWonLossCoverage:
    """Tax report must handle Claim/Won/Loss as sell-like dispositions."""

    def test_claim_type_generates_transaction(self):
        """A 'Claim' trade (market resolution payout) is a taxable event."""
        from prediction_analyzer.tax import calculate_capital_gains

        trades = [
            _make_trade(
                timestamp=datetime(2024, 1, 1), type="Buy", price=0.40, shares=100, cost=40.0
            ),
            _make_trade(
                timestamp=datetime(2024, 6, 1), type="Claim", price=1.00, shares=100, cost=100.0
            ),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")

        assert result["transaction_count"] == 1
        tx = result["transactions"][0]
        assert tx["proceeds"] == pytest.approx(100.0)
        assert tx["cost_basis"] == pytest.approx(40.0)
        assert tx["gain_loss"] == pytest.approx(60.0)

    def test_won_type_generates_transaction(self):
        """A 'Won' trade is a taxable event."""
        from prediction_analyzer.tax import calculate_capital_gains

        trades = [
            _make_trade(
                timestamp=datetime(2024, 1, 1), type="Buy", price=0.30, shares=50, cost=15.0
            ),
            _make_trade(
                timestamp=datetime(2024, 9, 1), type="Won", price=1.00, shares=50, cost=50.0
            ),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        assert result["transaction_count"] == 1
        assert result["net_gain_loss"] == pytest.approx(35.0)

    def test_loss_type_generates_transaction(self):
        """A 'Loss' trade (market resolved against position) is a taxable event."""
        from prediction_analyzer.tax import calculate_capital_gains

        trades = [
            _make_trade(
                timestamp=datetime(2024, 1, 1), type="Buy", price=0.70, shares=100, cost=70.0
            ),
            _make_trade(
                timestamp=datetime(2024, 6, 1), type="Loss", price=0.00, shares=100, cost=0.0
            ),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        assert result["transaction_count"] == 1
        tx = result["transactions"][0]
        assert tx["gain_loss"] == pytest.approx(-70.0)


# ===========================================================================
# Tax: Unrecognized trade types are reported in diagnostics
# ===========================================================================


class TestTaxDiagnostics:
    """Tax report should surface unrecognized trade types so traders notice gaps."""

    def test_skipped_types_included_in_result(self):
        from prediction_analyzer.tax import calculate_capital_gains

        trades = [
            _make_trade(
                timestamp=datetime(2024, 1, 1), type="Buy", price=0.50, shares=10, cost=5.0
            ),
            _make_trade(
                timestamp=datetime(2024, 3, 1), type="Dividend", price=0.0, shares=0, cost=1.0
            ),
            _make_trade(
                timestamp=datetime(2024, 6, 1), type="Rebate", price=0.0, shares=0, cost=0.5
            ),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")

        assert "skipped_trade_types" in result
        assert result["skipped_trade_types"]["Dividend"] == 1
        assert result["skipped_trade_types"]["Rebate"] == 1

    def test_no_skipped_types_when_all_recognized(self):
        from prediction_analyzer.tax import calculate_capital_gains

        trades = [
            _make_trade(
                timestamp=datetime(2024, 1, 1), type="Buy", price=0.50, shares=10, cost=5.0
            ),
            _make_trade(
                timestamp=datetime(2024, 6, 1), type="Sell", price=0.60, shares=10, cost=6.0
            ),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        assert "skipped_trade_types" not in result

    def test_warning_logged_for_skipped_types(self):
        from prediction_analyzer.tax import calculate_capital_gains

        trades = [
            _make_trade(
                timestamp=datetime(2024, 1, 1), type="Unknown Type", price=0.0, shares=0, cost=0.0
            ),
        ]

        with patch("prediction_analyzer.tax.logger") as mock_logger:
            calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
            mock_logger.warning.assert_called_once()
            assert "Unknown Type" in str(mock_logger.warning.call_args)


# ===========================================================================
# Timestamp parsing: failures should be visible, not silent
# ===========================================================================


class TestTimestampParsingVisibility:
    """Unparseable timestamps should log a warning, not silently return epoch."""

    def test_unparseable_value_logs_warning(self, caplog):
        """An unparseable timestamp should produce a warning."""
        import logging

        with caplog.at_level(logging.WARNING, logger="prediction_analyzer.trade_loader"):
            result = _parse_timestamp("completely-invalid-timestamp-xyz")
            # Should still return epoch fallback
            assert result.year == 1970
            # But should have logged a warning
            assert any("completely-invalid-timestamp-xyz" in msg for msg in caplog.messages)

    def test_valid_timestamps_no_warning(self, caplog):
        """Valid timestamps should NOT produce warnings."""
        import logging

        with caplog.at_level(logging.WARNING, logger="prediction_analyzer.trade_loader"):
            _parse_timestamp("2024-06-15T12:00:00Z")
            _parse_timestamp(1704067200)
            _parse_timestamp(1704067200000)
            assert len(caplog.records) == 0
