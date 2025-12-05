# prediction_analyzer/inference.py
"""
Market outcome inference logic
"""
from typing import Optional, Tuple, List
from .trade_loader import Trade
from .config import PRICE_RESOLUTION_THRESHOLD

def infer_resolved_side_from_trades(trades: List[Trade], threshold: float = PRICE_RESOLUTION_THRESHOLD) -> Tuple[Optional[str], Optional[Trade]]:
    """
    Infer the resolved outcome of a market from trade history

    Args:
        trades: List of trades for a market
        threshold: Price threshold for determining resolution (default 0.5 = 50 cents)

    Returns:
        Tuple of (inferred_side, latest_trade)
    """
    if not trades:
        return None, None

    # Get the latest trade
    latest = max(trades, key=lambda t: t.timestamp)
    price = latest.price
    side = latest.side

    if side not in {"YES", "NO"}:
        return None, latest

    threshold_cents = threshold * 100

    # If price is very high, assume the side being traded resolved YES
    # If price is very low, assume the opposite side resolved YES
    if price >= threshold_cents:
        inferred = side
    else:
        inferred = "NO" if side == "YES" else "YES"

    return inferred, latest

def detect_market_resolution(trades: List[Trade]) -> Optional[str]:
    """
    Detect if market is resolved by looking for resolution events

    Returns:
        "YES", "NO", or None if not resolved
    """
    # Look for explicit resolution indicators in trade data
    for trade in reversed(trades):  # Check most recent first
        # Check if trade has resolution info
        if hasattr(trade, 'resolution'):
            return trade.resolution

        # Check for claim/result events
        if trade.type in ["Claim", "Won", "Loss"]:
            return trade.side

    return None
