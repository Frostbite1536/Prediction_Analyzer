# tests/test_fees_wash_sales.py
"""
Regression tests for:
- Fee tracking (Trade.fee field, tax report total_fees)
- Wash sale detection (IRS §1091 for prediction markets)
- Data completeness (total_trades_in_scope)
"""
import pytest
from datetime import datetime

from prediction_analyzer.trade_loader import Trade
from prediction_analyzer.tax import calculate_capital_gains, _detect_wash_sales


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
        "fee": 0.0,
    }
    defaults.update(kwargs)
    return Trade(**defaults)


# ===========================================================================
# Fee tracking
# ===========================================================================

class TestFeeTracking:
    """Fee field on Trade and fee accumulation in tax report."""

    def test_trade_fee_field_default(self):
        """Trade.fee defaults to 0.0."""
        t = _make_trade()
        assert t.fee == 0.0

    def test_trade_fee_field_set(self):
        """Trade.fee can be set explicitly."""
        t = _make_trade(fee=2.50)
        assert t.fee == 2.50

    def test_fee_in_to_dict(self):
        """Trade.to_dict() includes fee."""
        t = _make_trade(fee=1.25)
        d = t.to_dict()
        assert "fee" in d
        assert d["fee"] == 1.25

    def test_tax_report_total_fees_buy_only(self):
        """Tax report accumulates fees from buy trades."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.50, fee=0.50),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert result["total_fees"] == pytest.approx(0.50)

    def test_tax_report_total_fees_buy_and_sell(self):
        """Tax report accumulates fees from both buy and sell trades."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.50, fee=0.50),
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.70, shares=10, cost=6.70, fee=0.30),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert result["total_fees"] == pytest.approx(0.80)

    def test_tax_transaction_includes_sell_fee(self):
        """Tax transaction output includes fee when sell has fee > 0."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0, fee=0.0),
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.70, shares=10, cost=7.0, fee=0.25),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert result["transaction_count"] == 1
        tx = result["transactions"][0]
        assert "fee" in tx
        assert tx["fee"] == pytest.approx(0.25)

    def test_tax_transaction_omits_zero_fee(self):
        """Tax transaction output omits fee when sell fee is 0."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0, fee=0.0),
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.70, shares=10, cost=7.0, fee=0.0),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        tx = result["transactions"][0]
        assert "fee" not in tx

    def test_large_fee_accumulation(self):
        """Large fees (e.g. $60k trader) accumulate correctly."""
        trades = []
        for i in range(100):
            day = 1 + (i % 28)
            month = 1 + (i // 28) % 12
            trades.append(_make_trade(
                timestamp=datetime(2024, month, day, 10, 0, 0),
                type="Buy", price=0.50, shares=1000, cost=500.0 + 600.0,
                fee=600.0, market_slug=f"market-{i}",
            ))
        result = calculate_capital_gains(trades, tax_year=2024)
        assert result["total_fees"] == pytest.approx(60000.0)


# ===========================================================================
# Wash sale detection
# ===========================================================================

class TestWashSaleDetection:
    """Wash sale detection per IRS §1091 for prediction markets."""

    def test_basic_wash_sale_detected(self):
        """Sell at loss + repurchase within 30 days = wash sale."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.70, shares=10, cost=7.0, side="YES"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0, side="YES"),
            # Repurchase within 30 days
            _make_trade(timestamp=datetime(2024, 3, 15), type="Buy",
                        price=0.55, shares=10, cost=5.5, side="YES"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" in result
        assert len(result["wash_sales"]) == 1
        ws = result["wash_sales"][0]
        assert ws["disallowed_loss"] == pytest.approx(2.0)  # loss of $2

    def test_no_wash_sale_when_gain(self):
        """Sells at a gain should not trigger wash sale."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0, side="YES"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.70, shares=10, cost=7.0, side="YES"),
            _make_trade(timestamp=datetime(2024, 3, 15), type="Buy",
                        price=0.55, shares=10, cost=5.5, side="YES"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" not in result

    def test_no_wash_sale_outside_window(self):
        """Repurchase > 30 days after loss sale is not a wash sale."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.70, shares=10, cost=7.0, side="YES"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0, side="YES"),
            # Repurchase 45 days later — outside window
            _make_trade(timestamp=datetime(2024, 4, 15), type="Buy",
                        price=0.55, shares=10, cost=5.5, side="YES"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" not in result

    def test_wash_sale_cross_side(self):
        """Buy on NO side within 30 days of YES loss = wash sale (same market)."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.70, shares=10, cost=7.0, side="YES"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0, side="YES"),
            # Buy NO side within 30 days
            _make_trade(timestamp=datetime(2024, 3, 15), type="Buy",
                        price=0.45, shares=10, cost=4.5, side="NO"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" in result
        assert len(result["wash_sales"]) == 1

    def test_wash_sale_before_sell(self):
        """Buy within 30 days BEFORE the loss sale = wash sale."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.70, shares=10, cost=7.0, side="YES"),
            # Another buy 15 days before the sell
            _make_trade(timestamp=datetime(2024, 2, 14), type="Buy",
                        price=0.55, shares=5, cost=2.75, side="YES"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0, side="YES"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" in result
        assert len(result["wash_sales"]) == 1

    def test_wash_sale_disallowed_loss_total(self):
        """wash_sale_disallowed_loss sums all disallowed losses."""
        trades = [
            # Market A: loss + repurchase
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.80, shares=10, cost=8.0, side="YES",
                        market_slug="market-a"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0, side="YES",
                        market_slug="market-a"),
            _make_trade(timestamp=datetime(2024, 3, 10), type="Buy",
                        price=0.55, shares=10, cost=5.5, side="YES",
                        market_slug="market-a"),
            # Market B: loss + repurchase
            _make_trade(timestamp=datetime(2024, 2, 1), type="Buy",
                        price=0.90, shares=20, cost=18.0, side="YES",
                        market_slug="market-b", market="Market B"),
            _make_trade(timestamp=datetime(2024, 4, 1), type="Sell",
                        price=0.60, shares=20, cost=12.0, side="YES",
                        market_slug="market-b", market="Market B"),
            _make_trade(timestamp=datetime(2024, 4, 20), type="Buy",
                        price=0.65, shares=20, cost=13.0, side="YES",
                        market_slug="market-b", market="Market B"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" in result
        # Market A loss: $3.0, Market B loss: $6.0
        assert result["wash_sale_disallowed_loss"] == pytest.approx(9.0)

    def test_no_wash_sales_key_when_none(self):
        """Result should not contain wash_sales key when there are none."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.70, shares=10, cost=7.0),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" not in result
        assert "wash_sale_disallowed_loss" not in result

    def test_original_buy_not_flagged_as_wash_sale(self):
        """The original buy that established the position must NOT trigger
        a wash sale. Only REPLACEMENT purchases count."""
        trades = [
            # Buy on Feb 15, sell at loss on Mar 1 — only 14 days apart.
            # No repurchase. The original buy should NOT be flagged.
            _make_trade(timestamp=datetime(2024, 2, 15), type="Buy",
                        price=0.70, shares=10, cost=7.0, side="YES"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0, side="YES"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" not in result

    def test_same_date_multi_market_losses_independent(self):
        """Two losses on the same date in different markets should each
        be independently checked for wash sales (not short-circuited)."""
        trades = [
            # Market A: loss with repurchase
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.80, shares=10, cost=8.0, side="YES",
                        market_slug="market-a"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0, side="YES",
                        market_slug="market-a"),
            _make_trade(timestamp=datetime(2024, 3, 10), type="Buy",
                        price=0.55, shares=10, cost=5.5, side="YES",
                        market_slug="market-a"),
            # Market B: loss with repurchase, SAME SELL DATE
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.90, shares=10, cost=9.0, side="YES",
                        market_slug="market-b", market="Market B"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.60, shares=10, cost=6.0, side="YES",
                        market_slug="market-b", market="Market B"),
            _make_trade(timestamp=datetime(2024, 3, 15), type="Buy",
                        price=0.65, shares=10, cost=6.5, side="YES",
                        market_slug="market-b", market="Market B"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" in result
        # Both markets should be flagged — not just the first one
        flagged_slugs = {ws["market_slug"] for ws in result["wash_sales"]}
        assert "market-a" in flagged_slugs
        assert "market-b" in flagged_slugs

    def test_wash_sale_at_exactly_30_days(self):
        """Repurchase at exactly 30 days should be flagged."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.70, shares=10, cost=7.0, side="YES"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0, side="YES"),
            # Exactly 30 days later
            _make_trade(timestamp=datetime(2024, 3, 31), type="Buy",
                        price=0.55, shares=10, cost=5.5, side="YES"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" in result

    def test_wash_sale_at_31_days_not_flagged(self):
        """Repurchase at 31 days should NOT be flagged."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.70, shares=10, cost=7.0, side="YES"),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Sell",
                        price=0.50, shares=10, cost=5.0, side="YES"),
            # 31 days later
            _make_trade(timestamp=datetime(2024, 4, 1), type="Buy",
                        price=0.55, shares=10, cost=5.5, side="YES"),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert "wash_sales" not in result


# ===========================================================================
# Data completeness: total_trades_in_scope
# ===========================================================================

class TestDataCompleteness:
    """Tax report includes total_trades_in_scope for verification."""

    def test_total_trades_in_scope(self):
        """total_trades_in_scope counts all trades passed in."""
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2024, 3, 1), type="Buy",
                        price=0.60, shares=5, cost=3.0),
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.70, shares=10, cost=7.0),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert result["total_trades_in_scope"] == 3

    def test_excess_sell_logs_warning(self, caplog):
        """Selling more shares than available buy lots should log a warning."""
        import logging
        trades = [
            _make_trade(timestamp=datetime(2024, 1, 1), type="Buy",
                        price=0.50, shares=5, cost=2.5),
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.70, shares=10, cost=7.0),
        ]
        with caplog.at_level(logging.WARNING, logger="prediction_analyzer.tax"):
            result = calculate_capital_gains(trades, tax_year=2024)
            assert any("no matching buy lots" in msg for msg in caplog.messages)

    def test_total_trades_includes_all_years(self):
        """total_trades_in_scope includes trades from all years."""
        trades = [
            _make_trade(timestamp=datetime(2023, 1, 1), type="Buy",
                        price=0.50, shares=10, cost=5.0),
            _make_trade(timestamp=datetime(2024, 6, 1), type="Sell",
                        price=0.70, shares=10, cost=7.0),
        ]
        result = calculate_capital_gains(trades, tax_year=2024)
        assert result["total_trades_in_scope"] == 2
