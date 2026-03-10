# prediction_analyzer/comparison.py
"""
Period-over-period performance comparison.
"""
import logging
from typing import List, Dict
from .trade_loader import Trade, sanitize_numeric
from .filters import filter_by_date
from .pnl import calculate_global_pnl_summary
from .metrics import calculate_advanced_metrics

logger = logging.getLogger(__name__)


def compare_periods(
    trades: List[Trade],
    period_1_start: str,
    period_1_end: str,
    period_2_start: str,
    period_2_end: str,
) -> Dict:
    """
    Compare trading performance between two time periods.

    Args:
        trades: List of Trade objects
        period_1_start: Start date for period 1 (YYYY-MM-DD)
        period_1_end: End date for period 1 (YYYY-MM-DD)
        period_2_start: Start date for period 2 (YYYY-MM-DD)
        period_2_end: End date for period 2 (YYYY-MM-DD)

    Returns:
        Dict with period_1, period_2 summaries and changes between them
    """
    p1_trades = filter_by_date(trades, start=period_1_start, end=period_1_end)
    p2_trades = filter_by_date(trades, start=period_2_start, end=period_2_end)

    p1_summary = calculate_global_pnl_summary(p1_trades)
    p2_summary = calculate_global_pnl_summary(p2_trades)

    p1_metrics = calculate_advanced_metrics(p1_trades)
    p2_metrics = calculate_advanced_metrics(p2_trades)

    p1_result = {
        "start_date": period_1_start,
        "end_date": period_1_end,
        "trades": p1_summary["total_trades"],
        "pnl": sanitize_numeric(p1_summary["total_pnl"]),
        "win_rate": sanitize_numeric(p1_summary["win_rate"]),
        "sharpe": sanitize_numeric(p1_metrics["sharpe_ratio"]),
        "avg_pnl": sanitize_numeric(p1_summary["avg_pnl"]),
    }

    p2_result = {
        "start_date": period_2_start,
        "end_date": period_2_end,
        "trades": p2_summary["total_trades"],
        "pnl": sanitize_numeric(p2_summary["total_pnl"]),
        "win_rate": sanitize_numeric(p2_summary["win_rate"]),
        "sharpe": sanitize_numeric(p2_metrics["sharpe_ratio"]),
        "avg_pnl": sanitize_numeric(p2_summary["avg_pnl"]),
    }

    # Calculate changes
    def _pct_change(old, new):
        if old == 0:
            return 0.0 if new == 0 else 100.0
        return sanitize_numeric(((new - old) / abs(old)) * 100)

    changes = {
        "pnl_change_pct": _pct_change(p1_result["pnl"], p2_result["pnl"]),
        "win_rate_change": sanitize_numeric(p2_result["win_rate"] - p1_result["win_rate"]),
        "sharpe_change": sanitize_numeric(p2_result["sharpe"] - p1_result["sharpe"]),
        "avg_pnl_change_pct": _pct_change(p1_result["avg_pnl"], p2_result["avg_pnl"]),
    }

    return {
        "period_1": p1_result,
        "period_2": p2_result,
        "changes": changes,
    }
