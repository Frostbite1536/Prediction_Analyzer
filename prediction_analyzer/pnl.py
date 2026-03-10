# prediction_analyzer/pnl.py
"""
PnL calculation and analysis functions
"""
from decimal import Decimal
from typing import List, Dict
import pandas as pd
import numpy as np
from .trade_loader import Trade
from .inference import detect_market_resolution

def calculate_pnl(trades: List[Trade]) -> pd.DataFrame:
    """
    Calculate PnL metrics for a list of trades

    Args:
        trades: List of Trade objects

    Returns:
        DataFrame with PnL calculations
    """
    if not trades:
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame([vars(t) for t in trades])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Calculate individual trade PnL
    df["trade_pnl"] = df["pnl"]

    # Calculate cumulative PnL using Decimal accumulation to avoid float drift
    cumulative = []
    running = Decimal("0")
    for pnl_val in df["trade_pnl"]:
        running += Decimal(str(pnl_val))
        cumulative.append(float(running))
    df["cumulative_pnl"] = cumulative

    # Calculate exposure (net shares held)
    df["exposure"] = 0.0
    cumulative_shares = 0.0

    for idx, row in df.iterrows():
        if row["type"] in ["Buy", "Market Buy", "Limit Buy"]:
            cumulative_shares += row["shares"]
        elif row["type"] in ["Sell", "Market Sell", "Limit Sell"]:
            cumulative_shares -= row["shares"]
        df.at[idx, "exposure"] = cumulative_shares

    return df

def _summarize_trades(trades: List[Trade]) -> Dict:
    """Compute summary stats for a list of trades (single currency group)."""
    if not trades:
        return {
            "total_trades": 0, "total_volume": 0.0, "total_pnl": 0.0,
            "win_rate": 0.0, "avg_pnl_per_trade": 0.0, "avg_pnl": 0.0,
            "winning_trades": 0, "losing_trades": 0, "breakeven_trades": 0,
            "total_invested": 0.0, "total_returned": 0.0, "roi": 0.0,
        }
    df = pd.DataFrame([vars(t) for t in trades])

    buy_trades = df[df["type"].isin(["Buy", "Market Buy", "Limit Buy"])]
    sell_trades = df[df["type"].isin(["Sell", "Market Sell", "Limit Sell"])]
    total_invested = buy_trades["cost"].sum() if len(buy_trades) > 0 else 0.0
    total_returned = sell_trades["cost"].sum() if len(sell_trades) > 0 else 0.0
    total_volume = total_invested + total_returned
    total_pnl = df["pnl"].sum()
    total_trades = len(df)

    # Only count wins/losses among trades that have PnL set
    settled = df[df["pnl_is_set"] == True]
    winning_trades = len(settled[settled["pnl"] > 0])
    losing_trades = len(settled[settled["pnl"] < 0])
    breakeven_trades = len(settled[settled["pnl"] == 0])

    roi = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    trades_with_outcome = winning_trades + losing_trades
    win_rate = (winning_trades / trades_with_outcome * 100) if trades_with_outcome > 0 else 0.0

    return {
        "total_trades": total_trades,
        "total_volume": total_volume,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "avg_pnl_per_trade": total_pnl / total_trades if total_trades > 0 else 0,
        "avg_pnl": total_pnl / total_trades if total_trades > 0 else 0,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "breakeven_trades": breakeven_trades,
        "total_invested": total_invested,
        "total_returned": total_returned,
        "roi": roi,
    }


