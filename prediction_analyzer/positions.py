# prediction_analyzer/positions.py
"""
Portfolio position analysis: open positions, unrealized PnL, concentration risk.
"""
import logging
from typing import List, Dict, Optional
from .trade_loader import Trade, sanitize_numeric
from .utils.data import fetch_market_details

logger = logging.getLogger(__name__)


def calculate_open_positions(
    trades: List[Trade],
    market_slug: Optional[str] = None,
) -> List[Dict]:
    """
    Calculate current open positions with unrealized PnL.

    Groups trades by market, computes net share position, and optionally
    fetches current prices for unrealized PnL calculation.

    Args:
        trades: List of Trade objects
        market_slug: Optional market slug to filter to a single market

    Returns:
        List of position dicts with keys:
            market, market_slug, net_shares, side, avg_entry_price,
            current_price, unrealized_pnl, cost_basis
    """
    # Group trades by market slug
    by_market: Dict[str, List[Trade]] = {}
    for t in trades:
        if market_slug and t.market_slug != market_slug:
            continue
        by_market.setdefault(t.market_slug, []).append(t)

    positions = []
    for slug, market_trades in sorted(by_market.items()):
        market_name = market_trades[0].market

        # Calculate net shares and cost basis
        net_shares = 0.0
        total_cost = 0.0

        for t in sorted(market_trades, key=lambda x: x.timestamp):
            if t.type in ("Buy", "Market Buy", "Limit Buy"):
                net_shares += t.shares
                total_cost += t.cost
            elif t.type in ("Sell", "Market Sell", "Limit Sell"):
                net_shares -= t.shares
                total_cost -= t.cost

        # Skip markets with no open position
        if abs(net_shares) < 1e-10:
            continue

        side = "YES" if net_shares > 0 else "NO"
        abs_shares = abs(net_shares)
        avg_entry = (abs(total_cost) / abs_shares) if abs_shares > 0 else 0.0

        # Try to get current market price
        current_price = None
        try:
            details = fetch_market_details(slug)
            if details and "lastPrice" in details:
                current_price = float(details["lastPrice"])
            elif details and "price" in details:
                current_price = float(details["price"])
        except Exception:
            logger.debug("Could not fetch price for %s", slug)

        unrealized_pnl = None
        if current_price is not None:
            unrealized_pnl = abs_shares * (current_price - avg_entry)

        positions.append({
            "market": market_name,
            "market_slug": slug,
            "net_shares": sanitize_numeric(abs_shares),
            "side": side,
            "avg_entry_price": sanitize_numeric(avg_entry),
            "current_price": sanitize_numeric(current_price) if current_price is not None else None,
            "unrealized_pnl": sanitize_numeric(unrealized_pnl) if unrealized_pnl is not None else None,
            "cost_basis": sanitize_numeric(abs(total_cost)),
        })

    return positions


def calculate_concentration_risk(trades: List[Trade]) -> Dict:
    """
    Analyze portfolio concentration and diversification across markets.

    Args:
        trades: List of Trade objects

    Returns:
        Dict with total_markets, total_exposure, per-market breakdown,
        herfindahl_index, and top_3_concentration_pct
    """
    # Calculate exposure (total cost) per market
    exposure_by_market: Dict[str, Dict] = {}

    for t in trades:
        slug = t.market_slug
        if slug not in exposure_by_market:
            exposure_by_market[slug] = {
                "market": t.market,
                "slug": slug,
                "exposure": 0.0,
                "trade_count": 0,
            }
        exposure_by_market[slug]["exposure"] += abs(t.cost)
        exposure_by_market[slug]["trade_count"] += 1

    total_exposure = sum(m["exposure"] for m in exposure_by_market.values())

    # Calculate percentage of total for each market
    markets = []
    for slug, data in exposure_by_market.items():
        pct = (data["exposure"] / total_exposure * 100) if total_exposure > 0 else 0.0
        markets.append({
            "market": data["market"],
            "slug": data["slug"],
            "exposure": sanitize_numeric(data["exposure"]),
            "pct_of_total": sanitize_numeric(pct),
            "trade_count": data["trade_count"],
        })

    # Sort by exposure descending
    markets.sort(key=lambda x: x["exposure"], reverse=True)

    # Herfindahl-Hirschman Index (HHI)
    # Sum of squared market shares (0-10000 scale)
    hhi = sum((m["pct_of_total"] / 100) ** 2 for m in markets) * 10000 if markets else 0.0

    # Top 3 concentration
    top_3_pct = sum(m["pct_of_total"] for m in markets[:3])

    return {
        "total_markets": len(markets),
        "total_exposure": sanitize_numeric(total_exposure),
        "markets": markets,
        "herfindahl_index": sanitize_numeric(hhi),
        "top_3_concentration_pct": sanitize_numeric(top_3_pct),
    }
