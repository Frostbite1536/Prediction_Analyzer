# tests/test_bugfixes.py
"""
Regression tests for bugs identified in the codebase audit.

Each test class corresponds to a specific bug fix and verifies the
fix works correctly without regressions.
"""
import json
import math
import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch

from prediction_analyzer.trade_loader import Trade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
        "source": "limitless",
        "currency": "USD",
    }
    defaults.update(kwargs)
    return Trade(**defaults)


# ===========================================================================
# Bug #3: Sortino ratio uses population variance (ddof=0) while Sharpe uses
# sample variance (ddof=1).  Fix: use ddof=1 for Sortino as well.
# ===========================================================================

class TestSortinoDdofConsistency:
    """Sortino ratio should use ddof=1 (Bessel's correction), matching Sharpe."""

    def test_sortino_uses_sample_variance(self):
        """Verify the downside deviation uses N-1 denominator."""
        from prediction_analyzer.metrics import _risk_adjusted_metrics

        # All-negative returns: easy to verify by hand
        pnls = [-1.0, -2.0, -3.0]
        result = _risk_adjusted_metrics(pnls)

        arr = np.array(pnls)
        mean_ret = np.mean(arr)
        downside = np.minimum(arr, 0.0)
        # ddof=1: divide by (N - 1)
        expected_dd = np.sqrt(np.sum(downside ** 2) / (len(arr) - 1))
        expected_sortino = mean_ret / expected_dd

        assert abs(result["sortino_ratio"] - round(expected_sortino, 4)) < 1e-4

    def test_sortino_not_population_variance(self):
        """Ensure the old ddof=0 formula is no longer used."""
        from prediction_analyzer.metrics import _risk_adjusted_metrics

        pnls = [-1.0, -2.0, -3.0]
        result = _risk_adjusted_metrics(pnls)

        arr = np.array(pnls)
        mean_ret = np.mean(arr)
        # Old (wrong) formula: ddof=0
        old_dd = np.sqrt(np.mean(np.minimum(arr, 0.0) ** 2))
        old_sortino = round(mean_ret / old_dd, 4)

        # The new result should differ from the old ddof=0 computation
        assert result["sortino_ratio"] != old_sortino

    def test_sortino_two_element_list(self):
        """Minimum valid input (len=2) should not divide by zero."""
        from prediction_analyzer.metrics import _risk_adjusted_metrics

        result = _risk_adjusted_metrics([-1.0, -2.0])
        assert math.isfinite(result["sortino_ratio"])

    def test_single_trade_returns_zero(self):
        """With fewer than 2 trades, Sortino should be 0.0."""
        from prediction_analyzer.metrics import _risk_adjusted_metrics

        result = _risk_adjusted_metrics([5.0])
        assert result["sortino_ratio"] == 0.0


# ===========================================================================
# Bug #4: Hardcoded '$' in report_text.py per-market sections.
# Fix: use cur_symbol derived from the portfolio's currency.
# ===========================================================================

class TestReportCurrencySymbol:
    """Per-market report sections should use the portfolio's currency symbol."""

    def test_mana_trades_use_mana_symbol_in_top_markets(self):
        """Top markets section should use M$ for MANA trades."""
        from prediction_analyzer.reporting.report_text import print_global_summary
        import io

        trades = [
            _make_trade(
                market="Q1", market_slug="q1", pnl=10.0, pnl_is_set=True,
                cost=5.0, type="Buy", currency="MANA", source="manifold",
            ),
            _make_trade(
                market="Q1", market_slug="q1", pnl=-3.0, pnl_is_set=True,
                cost=3.0, type="Sell", currency="MANA", source="manifold",
            ),
        ]
        buf = io.StringIO()
        print_global_summary(trades, stream=buf)
        output = buf.getvalue()

        # The top-markets line should contain M$ not bare $
        lines = [l for l in output.splitlines() if "q1" in l.lower() or "Q1" in l]
        assert any("M$" in line for line in lines), (
            f"Expected M$ in top-markets lines, got: {lines}"
        )

    def test_usd_trades_use_dollar_sign(self):
        """USD trades should still use $ in the per-market section."""
        from prediction_analyzer.reporting.report_text import generate_text_report
        import tempfile, os

        trades = [
            _make_trade(
                market="Election", market_slug="election", pnl=5.0,
                pnl_is_set=True, cost=10.0, type="Buy", currency="USD",
            ),
        ]
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            fname = f.name
        try:
            generate_text_report(trades, filename=fname)
            with open(fname) as f:
                content = f.read()
            # Should contain $ (from cur_symbol)
            assert "$" in content
        finally:
            os.unlink(fname)


