# prediction_analyzer/metrics.py
"""
Advanced trading performance metrics for prediction market traders.

Provides risk-adjusted metrics beyond basic PnL:
- Sharpe Ratio, Sortino Ratio
- Maximum Drawdown (amount, percentage, duration)
- Profit Factor, Expectancy
- Win/Loss Streak analysis
- Period-over-period comparison
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np
from .trade_loader import Trade


def calculate_advanced_metrics(trades: List[Trade]) -> Dict:
    """
    Calculate comprehensive trading performance metrics.

    Args:
        trades: List of Trade objects (should be sorted by timestamp)

    Returns:
        Dictionary with all advanced metrics
    """
    if not trades:
        return _empty_metrics()

    sorted_trades = sorted(trades, key=lambda t: t.timestamp)
    pnls = [t.pnl for t in sorted_trades]

    metrics = {}
    metrics.update(_basic_stats(pnls))
    metrics.update(_drawdown_metrics(pnls))
    metrics.update(_risk_adjusted_metrics(pnls))
    metrics.update(_streak_metrics(pnls))
    metrics.update(_trade_size_metrics(sorted_trades))

    return metrics


def _empty_metrics() -> Dict:
    """Return empty metrics dict when no trades exist."""
    return {
        "profit_factor": 0.0,
        "expectancy": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "largest_win": 0.0,
        "largest_loss": 0.0,
        "max_drawdown": 0.0,
        "max_drawdown_pct": 0.0,
        "max_drawdown_duration_trades": 0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "max_win_streak": 0,
        "max_loss_streak": 0,
        "current_streak": 0,
        "current_streak_type": None,
        "avg_trade_size": 0.0,
        "total_volume": 0.0,
    }


def _basic_stats(pnls: List[float]) -> Dict:
    """Calculate basic win/loss statistics."""
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0
    total_wins = sum(wins)
    total_losses = abs(sum(losses))

    profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf') if total_wins > 0 else 0.0
    # Cap inf for serialization
    if profit_factor == float('inf'):
        profit_factor = 999.99

    # Expectancy: average PnL per trade
    expectancy = float(np.mean(pnls)) if pnls else 0.0

    return {
        "profit_factor": round(profit_factor, 2),
        "expectancy": round(expectancy, 4),
        "avg_win": round(float(avg_win), 4),
        "avg_loss": round(float(avg_loss), 4),
        "largest_win": round(max(pnls), 4) if pnls else 0.0,
        "largest_loss": round(min(pnls), 4) if pnls else 0.0,
    }


def _drawdown_metrics(pnls: List[float]) -> Dict:
    """Calculate maximum drawdown metrics."""
    if not pnls:
        return {"max_drawdown": 0.0, "max_drawdown_pct": 0.0, "max_drawdown_duration_trades": 0}

    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdowns = peak - cumulative

    max_dd = float(np.max(drawdowns))
    peak_at_max_dd = float(peak[np.argmax(drawdowns)])
    max_dd_pct = (max_dd / peak_at_max_dd * 100) if peak_at_max_dd > 0 else 0.0

    # Calculate drawdown duration (in number of trades)
    max_duration = 0
    current_duration = 0
    for dd in drawdowns:
        if dd > 0:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            current_duration = 0

    return {
        "max_drawdown": round(max_dd, 4),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "max_drawdown_duration_trades": max_duration,
    }


def _risk_adjusted_metrics(pnls: List[float]) -> Dict:
    """Calculate Sharpe and Sortino ratios."""
    if len(pnls) < 2:
        return {"sharpe_ratio": 0.0, "sortino_ratio": 0.0}

    arr = np.array(pnls, dtype=float)
    mean_return = np.mean(arr)
    std_return = np.std(arr, ddof=1)

    # Sharpe ratio (risk-free rate assumed 0 for prediction markets)
    sharpe = (mean_return / std_return) if std_return > 0 else 0.0

    # Sortino ratio (only downside deviation)
    downside = arr[arr < 0]
    downside_std = np.std(downside, ddof=1) if len(downside) > 1 else 0.0
    sortino = (mean_return / downside_std) if downside_std > 0 else 0.0

    return {
        "sharpe_ratio": round(float(sharpe), 4),
        "sortino_ratio": round(float(sortino), 4),
    }


def _streak_metrics(pnls: List[float]) -> Dict:
    """Calculate win/loss streak metrics."""
    if not pnls:
        return {"max_win_streak": 0, "max_loss_streak": 0, "current_streak": 0, "current_streak_type": None}

    max_win = 0
    max_loss = 0
    current = 0
    current_type = None

    for pnl in pnls:
        if pnl > 0:
            if current_type == "win":
                current += 1
            else:
                current = 1
                current_type = "win"
            max_win = max(max_win, current)
        elif pnl < 0:
            if current_type == "loss":
                current += 1
            else:
                current = 1
                current_type = "loss"
            max_loss = max(max_loss, current)
        # breakeven trades don't break streaks

    return {
        "max_win_streak": max_win,
        "max_loss_streak": max_loss,
        "current_streak": current,
        "current_streak_type": current_type,
    }


def _trade_size_metrics(trades: List[Trade]) -> Dict:
    """Calculate trade size statistics."""
    costs = [t.cost for t in trades if t.cost > 0]
    return {
        "avg_trade_size": round(float(np.mean(costs)), 4) if costs else 0.0,
        "total_volume": round(sum(costs), 4),
    }


def format_metrics_report(metrics: Dict) -> str:
    """
    Format advanced metrics as a readable text report.

    Args:
        metrics: Dictionary from calculate_advanced_metrics()

    Returns:
        Formatted multi-line string
    """
    lines = []
    lines.append("=" * 50)
    lines.append("ADVANCED TRADING METRICS")
    lines.append("=" * 50)

    lines.append("\nRisk-Adjusted Returns:")
    lines.append(f"  Sharpe Ratio:          {metrics['sharpe_ratio']:.4f}")
    lines.append(f"  Sortino Ratio:         {metrics['sortino_ratio']:.4f}")

    lines.append("\nProfit Quality:")
    lines.append(f"  Profit Factor:         {metrics['profit_factor']:.2f}")
    lines.append(f"  Expectancy per Trade:  ${metrics['expectancy']:.4f}")
    lines.append(f"  Avg Win:               ${metrics['avg_win']:.4f}")
    lines.append(f"  Avg Loss:              ${metrics['avg_loss']:.4f}")
    lines.append(f"  Largest Win:           ${metrics['largest_win']:.4f}")
    lines.append(f"  Largest Loss:          ${metrics['largest_loss']:.4f}")

    lines.append("\nDrawdown:")
    lines.append(f"  Max Drawdown:          ${metrics['max_drawdown']:.4f}")
    lines.append(f"  Max Drawdown %:        {metrics['max_drawdown_pct']:.2f}%")
    lines.append(f"  Max DD Duration:       {metrics['max_drawdown_duration_trades']} trades")

    lines.append("\nStreaks:")
    lines.append(f"  Max Win Streak:        {metrics['max_win_streak']}")
    lines.append(f"  Max Loss Streak:       {metrics['max_loss_streak']}")
    streak_type = metrics.get('current_streak_type', 'none')
    lines.append(f"  Current Streak:        {metrics['current_streak']} ({streak_type})")

    lines.append("\nVolume:")
    lines.append(f"  Avg Trade Size:        ${metrics['avg_trade_size']:.4f}")
    lines.append(f"  Total Volume:          ${metrics['total_volume']:.4f}")

    lines.append("\n" + "=" * 50)
    return "\n".join(lines)
