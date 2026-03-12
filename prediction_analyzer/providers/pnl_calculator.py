# prediction_analyzer/providers/pnl_calculator.py
"""
FIFO PnL computation for providers that don't supply per-trade PnL
(Kalshi, Manifold, Polymarket).
"""

import logging
from decimal import Decimal
from typing import List, Dict
from collections import defaultdict, deque

from ..trade_loader import Trade

logger = logging.getLogger(__name__)


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
            buy_queues[key].append([Decimal(str(trade.price)), Decimal(str(trade.shares))])
        elif is_sell:
            # Always consume the buy queue to keep FIFO state correct,
            # even when trade already has a PnL value from the provider.
            remaining = Decimal(str(trade.shares))
            total_buy_cost = Decimal("0")
            queue = buy_queues[key]

            while remaining > 0 and queue:
                buy_price, buy_shares = queue[0]
                matched = min(remaining, buy_shares)
                total_buy_cost += matched * buy_price
                remaining -= matched
                queue[0][1] -= matched
                if queue[0][1] <= Decimal("1e-10"):
                    queue.popleft()

            if remaining > 0:
                logger.warning(
                    "Unmatched sell shares: %s shares for %s (market=%s, side=%s)",
                    remaining,
                    trade.type,
                    trade.market_slug,
                    trade.side,
                )

            # Only set PnL if trade doesn't already have one from the provider
            if not trade.pnl_is_set:
                matched_shares = Decimal(str(trade.shares)) - remaining
                sell_revenue = matched_shares * Decimal(str(trade.price))
                trade.pnl = float(sell_revenue - total_buy_cost)
                trade.pnl_is_set = True

    return trades
