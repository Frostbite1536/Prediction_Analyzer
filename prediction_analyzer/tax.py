# prediction_analyzer/tax.py
"""
Tax reporting: capital gains/losses with FIFO, LIFO, and average cost basis methods.
"""

import logging
from decimal import Decimal
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .trade_loader import Trade, sanitize_numeric

logger = logging.getLogger(__name__)

VALID_METHODS = {"fifo", "lifo", "average"}
LONG_TERM_THRESHOLD = timedelta(days=365)
WASH_SALE_WINDOW = timedelta(days=30)

_BUY_TYPES = {"Buy", "Market Buy", "Limit Buy"}
_SELL_TYPES = {"Sell", "Market Sell", "Limit Sell", "Claim", "Won", "Loss"}


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
        raise ValueError(
            f"Invalid cost basis method: {cost_basis_method}. Valid: {sorted(VALID_METHODS)}"
        )

    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    # Filter to sells in the tax year
    year_start = datetime(tax_year, 1, 1)
    year_end = datetime(tax_year + 1, 1, 1)

    # Build buy lots per market
    buy_lots: Dict[str, List[Dict]] = {}  # market_slug -> list of {date, shares, price, cost}

    transactions = []
    short_term_gains = Decimal("0")
    short_term_losses = Decimal("0")
    long_term_gains = Decimal("0")
    long_term_losses = Decimal("0")
    total_fees = Decimal("0")
    tax_year_fees = Decimal("0")
    skipped_types: Dict[str, int] = {}  # trade types not recognized

    for trade in sorted_trades:
        slug = trade.market_slug

        if trade.type in _BUY_TYPES:
            # Track fees
            fee_d = Decimal(str(getattr(trade, "fee", 0.0)))
            total_fees += fee_d
            in_tax_year_buy = year_start <= trade.timestamp < year_end
            if in_tax_year_buy:
                tax_year_fees += fee_d
            # Add to buy lots
            buy_lots.setdefault(slug, []).append(
                {
                    "date": trade.timestamp,
                    "shares": trade.shares,
                    "price": trade.price,
                    "cost_per_share": (
                        Decimal(str(trade.cost / trade.shares))
                        if trade.shares > 0
                        else Decimal("0")
                    ),
                }
            )

        elif trade.type in _SELL_TYPES:
            # Track fees
            sell_fee = Decimal(str(getattr(trade, "fee", 0.0)))
            total_fees += sell_fee

            # Determine if this sell falls within the tax year
            in_tax_year = year_start <= trade.timestamp < year_end
            if in_tax_year:
                tax_year_fees += sell_fee

            # ALWAYS consume buy lots to keep FIFO/LIFO state correct,
            # even for sells outside the tax year.  Otherwise, lots
            # already sold in prior years would be double-counted as
            # cost basis for later sells.
            lots = buy_lots.get(slug, [])
            remaining_shares = trade.shares
            proceeds_per_share = (
                Decimal(str(trade.cost / trade.shares)) if trade.shares > 0 else Decimal("0")
            )

            while remaining_shares > 1e-10 and lots:
                if cost_basis_method == "fifo":
                    lot = lots[0]
                elif cost_basis_method == "lifo":
                    lot = lots[-1]
                else:  # average
                    lot = _average_lot(lots)

                matched_shares = min(remaining_shares, lot["shares"])

                # Only record transaction details for sells in the tax year
                if in_tax_year:
                    matched_d = Decimal(str(matched_shares))
                    cost_basis = float(matched_d * lot["cost_per_share"])
                    proceeds = float(matched_d * proceeds_per_share)
                    gain_loss = proceeds - cost_basis

                    # Determine holding period
                    holding_delta = trade.timestamp - lot["date"]
                    is_long_term = holding_delta >= LONG_TERM_THRESHOLD
                    holding_period = "long_term" if is_long_term else "short_term"

                    tx = {
                        "market": trade.market,
                        "market_slug": slug,
                        "date_acquired": lot["date"].strftime("%Y-%m-%d"),
                        "date_sold": trade.timestamp.strftime("%Y-%m-%d"),
                        "shares": sanitize_numeric(matched_shares),
                        "proceeds": sanitize_numeric(proceeds),
                        "cost_basis": sanitize_numeric(cost_basis),
                        "gain_loss": sanitize_numeric(gain_loss),
                        "holding_period": holding_period,
                    }
                    if sell_fee > 0:
                        tx["fee"] = sanitize_numeric(float(sell_fee))
                    transactions.append(tx)

                    gain_loss_d = Decimal(str(gain_loss))
                    if is_long_term:
                        if gain_loss_d >= 0:
                            long_term_gains += gain_loss_d
                        else:
                            long_term_losses += abs(gain_loss_d)
                    else:
                        if gain_loss_d >= 0:
                            short_term_gains += gain_loss_d
                        else:
                            short_term_losses += abs(gain_loss_d)

                remaining_shares -= matched_shares

                # Update or remove lot
                if cost_basis_method == "average":
                    # For average cost, reduce all lots proportionally to
                    # maintain the same weighted average cost per share.
                    # Lots are sorted chronologically; as each lot's shares
                    # reach zero it is removed, so _average_lot's min-date
                    # naturally advances FIFO for holding period purposes.
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

            # Warn if sell has shares with no matching buy lots
            if remaining_shares > 1e-10 and in_tax_year:
                logger.warning(
                    "Tax report: %.4f shares of %s sold on %s have no matching buy lots "
                    "(missing cost basis data)",
                    remaining_shares,
                    slug,
                    trade.timestamp.strftime("%Y-%m-%d"),
                )

        else:
            # Track unrecognized trade types so the caller knows
            skipped_types[trade.type] = skipped_types.get(trade.type, 0) + 1

    if skipped_types:
        logger.warning(
            "Tax report skipped %d trades with unrecognized types: %s",
            sum(skipped_types.values()),
            skipped_types,
        )

    # Detect wash sales
    wash_sales = _detect_wash_sales(transactions, sorted_trades)

    net_gain_loss = short_term_gains - short_term_losses + long_term_gains - long_term_losses

    result = {
        "tax_year": tax_year,
        "method": cost_basis_method,
        "total_trades_in_scope": len(sorted_trades),
        "short_term_gains": sanitize_numeric(float(short_term_gains)),
        "short_term_losses": sanitize_numeric(float(short_term_losses)),
        "long_term_gains": sanitize_numeric(float(long_term_gains)),
        "long_term_losses": sanitize_numeric(float(long_term_losses)),
        "net_gain_loss": sanitize_numeric(float(net_gain_loss)),
        "total_fees": sanitize_numeric(float(tax_year_fees)),
        "transaction_count": len(transactions),
        "transactions": transactions,
    }

    if wash_sales:
        result["wash_sales"] = wash_sales
        result["wash_sale_disallowed_loss"] = sanitize_numeric(
            sum(ws["disallowed_loss"] for ws in wash_sales)
        )

    if skipped_types:
        result["skipped_trade_types"] = skipped_types

    return result


