# prediction_analyzer/providers/manifold.py
"""
Manifold Markets provider.

API docs: https://docs.manifold.markets/api
Base URL: https://api.manifold.markets
Auth: API key via "Authorization: Key <key>" header.
Currency: MANA (play money).
"""
import logging
import requests
from typing import List, Optional, Dict, Any

from .base import MarketProvider
from ..trade_loader import Trade, _parse_timestamp

logger = logging.getLogger(__name__)

BASE_URL = "https://api.manifold.markets"


class ManifoldProvider(MarketProvider):
    name = "manifold"
    display_name = "Manifold Markets"
    api_key_prefix = "manifold_"
    currency = "MANA"

    def _get_user_id(self, api_key: str) -> str:
        """Fetch the user's ID from /v0/me."""
        raw_key = api_key.removeprefix("manifold_")
        headers = {"Authorization": f"Key {raw_key}"}
        resp = requests.get(f"{BASE_URL}/v0/me", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()["id"]

    def _fetch_market_metadata(self, contract_ids: List[str]) -> Dict[str, dict]:
        """Batch-fetch market metadata for contractIds (bets lack question/slug)."""
        metadata: Dict[str, dict] = {}
        for cid in contract_ids:
            if cid in metadata:
                continue
            try:
                resp = requests.get(f"{BASE_URL}/v0/market/{cid}", timeout=10)
                if resp.status_code == 200:
                    m = resp.json()
                    metadata[cid] = {
                        "question": m.get("question", "Unknown"),
                        "slug": m.get("slug", cid),
                        "outcomeType": m.get("outcomeType", "BINARY"),
                        "probability": m.get("probability", 0),
                        "isResolved": m.get("isResolved", False),
                        "resolution": m.get("resolution"),
                    }
                else:
                    metadata[cid] = {"question": "Unknown", "slug": cid}
            except Exception as exc:
                logger.warning("Failed to fetch Manifold market metadata %s: %s", cid, exc)
                metadata[cid] = {"question": "Unknown", "slug": cid}
        return metadata

    def fetch_trades(self, api_key: str, page_limit: int = 1000) -> List[Trade]:
        """Fetch user's bet history from Manifold Markets."""
        user_id = self._get_user_id(api_key)
        all_bets: List[dict] = []
        cursor = None
        limit = min(page_limit, 10000)

        # Step 1: Fetch all bets (paginated by 'before' cursor)
        while True:
            params: Dict[str, Any] = {
                "userId": user_id,
                "limit": limit,
                "filterRedemptions": "true",
            }
            if cursor:
                params["before"] = cursor

            try:
                resp = requests.get(
                    f"{BASE_URL}/v0/bets", params=params, timeout=15
                )
                resp.raise_for_status()
                bets = resp.json()
            except requests.RequestException as exc:
                logger.error("Manifold API error: %s", exc)
                break

            if not bets:
                break

            all_bets.extend(bets)
            logger.info("Downloaded %d Manifold bets so far", len(all_bets))

            if len(bets) < limit:
                break
            cursor = bets[-1]["id"]

        # Step 2: Fetch market metadata for unique contractIds
        contract_ids = list(
            {b.get("contractId", "") for b in all_bets if b.get("contractId")}
        )
        logger.info("Fetching metadata for %d Manifold markets...", len(contract_ids))
        market_meta = self._fetch_market_metadata(contract_ids)

        # Step 3: Normalize
        trades = []
        for raw in all_bets:
            meta = market_meta.get(raw.get("contractId", ""), {})
            trades.append(self.normalize_trade(raw, market_meta=meta))

        return trades

    def normalize_trade(self, raw: dict, **kwargs) -> Trade:
        """Convert Manifold bet to Trade object.

        Bet fields: id, contractId, createdTime (ms), amount (neg=sell),
        shares (neg=sell), outcome (YES/NO), probBefore, probAfter, isRedemption.
        Market metadata must be passed separately as kwargs['market_meta'].
        """
        market_meta = kwargs.get("market_meta", {})
        amount = float(raw.get("amount", 0))
        shares = abs(float(raw.get("shares", 0)))
        # Derive actual fill price from amount/shares (not probAfter which is
        # the post-trade market probability, not the price paid per share)
        if shares > 0:
            fill_price = abs(amount) / shares
        else:
            fill_price = float(raw.get("probAfter", 0))

        return Trade(
            market=market_meta.get("question", "Unknown"),
            market_slug=market_meta.get("slug", raw.get("contractId", "unknown")),
            timestamp=_parse_timestamp(raw.get("createdTime", 0)),
            price=fill_price,
            shares=shares,
            cost=abs(amount),
            type="Buy" if amount >= 0 else "Sell",
            side=(raw.get("outcome") or "YES").upper(),
            pnl=0.0,  # Must compute client-side
            pnl_is_set=False,
            tx_hash=raw.get("id"),
            source="manifold",
            currency="MANA",
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market by ID or slug."""
        for endpoint in [f"/v0/market/{market_id}", f"/v0/slug/{market_id}"]:
            try:
                resp = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                if resp.status_code == 200:
                    return resp.json()
            except Exception as exc:
                logger.warning("Failed to fetch Manifold market %s via %s: %s", market_id, endpoint, exc)
        return None

    def detect_file_format(self, records: List[dict]) -> bool:
        """Manifold: has contractId, or probBefore/probAfter, or outcome+shares without ticker/conditionId."""
        if not records:
            return False
        first = records[0]
        return (
            "contractId" in first
            or ("probBefore" in first and "probAfter" in first)
            or (
                "outcome" in first
                and "shares" in first
                and "ticker" not in first
                and "conditionId" not in first
            )
        )
