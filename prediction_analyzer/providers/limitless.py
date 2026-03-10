# prediction_analyzer/providers/limitless.py
"""
Limitless Exchange provider — refactored from utils/data.py.
"""
import logging
import requests
from typing import List, Optional, Dict, Any

from .base import MarketProvider
from ..trade_loader import Trade, _parse_timestamp

logger = logging.getLogger(__name__)

BASE_URL = "https://api.limitless.exchange"

# USDC uses 6 decimal places; on-chain amounts are in micro-units.
USDC_DECIMALS = 1_000_000


class LimitlessProvider(MarketProvider):
    name = "limitless"
    display_name = "Limitless Exchange"
    api_key_prefix = "lmts_"
    currency = "USDC"

    def fetch_trades(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        """Fetch trade history from Limitless Exchange API."""
        all_trades = []
        page = 1
        headers = {"X-API-Key": api_key}

        logger.info("Downloading Limitless trade history...")

        while True:
            params = {"page": page, "limit": page_limit}
            try:
                resp = requests.get(
                    f"{BASE_URL}/portfolio/history",
                    params=params,
                    headers=headers,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as exc:
                logger.error("Limitless API error page %d: %s", page, exc)
                break

            raw_trades = data.get("data", [])
            if not raw_trades:
                break

            for raw in raw_trades:
                all_trades.append(self.normalize_trade(raw))

            logger.info("Downloaded page %d (%d trades so far)", page, len(all_trades))

            total_count = data.get("totalCount", 0)
            if len(all_trades) >= total_count:
                break
            page += 1

        logger.info("Downloaded %d total Limitless trades", len(all_trades))
        return all_trades

    def normalize_trade(self, raw: dict, **kwargs) -> Trade:
        """Convert Limitless API/file record to Trade object."""
        # Handle nested market object (API format)
        market_data = raw.get("market")
        if isinstance(market_data, dict):
            market_title = market_data.get("title") or "Unknown"
            market_slug = market_data.get("slug") or "unknown"
        else:
            market_title = (
                raw.get("market") if isinstance(raw.get("market"), str) else "Unknown"
            )
            market_slug = raw.get("market_slug") or "unknown"

        if not market_title:
            market_title = "Unknown"
        if not market_slug:
            market_slug = "unknown"

        # Convert from micro-units (USDC 6 decimals) if API format
        has_pnl = "pnl" in raw and raw["pnl"] is not None
        if "collateralAmount" in raw:
            cost = float(raw.get("collateralAmount") or 0) / USDC_DECIMALS
            pnl = float(raw.get("pnl") or 0) / USDC_DECIMALS
            shares = float(raw.get("outcomeTokenAmount") or 0) / USDC_DECIMALS
        else:
            cost = float(raw.get("cost") or 0)
            pnl = float(raw.get("pnl") or 0)
            shares = float(raw.get("shares") or 0)

        # Determine trade direction (Buy/Sell).
        # The Limitless API may return a category in "type" (e.g. "trade",
        # "split", "merge", "conversion") rather than a direction.  Prefer
        # "strategy" for direction, fall back to "action"/"side" fields,
        # then to "type" only if it looks like a direction keyword.
        _CATEGORY_TYPES = {"trade", "split", "merge", "conversion"}
        raw_type = raw.get("type") or ""
        strategy = raw.get("strategy") or ""
        action = raw.get("action") or ""

        if strategy:
            trade_type = strategy
        elif raw_type and raw_type.lower() not in _CATEGORY_TYPES:
            trade_type = raw_type
        elif action:
            trade_type = action
        else:
            trade_type = "Buy"

        # Normalize underscore-separated types (e.g. "market_buy" -> "Market Buy")
        if "_" in trade_type:
            trade_type = trade_type.replace("_", " ").title()
        elif trade_type.islower():
            trade_type = trade_type.title()

        side = raw.get("side")
        if not side:
            outcome_index = raw.get("outcomeIndex")
            if outcome_index is not None:
                side = "YES" if outcome_index == 0 else "NO"
            else:
                side = "YES"

        # Derive price from cost/shares when not explicitly provided
        raw_price = float(raw.get("price") or 0)
        if raw_price == 0 and shares > 0 and cost > 0:
            raw_price = cost / shares

        return Trade(
            market=market_title,
            market_slug=market_slug,
            timestamp=_parse_timestamp(
                raw.get("timestamp") or raw.get("blockTimestamp") or 0
            ),
            price=raw_price,
            shares=shares,
            cost=cost,
            type=trade_type,
            side=side,
            pnl=pnl,
            pnl_is_set=has_pnl,
            tx_hash=raw.get("tx_hash") or raw.get("transactionHash"),
            source="limitless",
            currency="USDC",
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market details by slug (public, no auth)."""
        try:
            resp = requests.get(f"{BASE_URL}/markets/{market_id}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            logger.warning("Failed to fetch Limitless market %s: %s", market_id, exc)
        return None

    def detect_file_format(self, records: List[dict]) -> bool:
        """Limitless format: has collateralAmount, outcomeTokenAmount, or nested market dict with slug."""
        if not records:
            return False
        first = records[0]
        return (
            "collateralAmount" in first
            or "outcomeTokenAmount" in first
            or (
                isinstance(first.get("market"), dict)
                and "slug" in first["market"]
            )
        )