def _average_lot(lots: List[Dict]) -> Dict:
    """Create a synthetic lot representing the weighted average of all lots.

    Cost per share is the pool-wide weighted average (all shares have equal
    cost under average basis).  The holding period date uses the earliest
    remaining lot, approximating FIFO per IRS Reg. 1.1012-1(e).
    """
    total_shares = sum(l["shares"] for l in lots)
    if total_shares <= 0:
        return {
            "date": datetime(1970, 1, 1),
            "shares": 0,
            "price": 0,
            "cost_per_share": Decimal("0"),
        }

    weighted_cost = sum(Decimal(str(l["shares"])) * l["cost_per_share"] for l in lots) / Decimal(
        str(total_shares)
    )
    # FIFO holding period: use the earliest lot's date (first lot consumed)
    earliest_date = min(l["date"] for l in lots)

    return {
        "date": earliest_date,
        "shares": total_shares,
        "price": weighted_cost,
        "cost_per_share": weighted_cost,
    }


def _detect_wash_sales(
    transactions: List[Dict],
    sorted_trades: List[Trade],
) -> List[Dict]:
    """Detect wash sales per IRS §1091.

    A wash sale occurs when a security is sold at a loss and a
    "substantially identical" security is *repurchased* within 30 days
    before or after the sale.  For prediction markets, "substantially
    identical" means the same market contract (market_slug), regardless
    of YES/NO side.

    Only buys that occur AFTER the sell (or within 30 days before it,
    but not before the position was originally acquired) count as
    replacement purchases.  The original buy that established the
    position is NOT a wash sale trigger.

    This function flags loss transactions that have a matching
    repurchase within the ±30 day window.  It does NOT adjust cost
    basis (that requires the CPA to handle), but reports the disallowed
    loss amount so the trader can file correctly.

    Returns:
        List of wash sale records with details for each flagged loss.
    """
    if not transactions:
        return []

    # Build a lookup: for each loss transaction, we need to find buys
    # that are REPLACEMENT purchases (not the original position buy).
    # A replacement buy is one that occurs within ±30 days of the sell
    # but is NOT the buy that was consumed to establish cost basis.
    #
    # Strategy: collect all buy timestamps per market_slug (across both
    # sides). For each loss tx, find buys within ±30 days of the sell
    # that occurred AFTER the acquisition date (i.e., they are new buys,
    # not the original position).
    buy_events: Dict[str, List[datetime]] = {}  # market_slug -> buy dates
    for trade in sorted_trades:
        if trade.type in _BUY_TYPES:
            buy_events.setdefault(trade.market_slug, []).append(trade.timestamp)

    wash_sales = []
    flagged_tx_ids: set = set()  # Track (slug, date_sold, date_acquired) to avoid duplicates

    for tx in transactions:
        # Only check loss transactions
        if tx["gain_loss"] >= 0:
            continue

        slug = tx["market_slug"]
        sell_date = datetime.strptime(tx["date_sold"], "%Y-%m-%d")
        acquired_date = datetime.strptime(tx["date_acquired"], "%Y-%m-%d")

        # Unique identity for this transaction (handles same-date multi-market)
        tx_id = (slug, tx["date_sold"], tx["date_acquired"])
        if tx_id in flagged_tx_ids:
            continue

        buy_dates = buy_events.get(slug, [])

        for buy_date in buy_dates:
            # Skip buys on or before the acquisition date — these are
            # the original position buys, not replacement purchases
            if buy_date.date() <= acquired_date.date():
                continue

            delta = abs((buy_date - sell_date).days)
            # IRS §1091: the wash sale window includes same-day repurchases
            # (delta == 0) as well as purchases within 30 days before/after.
            if delta <= 30:
                wash_sales.append(
                    {
                        "market": tx["market"],
                        "market_slug": slug,
                        "date_sold": tx["date_sold"],
                        "date_repurchased": buy_date.strftime("%Y-%m-%d"),
                        "disallowed_loss": sanitize_numeric(abs(tx["gain_loss"])),
                        "shares": tx["shares"],
                    }
                )
                flagged_tx_ids.add(tx_id)
                break  # One wash sale per loss transaction

    return wash_sales
