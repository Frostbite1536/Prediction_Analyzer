# prediction_analyzer/providers/polymarket.py
"""
Polymarket provider — largest prediction market by global volume.

Data API (public): https://data-api.polymarket.com
Gamma API (public): https://gamma-api.polymarket.com
CLOB API (auth):    https://clob.polymarket.com

Auth for public Data API: none — just pass wallet address as 'user' query param.
Currency: USDC on Polygon.
"""
import json
import logging
import requests
from typing import List, Optional, Dict, Any

from .base import MarketProvider
from ..trade_loader import Trade, _parse_timestamp

logger = logging.getLogger(__name__)

DATA_API_URL = "https://data-api.polymarket.com"
GAMMA_API_URL = "https://gamma-api.polymarket.com"


class PolymarketProvider(MarketProvider):
    name = "polymarket"
    display_name = "Polymarket"
    api_key_prefix = "0x"  # Wallet addresses start with 0x
    currency = "USDC"

    def fetch_trades(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        """Fetch trades using the public Data API with offset pagination.

        Args:
            api_key: Polymarket wallet address (0x...).
            page_limit: Trades per request (max 500).
        """
        all_trades: List[Trade] = []
        seen_hashes: set = set()
        limit = min(page_limit, 500)
        offset = 0

        logger.info("Downloading Polymarket trade history...")

        while True:
            params: Dict[str, Any] = {
                "user": api_key,
                "limit": limit,
                "offset": offset,
                "type": "TRADE",
            }

            try:
                resp = requests.get(
                    f"{DATA_API_URL}/activity", params=params, timeout=15
                )
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as exc:
                logger.error("Polymarket API error: %s", exc)
                break

            if not data:
                break

            for raw in data:
                tx_hash = raw.get("transactionHash")
                if tx_hash and tx_hash in seen_hashes:
                    continue
                if tx_hash:
                    seen_hashes.add(tx_hash)
                all_trades.append(self.normalize_trade(raw))

            logger.info("Downloaded %d Polymarket trades so far", len(all_trades))

            if len(data) < limit:
                break

            offset += limit

            # Polymarket caps offset at 10000
            if offset >= 10000:
                logger.warning(
                    "Reached Polymarket offset limit (10000). "
                    "Some older trades may not be fetched."
                )
                break

        logger.info("Downloaded %d total Polymarket trades", len(all_trades))
        return all_trades

    def normalize_trade(self, raw: dict, **kwargs) -> Trade:
        """Convert Polymarket Data API activity/trade to Trade object.

        Fields: side (BUY/SELL), conditionId, size, usdcSize, price (0-1),
        timestamp (Unix sec), transactionHash, outcomeIndex, outcome (Yes/No),
        title, slug, eventSlug.
        """
        return Trade(
            market=raw.get("title") or "Unknown",
            market_slug=raw.get("slug") or raw.get("conditionId") or "unknown",
            timestamp=_parse_timestamp(raw.get("timestamp") or 0),
            price=float(raw.get("price") or 0),
            shares=float(raw.get("size") or 0),
            cost=float(raw.get("usdcSize") or 0),
            type=(raw.get("side") or "BUY").title(),  # "BUY" → "Buy"
            side=(raw.get("outcome") or "Yes").upper(),  # "Yes" → "YES"
            pnl=0.0,  # Data API does not provide per-trade PnL
            pnl_is_set=False,
            tx_hash=raw.get("transactionHash"),
            source="polymarket",
            currency="USDC",
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market from Gamma API. market_id can be slug or conditionId."""
        try:
            resp = requests.get(
                f"{GAMMA_API_URL}/markets",
                params={"slug": market_id, "limit": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                markets = resp.json()
                if markets:
                    market = markets[0]
                    # Parse stringified JSON fields
                    for field in ("outcomes", "outcomePrices"):
                        val = market.get(field)
                        if isinstance(val, str):
                            try:
                                market[field] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
                    return market
        except Exception as exc:
            logger.warning("Failed to fetch Polymarket market %s: %s", market_id, exc)
        return None

    def detect_file_format(self, records: List[dict]) -> bool:
        """Polymarket: has conditionId, usdcSize, or eventSlug+outcome."""
        if not records:
            return False
        first = records[0]
        return (
            "conditionId" in first
            or "usdcSize" in first
            or ("eventSlug" in first and "outcome" in first)
        )
