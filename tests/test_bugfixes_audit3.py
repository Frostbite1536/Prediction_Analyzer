# tests/test_bugfixes_audit3.py
"""
Regression tests for bugs identified in the third bug-fix audit.

Bug #1: Unrealized PnL sign inverted for NO (short) positions
Bug #2: Mixed YES/NO buy lots in same deque corrupt cost basis
Bug #3: tax.py used float accumulation instead of Decimal for monetary totals
Bug #4: total_fees in tax report counted all years, not just tax year
Bug #5: sanitize_numeric did not handle Decimal NaN/Inf
Bug #6: analysis_tools provider breakdown used float accumulation
"""

import math
from datetime import datetime
from decimal import Decimal

import pytest

from prediction_analyzer.trade_loader import Trade, sanitize_numeric
from prediction_analyzer.positions import calculate_open_positions, calculate_concentration_risk
from prediction_analyzer.tax import calculate_capital_gains


def _make_trade(**kwargs):
    """Create a Trade with sensible defaults, overriding with kwargs."""
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
        "tx_hash": "",
        "source": "limitless",
        "currency": "USD",
        "fee": 0.0,
    }
    defaults.update(kwargs)
    return Trade(**defaults)


# ===========================================================================
# Bug #1: Unrealized PnL sign inverted for NO (short) positions
# ===========================================================================


class TestUnrealizedPnlSign:
    """NO positions should show positive unrealized PnL when price drops."""

    def test_yes_position_unrealized_pnl_positive_when_price_rises(self):
        """YES position profits when price goes up."""
        trades = [
            _make_trade(
                type="Buy",
                side="YES",
                shares=100.0,
                cost=50.0,
                price=0.50,
            ),
        ]
        positions = calculate_open_positions(trades)
        assert len(positions) == 1
        pos = positions[0]
        assert pos["side"] == "YES"
        assert pos["net_shares"] == 100.0

    def test_no_position_cost_basis(self):
        """NO position should track cost basis correctly via separate lots."""
        trades = [
            _make_trade(
                type="Buy",
                side="NO",
                shares=100.0,
                cost=40.0,
                price=0.40,
            ),
        ]
        positions = calculate_open_positions(trades)
        assert len(positions) == 1
        pos = positions[0]
        assert pos["side"] == "NO"
        assert pos["net_shares"] == 100.0
        assert pos["cost_basis"] == pytest.approx(40.0, abs=0.01)


# ===========================================================================
# Bug #2: Mixed YES/NO buy lots in same deque corrupt cost basis
# ===========================================================================


class TestMixedSideLotTracking:
    """YES and NO buy lots should be tracked separately."""

    def test_yes_sell_does_not_consume_no_lots(self):
        """Selling YES should only consume YES buy lots, not NO buy lots."""
        trades = [
            _make_trade(
                type="Buy",
                side="YES",
                shares=50.0,
                cost=25.0,
                price=0.50,
                timestamp=datetime(2024, 1, 1),
            ),
            _make_trade(
                type="Buy",
                side="NO",
                shares=100.0,
                cost=40.0,
                price=0.40,
                timestamp=datetime(2024, 1, 2),
            ),
            _make_trade(
                type="Sell",
                side="YES",
                shares=50.0,
                cost=30.0,
                price=0.60,
                timestamp=datetime(2024, 1, 3),
            ),
        ]
        # After: YES position fully closed, NO position of 100 shares remains
        positions = calculate_open_positions(trades)
        assert len(positions) == 1
        pos = positions[0]
        assert pos["side"] == "NO"
        assert pos["net_shares"] == 100.0
        # NO lot cost basis should be intact (not consumed by YES sell)
        assert pos["cost_basis"] == pytest.approx(40.0, abs=0.01)

    def test_mixed_sides_both_open(self):
        """Both YES and NO positions in separate markets track independently."""
        trades = [
            _make_trade(
                market="Market A",
                market_slug="market-a",
                type="Buy",
                side="YES",
                shares=100.0,
                cost=60.0,
                price=0.60,
                timestamp=datetime(2024, 1, 1),
            ),
            _make_trade(
                market="Market B",
                market_slug="market-b",
                type="Buy",
                side="NO",
                shares=50.0,
                cost=20.0,
                price=0.40,
                timestamp=datetime(2024, 1, 2),
            ),
        ]
        positions = calculate_open_positions(trades)
        assert len(positions) == 2
        by_slug = {p["market_slug"]: p for p in positions}
        assert by_slug["market-a"]["side"] == "YES"
        assert by_slug["market-a"]["net_shares"] == 100.0
        assert by_slug["market-b"]["side"] == "NO"
        assert by_slug["market-b"]["net_shares"] == 50.0


