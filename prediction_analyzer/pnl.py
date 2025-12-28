# prediction_analyzer/pnl.py
"""
PnL calculation and analysis functions
"""
from typing import List, Dict
import pandas as pd
import numpy as np
from .trade_loader import Trade

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

    # Calculate cumulative PnL
    df["cumulative_pnl"] = df["trade_pnl"].cumsum()

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

def calculate_global_pnl_summary(trades: List[Trade]) -> Dict:
    """
    Calculate global PnL summary across all trades

    Returns:
        Dictionary with summary statistics
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
            "total_invested": 0.0,
            "total_returned": 0.0,
            "roi": 0.0,
            "avg_pnl": 0.0
        }

    df = pd.DataFrame([vars(t) for t in trades])

    total_volume = df["cost"].sum()
    total_pnl = df["pnl"].sum()
    winning_trades = len(df[df["pnl"] > 0])
    losing_trades = len(df[df["pnl"] < 0])
    breakeven_trades = len(df[df["pnl"] == 0])
    total_trades = len(df)

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
        "roi": roi
    }

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
    winning_trades = len(df[df["pnl"] > 0])
    losing_trades = len(df[df["pnl"] < 0])
    breakeven_trades = len(df[df["pnl"] == 0])
    total_trades = len(df)

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

    # Try to infer market outcome if available
    market_outcome = None
    if hasattr(trades[0], 'outcome') and trades[0].outcome:
        market_outcome = trades[0].outcome

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