# ===========================================================================
# Bug #5: export_to_json uses vars(t) instead of t.to_dict(), bypassing
# NaN/Inf sanitization and producing invalid JSON.
# ===========================================================================

class TestJsonExportUsesToDict:
    """export_to_json should use to_dict() for NaN/Inf sanitization."""

    def test_nan_pnl_produces_valid_json(self, tmp_path):
        """NaN in pnl should be sanitized to 0.0 in JSON output."""
        from prediction_analyzer.reporting.report_data import export_to_json

        trades = [_make_trade(pnl=float('nan'), pnl_is_set=True)]
        outfile = str(tmp_path / "test.json")
        export_to_json(trades, filename=outfile)

        with open(outfile) as f:
            data = json.load(f)  # Would raise if NaN leaked through

        assert data[0]["pnl"] == 0.0

    def test_inf_cost_produces_valid_json(self, tmp_path):
        """Infinity in cost should be sanitized in JSON output."""
        from prediction_analyzer.reporting.report_data import export_to_json

        trades = [_make_trade(cost=float('inf'))]
        outfile = str(tmp_path / "test.json")
        export_to_json(trades, filename=outfile)

        with open(outfile) as f:
            data = json.load(f)

        assert math.isfinite(data[0]["cost"])

    def test_timestamp_serialized_as_string(self, tmp_path):
        """Timestamps should be ISO strings in JSON output."""
        from prediction_analyzer.reporting.report_data import export_to_json

        trades = [_make_trade()]
        outfile = str(tmp_path / "test.json")
        export_to_json(trades, filename=outfile)

        with open(outfile) as f:
            data = json.load(f)

        assert isinstance(data[0]["timestamp"], str)
        assert "2024" in data[0]["timestamp"]


# ===========================================================================
# Bug #6: group_trades_by_market uses a different grouping key than
# calculate_market_pnl.  Fix: both use trade.market_slug.
# ===========================================================================

class TestGroupingKeyConsistency:
    """group_trades_by_market and calculate_market_pnl should use the same key."""

    def test_group_trades_uses_market_slug(self):
        """group_trades_by_market should group by market_slug."""
        from prediction_analyzer.trade_filter import group_trades_by_market

        trades = [
            _make_trade(market="Alpha", market_slug="alpha-slug"),
            _make_trade(market="Beta", market_slug="beta-slug"),
            _make_trade(market="Alpha Again", market_slug="alpha-slug"),
        ]
        grouped = group_trades_by_market(trades)

        assert "alpha-slug" in grouped
        assert "beta-slug" in grouped
        assert len(grouped["alpha-slug"]) == 2

    def test_consistent_with_calculate_market_pnl(self):
        """Keys from group_trades_by_market should match calculate_market_pnl."""
        from prediction_analyzer.trade_filter import group_trades_by_market
        from prediction_analyzer.pnl import calculate_market_pnl

        trades = [
            _make_trade(market="M1", market_slug="m1-slug", pnl=5.0, pnl_is_set=True),
            _make_trade(market="M2", market_slug="m2-slug", pnl=-2.0, pnl_is_set=True),
        ]
        group_keys = set(group_trades_by_market(trades).keys())
        pnl_keys = set(calculate_market_pnl(trades).keys())

        assert group_keys == pnl_keys


# ===========================================================================
# Bug #7: filter_by_date adds timedelta(days=1) when `end` is a datetime,
# silently extending the range by 24 hours.
# Fix: only add the extra day for string dates (midnight-based).
# ===========================================================================

