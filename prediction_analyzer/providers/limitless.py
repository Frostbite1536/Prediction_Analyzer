# prediction_analyzer/providers/limitless.py
"""
Limitless Exchange provider — uses the official limitless-sdk.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any

from .base import MarketProvider
from ..trade_loader import Trade
from ..utils.time_utils import parse_timestamp as _parse_timestamp

logger = logging.getLogger(__name__)

# USDC uses 6 decimal places; on-chain amounts are in micro-units.
USDC_DECIMALS = 1_000_000


def _run_async(coro):
    """Run an async coroutine from synchronous code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside an async context (e.g. FastAPI) — create a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class LimitlessProvider(MarketProvider):
    name = "limitless"
    display_name = "Limitless Exchange"
    api_key_prefix = "lmts_"
    currency = "USDC"

    def fetch_trades(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        """Fetch trade history from Limitless Exchange using the official SDK."""
        return _run_async(self._fetch_trades_async(api_key, page_limit))

    async def _fetch_trades_async(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        """Async implementation of trade fetching via limitless-sdk."""
        from limitless_sdk import Client

        client = Client(api_key=api_key)
        all_trades: List[Trade] = []
        page = 1

        logger.info("Downloading Limitless trade history via SDK...")

        try:
            while True:
                response = await client.portfolio.get_user_history(
                    page=page, limit=page_limit
                )

                raw_trades = response.get("data", [])
                if not raw_trades:
                    break

                for raw in raw_trades:
                    all_trades.append(self.normalize_trade(raw))

                logger.info("Downloaded page %d (%d trades so far)", page, len(all_trades))

                total_count = response.get("totalCount", 0)
                if len(all_trades) >= total_count:
                    break
                page += 1
        except Exception as exc:
            logger.error("Limitless SDK error on page %d: %s", page, exc)
            # Return whatever we collected so far rather than losing everything
            if not all_trades:
                raise
        finally:
            await client.http.close()

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
            market_title = raw.get("market") if isinstance(raw.get("market"), str) else "Unknown"
            market_slug = raw.get("market_slug") or raw.get("marketSlug") or "unknown"

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

        # SDK history entries store trade details in a nested "details" dict
        details = raw.get("details") or {}
        if isinstance(details, dict):
            if not strategy:
                strategy = details.get("strategy") or ""
            if not action:
                action = details.get("action") or details.get("side") or ""
            # Pull collateral/outcome amounts from details if not at top level
            if "collateralAmount" not in raw and "collateralAmount" in details:
                cost = float(details.get("collateralAmount") or 0) / USDC_DECIMALS
                shares = float(details.get("outcomeTokenAmount") or 0) / USDC_DECIMALS
            if "pnl" not in raw and "pnl" in details:
                pnl = float(details.get("pnl") or 0) / USDC_DECIMALS
                has_pnl = details["pnl"] is not None

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

        side = raw.get("side") or details.get("side")
        if not side:
            outcome_index = raw.get("outcomeIndex") or details.get("outcomeIndex")
            if outcome_index is not None:
                side = "YES" if int(outcome_index) == 0 else "NO"
            else:
                side = "YES"

        # Derive price from cost/shares when not explicitly provided
        raw_price = float(raw.get("price") or details.get("price") or 0)
        if raw_price == 0 and shares > 0 and cost > 0:
            raw_price = cost / shares

        # Timestamp: SDK uses "createdAt", raw API uses "timestamp"/"blockTimestamp"
        ts_raw = (
            raw.get("createdAt")
            or raw.get("timestamp")
            or raw.get("blockTimestamp")
            or details.get("timestamp")
            or 0
        )

        return Trade(
            market=market_title,
            market_slug=market_slug,
            timestamp=_parse_timestamp(ts_raw),
            price=raw_price,
            shares=shares,
            cost=cost,
            type=trade_type,
            side=side,
            pnl=pnl,
            pnl_is_set=has_pnl,
            tx_hash=raw.get("tx_hash") or raw.get("transactionHash") or details.get("txHash"),
            source="limitless",
            currency="USDC",
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market details by slug using the SDK."""
        try:
            return _run_async(self._fetch_market_async(market_id))
        except Exception as exc:
            logger.warning("Failed to fetch Limitless market %s: %s", market_id, exc)
            return None

    async def _fetch_market_async(self, slug: str) -> Dict[str, Any]:
        """Async market fetch via SDK."""
        from limitless_sdk import Client

        client = Client()  # Public endpoint, no auth needed
        try:
            market = await client.markets.get_market(slug)
            return market.model_dump()
        finally:
            await client.http.close()

    def detect_file_format(self, records: List[dict]) -> bool:
        """Detect Limitless format by field signatures."""
        if not records:
            return False
        first = records[0]
        return (
            "collateralAmount" in first
            or "outcomeTokenAmount" in first
            or (isinstance(first.get("market"), dict) and "slug" in first["market"])
        )