def calculate_global_pnl_summary(trades: List[Trade]) -> Dict:
    """
    Calculate global PnL summary across all trades.

    When trades span multiple currencies (e.g. USD/USDC vs MANA), the
    top-level totals only aggregate real-money currencies (USD, USDC).
    Play-money currencies (MANA) are reported separately under
    ``by_currency`` to avoid mixing incompatible units.

    Returns:
        Dictionary with summary statistics.  Always contains a
        ``by_currency`` key mapping each currency to its own summary
        when more than one currency is present.
    """
    if not trades:
        return {
            "total_trades": 0,
            "total_volume": 0.0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_pnl_per_trade": 0.0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "total_invested": 0.0,
            "total_returned": 0.0,
            "roi": 0.0,
            "avg_pnl": 0.0
        }

    # Group trades by currency
    _REAL_MONEY = {"USD", "USDC"}
    by_currency: Dict[str, List[Trade]] = {}
    for t in trades:
        cur = getattr(t, "currency", "USD")
        by_currency.setdefault(cur, []).append(t)

    currencies = set(by_currency.keys())

    # Primary summary: only real-money trades go into top-level totals
    real_money_trades = [t for t in trades if getattr(t, "currency", "USD") in _REAL_MONEY]
    if real_money_trades:
        result = _summarize_trades(real_money_trades)
        result["currency"] = "USD"  # normalized label for real-money aggregate
    else:
        # All trades are play-money — use them for top-level so it's not empty
        result = _summarize_trades(trades)
        first_cur = next(iter(by_currency))
        result["currency"] = first_cur

    # Per-currency breakdown (always present when >1 currency)
    if len(currencies) > 1:
        result["by_currency"] = {}
        for cur in sorted(currencies):
            cur_summary = _summarize_trades(by_currency[cur])
            cur_summary["currency"] = cur
            result["by_currency"][cur] = cur_summary

    # Per-source breakdown (kept for backward compat)
    by_source = {}
    sources = set(getattr(t, "source", "limitless") for t in trades)
    if len(sources) > 1:
        for source in sources:
            source_trades = [t for t in trades if getattr(t, "source", "limitless") == source]
            source_pnl = sum(t.pnl for t in source_trades)
            by_source[source] = {
                "total_trades": len(source_trades),
                "total_pnl": source_pnl,
                "currency": getattr(source_trades[0], "currency", "USD") if source_trades else "USD",
            }
        result["by_source"] = by_source

    return result

def calculate_market_pnl(trades: List[Trade]) -> Dict[str, Dict]:
    """
    Calculate PnL breakdown by market

    Returns:
        Dictionary mapping market_slug to PnL statistics
    """
    market_stats = {}

    for trade in trades:
        slug = trade.market_slug
        if slug not in market_stats:
            market_stats[slug] = {
                "market_name": trade.market,
                "total_volume": 0.0,
                "total_pnl": 0.0,
                "trade_count": 0
            }

        market_stats[slug]["total_volume"] += trade.cost
        market_stats[slug]["total_pnl"] += trade.pnl
        market_stats[slug]["trade_count"] += 1

    return market_stats

def calculate_market_pnl_summary(trades: List[Trade]) -> Dict:
    """
    Calculate detailed PnL summary for a specific market's trades

    Args:
        trades: List of Trade objects for a specific market

    Returns:
        Dictionary with market summary statistics
    """
    if not trades:
        return {
            "market_title": "Unknown Market",
            "total_trades": 0,
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_invested": 0.0,
            "total_returned": 0.0,
            "roi": 0.0,
            "market_outcome": None
        }

    # Get market title from first trade
    market_title = trades[0].market

    df = pd.DataFrame([vars(t) for t in trades])

    total_pnl = df["pnl"].sum()
    total_trades = len(df)

    # Only count wins/losses among trades that have PnL set
    settled = df[df["pnl_is_set"] == True]
    winning_trades = len(settled[settled["pnl"] > 0])
    losing_trades = len(settled[settled["pnl"] < 0])
    breakeven_trades = len(settled[settled["pnl"] == 0])

    # Calculate total invested and returned
    buy_trades = df[df["type"].isin(["Buy", "Market Buy", "Limit Buy"])]
    sell_trades = df[df["type"].isin(["Sell", "Market Sell", "Limit Sell"])]
    total_invested = buy_trades["cost"].sum() if len(buy_trades) > 0 else 0.0
    total_returned = sell_trades["cost"].sum() if len(sell_trades) > 0 else 0.0

    # Calculate ROI
    roi = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    # Win rate excludes breakeven trades from the denominator for accuracy
    trades_with_outcome = winning_trades + losing_trades
    win_rate = (winning_trades / trades_with_outcome * 100) if trades_with_outcome > 0 else 0.0

    # Try to infer market outcome from trade data
    market_outcome = detect_market_resolution(trades)

    return {
        "market_title": market_title,
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "avg_pnl": total_pnl / total_trades if total_trades > 0 else 0,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "breakeven_trades": breakeven_trades,
        "win_rate": win_rate,
        "total_invested": total_invested,
        "total_returned": total_returned,
        "roi": roi,
        "market_outcome": market_outcome
    }
