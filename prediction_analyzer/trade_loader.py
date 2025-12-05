# prediction_analyzer/trade_loader.py
"""
Trade loading functionality - supports JSON, CSV, XLSX
"""
import json
import pandas as pd
from dataclasses import dataclass
from typing import List, Union, Optional
from datetime import datetime

@dataclass
class Trade:
    """Data class representing a single trade"""
    market: str
    market_slug: str
    timestamp: datetime
    price: float
    shares: float
    cost: float
    type: str  # "Buy" or "Sell"
    side: str  # "YES" or "NO"
    pnl: float = 0.0
    tx_hash: Optional[str] = None

def load_trades(file_path: str) -> List[Trade]:
    """
    Load trades from JSON, CSV, or XLSX file

    Args:
        file_path: Path to the trade file

    Returns:
        List of Trade objects
    """
    trades = []

    try:
        if file_path.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                raw_trades = json.load(f)
        elif file_path.endswith(".csv"):
            raw_trades = pd.read_csv(file_path).to_dict(orient="records")
        elif file_path.endswith(".xlsx"):
            raw_trades = pd.read_excel(file_path).to_dict(orient="records")
        else:
            raise ValueError("Unsupported file type. Use JSON, CSV, or XLSX.")

        for t in raw_trades:
            # Handle both old and new format
            market_data = t.get("market", {})
            if isinstance(market_data, dict):
                market_title = market_data.get("title", "Unknown")
                market_slug = market_data.get("slug", "unknown")
            else:
                market_title = t.get("market", "Unknown")
                market_slug = t.get("market_slug", "unknown")

            # Convert from micro-units (USDC has 6 decimals)
            # If data comes from API (has collateralAmount), values are in micro-units
            if "collateralAmount" in t:
                # API data - convert from micro-units to regular units
                raw_cost = float(t.get("collateralAmount", 0)) / 1_000_000
                raw_pnl = float(t.get("pnl", 0)) / 1_000_000
                raw_shares = float(t.get("outcomeTokenAmount", 0)) / 1_000_000
            else:
                # File data - already in regular units
                raw_cost = float(t.get("cost", 0))
                raw_pnl = float(t.get("pnl", 0))
                raw_shares = float(t.get("shares", 0))

            trade = Trade(
                market=market_title,
                market_slug=market_slug,
                timestamp=pd.to_datetime(t.get("timestamp", t.get("blockTimestamp", 0)), unit='s'),
                price=float(t.get("price", 0)),
                shares=raw_shares,
                cost=raw_cost,
                type=t.get("type", t.get("strategy", "Buy")),
                side=t.get("side", "YES" if t.get("outcomeIndex", 0) == 0 else "NO"),
                pnl=raw_pnl,
                tx_hash=t.get("tx_hash", t.get("transactionHash"))
            )
            trades.append(trade)

    except Exception as e:
        print(f"Error loading trades: {e}")
        return []

    return trades

def save_trades(trades: List[Union[Trade, dict]], file_path: str):
    """Save trades to JSON file"""
    # Handle both Trade objects and raw dictionaries
    trades_dict = []
    for t in trades:
        if isinstance(t, dict):
            trades_dict.append(t)
        else:
            # It's a Trade object, convert using vars()
            trades_dict.append(vars(t))

    # Convert datetime to string for JSON serialization
    for t in trades_dict:
        if 'timestamp' in t and isinstance(t['timestamp'], datetime):
            t['timestamp'] = t['timestamp'].isoformat()

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(trades_dict, f, indent=2)
