# prediction_analyzer/drawdown.py
"""
Detailed drawdown analysis with date-aware tracking.

Extends the basic drawdown metrics from metrics.py with full
drawdown period identification and recovery analysis.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np
from .trade_loader import Trade, sanitize_numeric

logger = logging.getLogger(__name__)


def analyze_drawdowns(
    trades: List[Trade],
    market_slug: Optional[str] = None,
) -> Dict:
    """
    Analyze maximum drawdown periods including duration and recovery.

    Args:
        trades: List of Trade objects
        market_slug: Optional market slug to filter

    Returns:
        Dict with drawdown analysis including:
            max_drawdown_amount, max_drawdown_pct, peak/trough values,
            drawdown dates, duration, recovery info, current drawdown state,
            and list of all drawdown periods
    """
    if market_slug:
        trades = [t for t in trades if t.market_slug == market_slug]

    if not trades:
        return _empty_drawdown()

    sorted_trades = sorted(trades, key=lambda t: t.timestamp)
    pnls = [t.pnl for t in sorted_trades]
    timestamps = [t.timestamp for t in sorted_trades]

    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdowns = peak - cumulative

    # Find the maximum drawdown
    max_dd_idx = int(np.argmax(drawdowns))
    max_dd = float(drawdowns[max_dd_idx])
    peak_value = float(peak[max_dd_idx])
    trough_value = float(cumulative[max_dd_idx])
    max_dd_pct = (max_dd / peak_value * 100) if peak_value > 0 else 0.0

    # Find drawdown start (last peak before max drawdown)
    dd_start_idx = max_dd_idx
    for i in range(max_dd_idx, -1, -1):
        if drawdowns[i] == 0:
            dd_start_idx = i
            break

    # Find recovery (first return to peak after max drawdown)
    recovery_idx = None
    for i in range(max_dd_idx, len(drawdowns)):
        if drawdowns[i] == 0 and i > max_dd_idx:
            recovery_idx = i
            break

    dd_start_date = timestamps[dd_start_idx].strftime("%Y-%m-%d")
    dd_end_date = timestamps[max_dd_idx].strftime("%Y-%m-%d")
    recovery_date = timestamps[recovery_idx].strftime("%Y-%m-%d") if recovery_idx else None

    dd_duration = (timestamps[max_dd_idx] - timestamps[dd_start_idx]).days
    recovery_duration = None
    if recovery_idx:
        recovery_duration = (timestamps[recovery_idx] - timestamps[max_dd_idx]).days

    # Current drawdown state
    current_dd = float(drawdowns[-1])
    is_in_drawdown = current_dd > 0

    # Identify all drawdown periods
    periods = _identify_drawdown_periods(drawdowns, cumulative, peak, timestamps)

    return {
        "max_drawdown_amount": sanitize_numeric(max_dd),
        "max_drawdown_pct": sanitize_numeric(max_dd_pct),
        "peak_value": sanitize_numeric(peak_value),
        "trough_value": sanitize_numeric(trough_value),
        "drawdown_start_date": dd_start_date,
        "drawdown_end_date": dd_end_date,
        "recovery_date": recovery_date,
        "drawdown_duration_days": dd_duration,
        "recovery_duration_days": recovery_duration,
        "current_drawdown": sanitize_numeric(current_dd),
        "is_in_drawdown": is_in_drawdown,
        "drawdown_periods": periods,
    }


def _identify_drawdown_periods(
    drawdowns: np.ndarray,
    cumulative: np.ndarray,
    peak: np.ndarray,
    timestamps: List[datetime],
) -> List[Dict]:
    """Identify all distinct drawdown periods."""
    periods = []
    in_dd = False
    start_idx = 0

    for i in range(len(drawdowns)):
        if drawdowns[i] > 0 and not in_dd:
            in_dd = True
            start_idx = max(0, i - 1)
        elif drawdowns[i] == 0 and in_dd:
            in_dd = False
            # Find the worst point in this period
            period_dds = drawdowns[start_idx:i]
            worst_idx = start_idx + int(np.argmax(period_dds))
            amount = float(drawdowns[worst_idx])
            peak_val = float(peak[worst_idx])
            pct = (amount / peak_val * 100) if peak_val > 0 else 0.0
            duration = (timestamps[i] - timestamps[start_idx]).days

            periods.append({
                "start": timestamps[start_idx].strftime("%Y-%m-%d"),
                "end": timestamps[i].strftime("%Y-%m-%d"),
                "amount": sanitize_numeric(amount),
                "pct": sanitize_numeric(pct),
                "duration_days": duration,
            })

    # Handle ongoing drawdown
    if in_dd:
        period_dds = drawdowns[start_idx:]
        worst_idx = start_idx + int(np.argmax(period_dds))
        amount = float(drawdowns[worst_idx])
        peak_val = float(peak[worst_idx])
        pct = (amount / peak_val * 100) if peak_val > 0 else 0.0
        duration = (timestamps[-1] - timestamps[start_idx]).days

        periods.append({
            "start": timestamps[start_idx].strftime("%Y-%m-%d"),
            "end": None,
            "amount": sanitize_numeric(amount),
            "pct": sanitize_numeric(pct),
            "duration_days": duration,
        })

    return periods


def _empty_drawdown() -> Dict:
    """Return empty drawdown analysis when no trades exist."""
    return {
        "max_drawdown_amount": 0.0,
        "max_drawdown_pct": 0.0,
        "peak_value": 0.0,
        "trough_value": 0.0,
        "drawdown_start_date": None,
        "drawdown_end_date": None,
        "recovery_date": None,
        "drawdown_duration_days": 0,
        "recovery_duration_days": None,
        "current_drawdown": 0.0,
        "is_in_drawdown": False,
        "drawdown_periods": [],
    }