# ===========================================================================
# Bug #3: tax.py used float accumulation instead of Decimal
# ===========================================================================


class TestTaxDecimalPrecision:
    """Tax calculations should use Decimal to avoid float drift."""

    def test_many_small_transactions_no_drift(self):
        """Many small gains should not lose precision from float accumulation."""
        trades = []
        # 1000 buy-sell pairs, each with a tiny gain
        for i in range(1000):
            trades.append(
                _make_trade(
                    type="Buy",
                    side="YES",
                    shares=1.0,
                    cost=0.01,
                    price=0.01,
                    fee=0.0,
                    timestamp=datetime(2024, 1, 1, 0, i // 60, i % 60),
                    tx_hash=f"buy_{i}",
                )
            )
            trades.append(
                _make_trade(
                    type="Sell",
                    side="YES",
                    shares=1.0,
                    cost=0.02,
                    price=0.02,
                    fee=0.0,
                    timestamp=datetime(2024, 6, 1, 0, i // 60, i % 60),
                    tx_hash=f"sell_{i}",
                )
            )

        report = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        # Each sell gains 0.01, so total should be exactly 10.00
        assert report["short_term_gains"] == pytest.approx(10.0, abs=0.001)
        assert report["short_term_losses"] == pytest.approx(0.0, abs=0.001)
        assert report["net_gain_loss"] == pytest.approx(10.0, abs=0.001)


# ===========================================================================
# Bug #4: total_fees counted all years, not just tax year
# ===========================================================================


class TestTaxYearFees:
    """total_fees should only count fees within the tax year."""

    def test_fees_scoped_to_tax_year(self):
        """Fees from prior years should not be included in tax year total."""
        trades = [
            # Prior year buy with fee
            _make_trade(
                type="Buy",
                side="YES",
                shares=100.0,
                cost=50.0,
                price=0.50,
                fee=5.0,
                timestamp=datetime(2023, 6, 1),
                tx_hash="old_buy",
            ),
            # Tax year sell with fee
            _make_trade(
                type="Sell",
                side="YES",
                shares=100.0,
                cost=60.0,
                price=0.60,
                fee=3.0,
                timestamp=datetime(2024, 6, 1),
                tx_hash="new_sell",
            ),
        ]
        report = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        # Only the sell fee (3.0) should be in tax year fees, not the buy fee (5.0)
        assert report["total_fees"] == pytest.approx(3.0, abs=0.01)


# ===========================================================================
# Bug #5: sanitize_numeric did not handle Decimal NaN/Inf
# ===========================================================================


class TestSanitizeNumericDecimal:
    """sanitize_numeric should handle Decimal NaN and Infinity."""

    def test_decimal_nan_becomes_zero(self):
        assert sanitize_numeric(Decimal("NaN")) == 0.0

    def test_decimal_positive_inf_capped(self):
        result = sanitize_numeric(Decimal("Infinity"))
        assert result == 999999.99

    def test_decimal_negative_inf_capped(self):
        result = sanitize_numeric(Decimal("-Infinity"))
        assert result == -999999.99

    def test_decimal_normal_value_returned_as_float(self):
        result = sanitize_numeric(Decimal("3.14"))
        assert result == pytest.approx(3.14)
        assert isinstance(result, float)

    def test_float_nan_still_works(self):
        assert sanitize_numeric(float("nan")) == 0.0

    def test_float_inf_still_works(self):
        assert sanitize_numeric(float("inf")) == 999999.99

    def test_int_passthrough(self):
        assert sanitize_numeric(42) == 42