class TestFilterByDateDatetimeEnd:
    """filter_by_date should not add 24h when end is a datetime."""

    def test_datetime_end_is_exclusive_upper_bound(self):
        """A datetime end value should be an exclusive upper bound, no extra day."""
        from prediction_analyzer.filters import filter_by_date

        trades = [
            _make_trade(timestamp=datetime(2024, 3, 10, 12, 0)),
            _make_trade(timestamp=datetime(2024, 3, 10, 18, 0)),
            _make_trade(timestamp=datetime(2024, 3, 11, 6, 0)),
        ]
        # End at 15:00 on March 10 — should exclude 18:00 and March 11
        result = filter_by_date(trades, end=datetime(2024, 3, 10, 15, 0))
        assert len(result) == 1
        assert result[0].timestamp == datetime(2024, 3, 10, 12, 0)

    def test_string_end_still_includes_full_day(self):
        """String end dates should still include the entire day."""
        from prediction_analyzer.filters import filter_by_date

        trades = [
            _make_trade(timestamp=datetime(2024, 3, 10, 23, 59)),
            _make_trade(timestamp=datetime(2024, 3, 11, 0, 0, 1)),
        ]
        result = filter_by_date(trades, end="2024-03-10")
        assert len(result) == 1
        assert result[0].timestamp.day == 10


# ===========================================================================
# Bug #8: Manifold classifies zero-amount trades as "Buy".
# Fix: zero-amount trades are classified as "Buy" (amount >= 0).
# This is now explicit rather than an accidental fallthrough.
# ===========================================================================

class TestManifoldZeroAmountTrade:
    """Manifold provider should handle zero-amount trades explicitly."""

    def test_zero_amount_classified_as_buy(self):
        """A zero-amount bet should be classified as Buy (not an error)."""
        from prediction_analyzer.providers.manifold import ManifoldProvider

        provider = ManifoldProvider()
        raw = {
            "amount": 0,
            "shares": 0,
            "outcome": "YES",
            "createdTime": 1704067200000,
            "id": "test-zero",
        }
        trade = provider.normalize_trade(raw, market_meta={"question": "Q", "slug": "q"})
        assert trade.type == "Buy"

    def test_positive_amount_is_buy(self):
        """Positive amount should be Buy."""
        from prediction_analyzer.providers.manifold import ManifoldProvider

        provider = ManifoldProvider()
        raw = {"amount": 10, "shares": 10, "outcome": "YES", "createdTime": 0, "id": "t1"}
        trade = provider.normalize_trade(raw, market_meta={})
        assert trade.type == "Buy"

    def test_negative_amount_is_sell(self):
        """Negative amount should be Sell."""
        from prediction_analyzer.providers.manifold import ManifoldProvider

        provider = ManifoldProvider()
        raw = {"amount": -10, "shares": 10, "outcome": "NO", "createdTime": 0, "id": "t2"}
        trade = provider.normalize_trade(raw, market_meta={})
        assert trade.type == "Sell"


# ===========================================================================
# Bug #10: inference.py docstring says threshold default is 0.5, but the
# actual default is PRICE_RESOLUTION_THRESHOLD = 0.85.
# ===========================================================================

class TestInferenceDocstring:
    """Verify inference function's default threshold matches documentation."""

    def test_default_threshold_matches_config(self):
        """The default threshold should be PRICE_RESOLUTION_THRESHOLD (0.85)."""
        from prediction_analyzer.inference import infer_resolved_side_from_trades
        from prediction_analyzer.config import PRICE_RESOLUTION_THRESHOLD
        import inspect

        sig = inspect.signature(infer_resolved_side_from_trades)
        default = sig.parameters["threshold"].default
        assert default == PRICE_RESOLUTION_THRESHOLD

    def test_docstring_mentions_correct_threshold(self):
        """The docstring should reference 0.85, not 0.5."""
        from prediction_analyzer.inference import infer_resolved_side_from_trades

        doc = infer_resolved_side_from_trades.__doc__
        assert "0.5" not in doc
        assert "0.85" in doc
