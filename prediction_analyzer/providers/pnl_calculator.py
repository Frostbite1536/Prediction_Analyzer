# prediction_analyzer/providers/pnl_calculator.py
"""
FIFO PnL computation for providers that don't supply per-trade PnL
(Kalshi, Manifold, Polymarket).
"""
from typing import List, Dict
from collections import defaultdict, deque

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
    # Skip if there are no sell trades needing PnL computation.
    # We cannot use `all(t.pnl != 0.0)` because legitimate zero-PnL
    # trades (breakeven) would incorrectly trigger a full recalc.
    if not trades:
        return trades

    # Group buys by (market_slug, side, source): deque of [price, remaining_shares]
    buy_queues: Dict[tuple, deque] = defaultdict(deque)

    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    for trade in sorted_trades:
        key = (trade.market_slug, trade.side, trade.source)
        is_buy = trade.type.lower() in ("buy", "market buy", "limit buy")
        is_sell = trade.type.lower() in ("sell", "market sell", "limit sell")

        if is_buy:
            buy_queues[key].append([trade.price, trade.shares])
        elif is_sell:
            # Always consume the buy queue to keep FIFO state correct,
            # even when trade already has a PnL value from the provider.
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
                    queue.popleft()

            # Only set PnL if trade doesn't already have one from the provider
            if trade.pnl == 0.0:
                matched_shares = trade.shares - remaining
                sell_revenue = matched_shares * trade.price
                trade.pnl = sell_revenue - total_buy_cost

    return trades
