# prediction_analyzer/providers/pnl_calculator.py
"""
FIFO PnL computation for providers that don't supply per-trade PnL
(Kalshi, Manifold, Polymarket).
"""
from typing import List, Dict
from collections import defaultdict

from ..trade_loader import Trade


def compute_realized_pnl(trades: List[Trade]) -> List[Trade]:
    """Compute realized PnL from buy/sell pairs per market+side using FIFO matching.

    Modifies and returns the same Trade objects with updated pnl fields.
    Only updates trades whose pnl is currently 0.0.

    Args:
        trades: List of trades (may be unsorted).

    Returns:
        Same list with pnl field updated on sell trades.
    """
    # Skip if all trades already have PnL
    if all(t.pnl != 0.0 for t in trades):
        return trades

    # Group buys by (market_slug, side, source): list of [price, remaining_shares]
    buy_queues: Dict[tuple, list] = defaultdict(list)

    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    for trade in sorted_trades:
        key = (trade.market_slug, trade.side, trade.source)
        is_buy = trade.type.lower() in ("buy", "market buy", "limit buy")
        is_sell = trade.type.lower() in ("sell", "market sell", "limit sell")

        if is_buy:
            buy_queues[key].append([trade.price, trade.shares])
        elif is_sell and trade.pnl == 0.0:
            # FIFO match against buy queue
            remaining = trade.shares
            total_buy_cost = 0.0
            queue = buy_queues[key]

            while remaining > 0 and queue:
                buy_price, buy_shares = queue[0]
                matched = min(remaining, buy_shares)
                total_buy_cost += matched * buy_price
                remaining -= matched
                queue[0][1] -= matched
                if queue[0][1] <= 1e-10:
                    queue.pop(0)

            matched_shares = trade.shares - remaining
            sell_revenue = matched_shares * trade.price
            trade.pnl = sell_revenue - total_buy_cost

    return trades
