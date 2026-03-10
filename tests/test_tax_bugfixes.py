# tests/test_tax_bugfixes.py
"""
Regression tests for tax-critical bugs.

These tests verify that capital gains calculations are correct for
real-world scenarios that million-dollar traders would encounter.
"""
import pytest
from datetime import datetime

from prediction_analyzer.trade_loader import Trade
from prediction_analyzer.tax import calculate_capital_gains


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
# CRITICAL BUG: Sells outside the tax year were not consuming buy lots,
# causing double-counted cost basis in subsequent years.
#
# Example: Buy 10 @ $0.30, Buy 10 @ $0.70, Sell 10 in 2023, Sell 10 in 2024
# Old bug: 2024 sell matched the $0.30 lot (already sold in 2023!)
# Fix: All sells consume lots; only tax-year sells generate transactions.
# ===========================================================================

class TestPriorYearSellsConsumeLots:
    """Sells in prior years MUST consume buy lots so later years are correct."""

    def test_fifo_prior_year_sell_consumes_earliest_lot(self):
        """FIFO: a 2023 sell should consume the $0.30 lot, leaving only $0.70 for 2024."""
        trades = [
            _make_trade(timestamp=datetime(2023, 1, 15), type="Buy",
                        price=0.30, shares=10, cost=3.0),
            _make_trade(timestamp=datetime(2023, 6, 15), type="Buy",
                        price=0.70, shares=10, cost=7.0),
            _make_trade(timestamp=datetime(2023, 12, 1), type="Sell",
                        price=0.90, shares=10, cost=9.0),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")

        assert result["transaction_count"] == 1
        tx = result["transactions"][0]

        # 2024 sell should match the $0.70 lot (the $0.30 lot was consumed in 2023)
        assert tx["cost_basis"] == pytest.approx(7.0)  # 10 * $0.70
        assert tx["proceeds"] == pytest.approx(5.0)    # 10 * $0.50
        assert tx["gain_loss"] == pytest.approx(-2.0)   # loss, NOT a gain

    def test_lifo_prior_year_sell_consumes_latest_lot(self):
        """LIFO: a 2023 sell should consume the $0.70 lot, leaving $0.30 for 2024."""
        trades = [
            _make_trade(timestamp=datetime(2023, 1, 15), type="Buy",
                        price=0.30, shares=10, cost=3.0),
            _make_trade(timestamp=datetime(2023, 6, 15), type="Buy",
                        price=0.70, shares=10, cost=7.0),
            _make_trade(timestamp=datetime(2023, 12, 1), type="Sell",
                        price=0.90, shares=10, cost=9.0),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="lifo")

        assert result["transaction_count"] == 1
        tx = result["transactions"][0]

        # 2024 sell should match the $0.30 lot (LIFO consumed $0.70 in 2023)
        assert tx["cost_basis"] == pytest.approx(3.0)
        assert tx["proceeds"] == pytest.approx(5.0)
        assert tx["gain_loss"] == pytest.approx(2.0)

    def test_average_prior_year_sell_reduces_pool(self):
        """Average: a 2023 sell should reduce the share pool for 2024."""
        trades = [
            _make_trade(timestamp=datetime(2023, 1, 15), type="Buy",
                        price=0.40, shares=10, cost=4.0),
            _make_trade(timestamp=datetime(2023, 6, 15), type="Buy",
                        price=0.60, shares=10, cost=6.0),
            _make_trade(timestamp=datetime(2023, 12, 1), type="Sell",
                        price=0.80, shares=10, cost=8.0),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.70, shares=10, cost=7.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="average")

        assert result["transaction_count"] == 1
        tx = result["transactions"][0]

        # Average cost = (4.0 + 6.0) / 20 = 0.50 per share
        # After 2023 sell of 10 shares, 10 shares remain at avg $0.50
        assert tx["cost_basis"] == pytest.approx(5.0)  # 10 * $0.50
        assert tx["proceeds"] == pytest.approx(7.0)
        assert tx["gain_loss"] == pytest.approx(2.0)

    def test_no_transactions_outside_tax_year(self):
        """Sells outside the tax year should NOT appear in transactions."""
        trades = [
            _make_trade(timestamp=datetime(2023, 1, 15), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2023, 12, 1), type="Sell",
                        price=0.80, shares=10, cost=8.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")

        assert result["transaction_count"] == 0
        assert result["net_gain_loss"] == 0.0

    def test_prior_year_sell_prevents_double_counting(self):
        """Cannot sell more shares than bought — prior sells must deplete the pool."""
        trades = [
            _make_trade(timestamp=datetime(2023, 1, 15), type="Buy",
                        price=0.50, shares=100, cost=50.0),
            # Sell ALL 100 shares in 2023
            _make_trade(timestamp=datetime(2023, 6, 1), type="Sell",
                        price=0.80, shares=100, cost=80.0),
            # Try to sell 50 more in 2024 — no lots should remain
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.60, shares=50, cost=30.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")

        # No lots available — transaction should have zero cost basis
        # (the shares were already sold in 2023)
        assert result["transaction_count"] == 0

    def test_partial_prior_year_sell(self):
        """A partial sell in 2023 should only consume that many shares."""
        trades = [
            _make_trade(timestamp=datetime(2023, 1, 15), type="Buy",
                        price=0.40, shares=100, cost=40.0),
            # Sell 30 of 100 in 2023
            _make_trade(timestamp=datetime(2023, 6, 1), type="Sell",
                        price=0.70, shares=30, cost=21.0),
            # Sell 70 in 2024
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.60, shares=70, cost=42.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")

        assert result["transaction_count"] == 1
        tx = result["transactions"][0]

        # 70 remaining shares at $0.40 cost
        assert tx["shares"] == pytest.approx(70.0)
        assert tx["cost_basis"] == pytest.approx(28.0)  # 70 * $0.40
        assert tx["proceeds"] == pytest.approx(42.0)     # 70 * $0.60
        assert tx["gain_loss"] == pytest.approx(14.0)

    def test_multi_market_isolation(self):
        """Prior-year sells in market A should not affect market B's lots."""
        trades = [
            # Market A: buy and sell in 2023
            _make_trade(timestamp=datetime(2023, 1, 1), type="Buy",
                        market_slug="market-a", price=0.30, shares=10, cost=3.0),
            _make_trade(timestamp=datetime(2023, 6, 1), type="Sell",
                        market_slug="market-a", price=0.80, shares=10, cost=8.0),
            # Market B: buy in 2023, sell in 2024
            _make_trade(timestamp=datetime(2023, 1, 1), type="Buy",
                        market_slug="market-b", price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        market_slug="market-b", price=0.70, shares=10, cost=7.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")

        assert result["transaction_count"] == 1
        tx = result["transactions"][0]
        assert tx["market_slug"] == "market-b"
        assert tx["cost_basis"] == pytest.approx(5.0)
        assert tx["gain_loss"] == pytest.approx(2.0)


# ===========================================================================
# BUG: year_end = datetime(tax_year, 12, 31, 23, 59, 59) misses trades
# with sub-second timestamps.  Fix: use datetime(tax_year + 1, 1, 1) with <.
# ===========================================================================

class TestYearBoundaryPrecision:
    """Year boundary should handle sub-second timestamps correctly."""

    def test_trade_at_last_microsecond_of_year_included(self):
        """A trade at 23:59:59.999999 on Dec 31 should be included."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2024, 12, 31, 23, 59, 59, 999999),
                        type="Sell", price=0.80, shares=10, cost=8.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        assert result["transaction_count"] == 1

    def test_trade_at_midnight_jan1_next_year_excluded(self):
        """A trade at exactly midnight Jan 1 next year should be excluded."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2025, 1, 1, 0, 0, 0),
                        type="Sell", price=0.80, shares=10, cost=8.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        assert result["transaction_count"] == 0

    def test_trade_at_midnight_jan1_same_year_included(self):
        """A trade at midnight Jan 1 of the tax year should be included."""
        trades = [
            _make_trade(timestamp=datetime(2023, 6, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2024, 1, 1, 0, 0, 0),
                        type="Sell", price=0.80, shares=10, cost=8.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        assert result["transaction_count"] == 1


# ===========================================================================
# Holding period classification (short-term vs long-term)
# ===========================================================================

class TestHoldingPeriodClassification:
    """Verify short-term vs long-term is correct at the 365-day boundary."""

    def test_exactly_365_days_is_long_term(self):
        """Holding for exactly 365 days should be long-term."""
        trades = [
            _make_trade(timestamp=datetime(2023, 3, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2024, 2, 29), type="Sell",  # 365 days later (2024 is leap year)
                        price=0.80, shares=10, cost=8.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        tx = result["transactions"][0]
        assert tx["holding_period"] == "long_term"

    def test_364_days_is_short_term(self):
        """Holding for 364 days should be short-term."""
        trades = [
            _make_trade(timestamp=datetime(2023, 3, 2), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2024, 2, 29), type="Sell",  # 364 days
                        price=0.80, shares=10, cost=8.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        tx = result["transactions"][0]
        assert tx["holding_period"] == "short_term"

    def test_short_and_long_term_separation(self):
        """Gains should be correctly split between short-term and long-term."""
        trades = [
            # Long-term lot: bought > 365 days before sell
            _make_trade(timestamp=datetime(2022, 6, 1), type="Buy",
                        price=0.30, shares=10, cost=3.0),
            # Short-term lot: bought < 365 days before sell
            _make_trade(timestamp=datetime(2024, 1, 15), type="Buy",
                        price=0.60, shares=10, cost=6.0),
            # Sell all 20 shares
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.80, shares=20, cost=16.0),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")

        assert result["transaction_count"] == 2
        # FIFO: first 10 from 2022 (long-term), next 10 from 2024 (short-term)
        assert result["long_term_gains"] == pytest.approx(5.0)   # 10 * (0.80 - 0.30)
        assert result["short_term_gains"] == pytest.approx(2.0)  # 10 * (0.80 - 0.60)


# ===========================================================================
# FIFO / LIFO / Average cost basis method correctness
# ===========================================================================

class TestCostBasisMethods:
    """Verify each cost basis method produces correct results."""

    @pytest.fixture
    def three_lot_trades(self):
        """Three buys at different prices, one sell of all."""
        return [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.30, shares=10, cost=3.0),
            _make_trade(timestamp=datetime(2024, 2, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Buy",
                        price=0.70, shares=10, cost=7.0),
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.60, shares=30, cost=18.0),
        ]

    def test_fifo_matches_oldest_first(self, three_lot_trades):
        result = calculate_capital_gains(three_lot_trades, tax_year=2024, cost_basis_method="fifo")

        # FIFO: matches $0.30, then $0.50, then $0.70
        assert result["transaction_count"] == 3
        total_cost = sum(tx["cost_basis"] for tx in result["transactions"])
        assert total_cost == pytest.approx(15.0)  # 3 + 5 + 7
        assert result["net_gain_loss"] == pytest.approx(3.0)  # 18 - 15

    def test_lifo_matches_newest_first(self, three_lot_trades):
        result = calculate_capital_gains(three_lot_trades, tax_year=2024, cost_basis_method="lifo")

        # LIFO: matches $0.70, then $0.50, then $0.30
        assert result["transaction_count"] == 3
        total_cost = sum(tx["cost_basis"] for tx in result["transactions"])
        assert total_cost == pytest.approx(15.0)  # 7 + 5 + 3
        assert result["net_gain_loss"] == pytest.approx(3.0)

    def test_average_uses_weighted_mean(self, three_lot_trades):
        result = calculate_capital_gains(three_lot_trades, tax_year=2024, cost_basis_method="average")

        # Average: (3 + 5 + 7) / 30 = $0.50 per share
        assert result["transaction_count"] == 1  # average creates one synthetic lot
        tx = result["transactions"][0]
        assert tx["cost_basis"] == pytest.approx(15.0)  # 30 * $0.50
        assert tx["gain_loss"] == pytest.approx(3.0)

    def test_invalid_method_raises(self):
        with pytest.raises(ValueError, match="Invalid cost basis method"):
            calculate_capital_gains([], tax_year=2024, cost_basis_method="invalid")


# ===========================================================================
# Large-value accuracy (million-dollar scenarios)
# ===========================================================================

class TestLargeValueAccuracy:
    """Verify calculations don't lose precision at high dollar amounts."""

    def test_million_dollar_trade_precision(self):
        """$1M+ trades should maintain cent-level precision."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.5500, shares=2_000_000, cost=1_100_000.00),
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.5501, shares=2_000_000, cost=1_100_200.00),
        ]

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")
        tx = result["transactions"][0]

        assert tx["proceeds"] == pytest.approx(1_100_200.00, abs=0.01)
        assert tx["cost_basis"] == pytest.approx(1_100_000.00, abs=0.01)
        assert tx["gain_loss"] == pytest.approx(200.00, abs=0.01)

    def test_many_small_trades_accumulate_correctly(self):
        """1000 small trades should sum correctly."""
        trades = []
        for i in range(1000):
            trades.append(_make_trade(
                timestamp=datetime(2024, 1, 1, i // 60, i % 60),
                type="Buy", price=0.50, shares=1.0, cost=0.50,
            ))
        trades.append(_make_trade(
            timestamp=datetime(2024, 6, 1), type="Sell",
            price=0.60, shares=1000.0, cost=600.0,
        ))

        result = calculate_capital_gains(trades, tax_year=2024, cost_basis_method="fifo")

        total_cost = sum(tx["cost_basis"] for tx in result["transactions"])
        total_proceeds = sum(tx["proceeds"] for tx in result["transactions"])
        assert total_cost == pytest.approx(500.0, abs=0.01)
        assert total_proceeds == pytest.approx(600.0, abs=0.01)
        assert result["net_gain_loss"] == pytest.approx(100.0, abs=0.01)
