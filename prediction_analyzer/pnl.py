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
            "avg_pnl_per_trade": 0.0
        }

    df = pd.DataFrame([vars(t) for t in trades])

    total_volume = df["cost"].sum()
    total_pnl = df["pnl"].sum()
    winning_trades = len(df[df["pnl"] > 0])
    total_trades = len(df)

    return {
        "total_trades": total_trades,
        "total_volume": total_volume,
        "total_pnl": total_pnl,
        "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
        "avg_pnl_per_trade": total_pnl / total_trades if total_trades > 0 else 0,
        "winning_trades": winning_trades,
        "losing_trades": total_trades - winning_trades
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
