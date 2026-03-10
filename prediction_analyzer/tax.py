# prediction_analyzer/tax.py
"""
Tax reporting: capital gains/losses with FIFO, LIFO, and average cost basis methods.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .trade_loader import Trade, sanitize_numeric

logger = logging.getLogger(__name__)

VALID_METHODS = {"fifo", "lifo", "average"}
LONG_TERM_THRESHOLD = timedelta(days=365)


def calculate_capital_gains(
    trades: List[Trade],
    tax_year: int,
    cost_basis_method: str = "fifo",
) -> Dict:
    """
    Generate capital gains/losses report for a tax year.

    Args:
        trades: List of Trade objects
        tax_year: Tax year to report on (e.g. 2025)
        cost_basis_method: One of "fifo", "lifo", "average"

    Returns:
        Dict with tax summary and per-transaction breakdown
    """
    if cost_basis_method not in VALID_METHODS:
        raise ValueError(f"Invalid cost basis method: {cost_basis_method}. Valid: {sorted(VALID_METHODS)}")

    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    # Filter to sells in the tax year
    year_start = datetime(tax_year, 1, 1)
    year_end = datetime(tax_year, 12, 31, 23, 59, 59)

    # Build buy lots per market
    buy_lots: Dict[str, List[Dict]] = {}  # market_slug -> list of {date, shares, price, cost}

    transactions = []
    short_term_gains = 0.0
    short_term_losses = 0.0
    long_term_gains = 0.0
    long_term_losses = 0.0

    for trade in sorted_trades:
        slug = trade.market_slug

        if trade.type in ("Buy", "Market Buy", "Limit Buy"):
            # Add to buy lots
            buy_lots.setdefault(slug, []).append({
                "date": trade.timestamp,
                "shares": trade.shares,
                "price": trade.price,
                "cost_per_share": (trade.cost / trade.shares) if trade.shares > 0 else 0.0,
            })

        elif trade.type in ("Sell", "Market Sell", "Limit Sell"):
            # Only process sells within the tax year
            if trade.timestamp < year_start or trade.timestamp > year_end:
                continue

            lots = buy_lots.get(slug, [])
            remaining_shares = trade.shares
            proceeds_per_share = (trade.cost / trade.shares) if trade.shares > 0 else 0.0

            while remaining_shares > 1e-10 and lots:
                if cost_basis_method == "fifo":
                    lot = lots[0]
                elif cost_basis_method == "lifo":
                    lot = lots[-1]
                else:  # average
                    lot = _average_lot(lots)

                matched_shares = min(remaining_shares, lot["shares"])
                cost_basis = matched_shares * lot["cost_per_share"]
                proceeds = matched_shares * proceeds_per_share
                gain_loss = proceeds - cost_basis

                # Determine holding period
                holding_delta = trade.timestamp - lot["date"]
                is_long_term = holding_delta >= LONG_TERM_THRESHOLD
                holding_period = "long_term" if is_long_term else "short_term"

                transactions.append({
                    "market": trade.market,
                    "market_slug": slug,
                    "date_acquired": lot["date"].strftime("%Y-%m-%d"),
                    "date_sold": trade.timestamp.strftime("%Y-%m-%d"),
                    "shares": sanitize_numeric(matched_shares),
                    "proceeds": sanitize_numeric(proceeds),
                    "cost_basis": sanitize_numeric(cost_basis),
                    "gain_loss": sanitize_numeric(gain_loss),
                    "holding_period": holding_period,
                })

                if is_long_term:
                    if gain_loss >= 0:
                        long_term_gains += gain_loss
                    else:
                        long_term_losses += abs(gain_loss)
                else:
                    if gain_loss >= 0:
                        short_term_gains += gain_loss
                    else:
                        short_term_losses += abs(gain_loss)

                remaining_shares -= matched_shares

                # Update or remove lot
                if cost_basis_method == "average":
                    # For average, reduce total pool
                    total_shares = sum(l["shares"] for l in lots)
                    if total_shares > 0:
                        ratio = matched_shares / total_shares
                        for l in lots:
                            l["shares"] -= l["shares"] * ratio
                        lots[:] = [l for l in lots if l["shares"] > 1e-10]
                else:
                    lot["shares"] -= matched_shares
                    if lot["shares"] <= 1e-10:
                        if cost_basis_method == "fifo":
                            lots.pop(0)
                        else:
                            lots.pop(-1)

    net_gain_loss = (short_term_gains - short_term_losses + long_term_gains - long_term_losses)

    return {
        "tax_year": tax_year,
        "method": cost_basis_method,
        "short_term_gains": sanitize_numeric(short_term_gains),
        "short_term_losses": sanitize_numeric(short_term_losses),
        "long_term_gains": sanitize_numeric(long_term_gains),
        "long_term_losses": sanitize_numeric(long_term_losses),
        "net_gain_loss": sanitize_numeric(net_gain_loss),
        "transaction_count": len(transactions),
        "transactions": transactions,
    }


def _average_lot(lots: List[Dict]) -> Dict:
    """Create a synthetic lot representing the weighted average of all lots."""
    total_shares = sum(l["shares"] for l in lots)
    if total_shares <= 0:
        return {"date": datetime(1970, 1, 1), "shares": 0, "price": 0, "cost_per_share": 0}

    weighted_cost = sum(l["shares"] * l["cost_per_share"] for l in lots) / total_shares
    # Use earliest date for holding period calculation
    earliest_date = min(l["date"] for l in lots)

    return {
        "date": earliest_date,
        "shares": total_shares,
        "price": weighted_cost,
        "cost_per_share": weighted_cost,
    }
