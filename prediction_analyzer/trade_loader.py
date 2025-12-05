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

            trade = Trade(
                market=market_title,
                market_slug=market_slug,
                timestamp=pd.to_datetime(t.get("timestamp", t.get("blockTimestamp", 0)), unit='s'),
                price=float(t.get("price", 0)),
                shares=float(t.get("shares", t.get("outcomeTokenAmount", 0))),
                cost=float(t.get("cost", t.get("collateralAmount", 0))),
                type=t.get("type", t.get("strategy", "Buy")),
                side=t.get("side", "YES" if t.get("outcomeIndex", 0) == 0 else "NO"),
                pnl=float(t.get("pnl", 0)),
                tx_hash=t.get("tx_hash", t.get("transactionHash"))
            )
            trades.append(trade)

    except Exception as e:
        print(f"Error loading trades: {e}")
        return []

    return trades

def save_trades(trades: List[Trade], file_path: str):
    """Save trades to JSON file"""
    trades_dict = [vars(t) for t in trades]
    # Convert datetime to string for JSON serialization
    for t in trades_dict:
        if isinstance(t['timestamp'], datetime):
            t['timestamp'] = t['timestamp'].isoformat()

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(trades_dict, f, indent=2)
