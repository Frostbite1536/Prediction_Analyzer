# prediction_analyzer/providers/kalshi.py
"""
Kalshi provider — CFTC-regulated US prediction exchange.

API docs: https://docs.kalshi.com
Base URL: https://api.elections.kalshi.com (serves ALL markets, not just elections)
Auth: RSA-PSS request signing (no login/session endpoint).
Currency: USD.

IMPORTANT: Integer cent fields (price, yes_price, etc.) are deprecated and will be
removed March 12, 2026. This provider uses the _fixed/_fp/_dollars string fields.
"""

import base64
import datetime
import logging
import os
import requests
from typing import List, Optional, Dict, Any

from .base import MarketProvider
from ..trade_loader import Trade, sanitize_numeric
from ..utils.time_utils import parse_timestamp as _parse_timestamp

logger = logging.getLogger(__name__)

PROD_BASE_URL = "https://api.elections.kalshi.com"
DEMO_BASE_URL = "https://demo-api.kalshi.co"


class KalshiProvider(MarketProvider):
    name = "kalshi"
    display_name = "Kalshi"
    api_key_prefix = "kalshi_"
    currency = "USD"

    def __init__(self):
        self._private_key = None
        self._api_key_id = None
        self._base_url = PROD_BASE_URL

    def _load_credentials(self, api_key: str):
        """Parse Kalshi credentials.

        Accepts formats:
          - "kalshi_<KEY_ID>:<PEM_FILE_PATH>"
          - "kalshi_<KEY_ID>" (uses KALSHI_PRIVATE_KEY_PATH env var)
        """
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        key_str = api_key.removeprefix("kalshi_")
        if ":" in key_str:
            self._api_key_id, pem_path = key_str.split(":", 1)
        else:
            self._api_key_id = key_str
            pem_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH", "kalshi_private_key.pem")

        with open(pem_path, "rb") as f:
            self._private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

        # Allow demo mode via env var
        if os.environ.get("KALSHI_DEMO", "").lower() in ("1", "true", "yes"):
            self._base_url = DEMO_BASE_URL

    def _sign_request(self, method: str, path: str) -> dict:
        """Build auth headers with RSA-PSS signature."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        timestamp_ms = str(int(datetime.datetime.now().timestamp() * 1000))
        path_without_query = path.split("?")[0]
        message = (timestamp_ms + method.upper() + path_without_query).encode("utf-8")

        signature = self._private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                # DIGEST_LENGTH (not MAX_LENGTH) per Kalshi's official docs.
                # Matches their Node.js RSA_PSS_SALTLEN_DIGEST constant.
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )

        return {
            "KALSHI-ACCESS-KEY": self._api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
        }

    def fetch_trades(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        """Fetch user's fill history from Kalshi."""
        self._load_credentials(api_key)
        try:
            return self._fetch_trades_inner(page_limit, api_key)
        finally:
            # Clear private key from memory after use
            self._private_key = None
            self._api_key_id = None

    def _fetch_trades_inner(self, page_limit: int, api_key: str) -> List[Trade]:
        all_trades: List[Trade] = []
        cursor: Optional[str] = None
        limit = min(page_limit, 1000)

        logger.info("Downloading Kalshi fill history...")

        while True:
            path = f"/trade-api/v2/portfolio/fills?limit={limit}"
            if cursor:
                path += f"&cursor={cursor}"

            headers = self._sign_request("GET", path)
            try:
                resp = requests.get(f"{self._base_url}{path}", headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as exc:
                logger.error("Kalshi API error: %s", exc)
                break

            fills = data.get("fills", [])
            if not fills:
                break

            for raw in fills:
                all_trades.append(self.normalize_trade(raw))

            logger.info("Downloaded %d Kalshi fills so far", len(all_trades))

            cursor = data.get("cursor", "")
            if not cursor:
                break

        # Enrich with position-level PnL if available
        try:
            pnl_map = self._fetch_position_pnl(api_key)
            if pnl_map:
                self._apply_position_pnl(all_trades, pnl_map)
        except Exception as exc:
            logger.warning("Could not fetch Kalshi position PnL: %s", exc)

        # Enrich market field with human-readable titles (tickers are cryptic)
        try:
            unique_tickers = list({t.market_slug for t in all_trades})
            if unique_tickers:
                logger.info("Fetching titles for %d Kalshi markets...", len(unique_tickers))
                title_map = self._fetch_market_titles(unique_tickers)
                for t in all_trades:
                    t.market = title_map.get(t.market_slug, t.market_slug)
        except Exception as exc:
            logger.warning("Could not fetch Kalshi market titles: %s", exc)

        logger.info("Downloaded %d total Kalshi fills", len(all_trades))
        return all_trades

    def _fetch_position_pnl(self, api_key: str) -> Dict[str, float]:
        """Fetch realized PnL per ticker from positions endpoint."""
        pnl_map: Dict[str, float] = {}
        cursor: Optional[str] = None

        while True:
            path = "/trade-api/v2/portfolio/positions?limit=1000"
            if cursor:
                path += f"&cursor={cursor}"

            headers = self._sign_request("GET", path)
            try:
                resp = requests.get(f"{self._base_url}{path}", headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException:
                break

            for pos in data.get("market_positions", []):
                ticker = pos.get("ticker", "")
                pnl_map[ticker] = sanitize_numeric(float(pos.get("realized_pnl_dollars", "0")))

            cursor = data.get("cursor", "")
            if not cursor:
                break

        return pnl_map

    _SELL_TYPES = {"sell", "market sell", "limit sell"}

    @staticmethod
    def _apply_position_pnl(trades: List[Trade], pnl_map: Dict[str, float]):
        """Distribute realized PnL from positions across sell trades,
        weighted proportionally by share count (not evenly)."""
        from collections import defaultdict

        sell_shares: Dict[str, float] = defaultdict(float)
        for t in trades:
            if t.type.lower() in KalshiProvider._SELL_TYPES and t.market_slug in pnl_map:
                sell_shares[t.market_slug] += t.shares

        for t in trades:
            if t.type.lower() in KalshiProvider._SELL_TYPES and t.market_slug in pnl_map:
                total = sell_shares[t.market_slug]
                if total > 0:
                    t.pnl = pnl_map[t.market_slug] * (t.shares / total)
                    t.pnl_is_set = True

    def _fetch_market_titles(self, tickers: List[str]) -> Dict[str, str]:
        """Batch-fetch human-readable titles for market tickers (public, no auth)."""
        titles: Dict[str, str] = {}
        for ticker in tickers:
            if ticker in titles:
                continue
            try:
                resp = requests.get(
                    f"{self._base_url}/trade-api/v2/markets/{ticker}",
                    timeout=10,
                )
                if resp.status_code == 200:
                    market = resp.json().get("market", {})
                    titles[ticker] = market.get("title") or ticker
                else:
                    titles[ticker] = ticker
            except Exception as exc:
                logger.warning("Failed to fetch Kalshi title for %s: %s", ticker, exc)
                titles[ticker] = ticker
        return titles

    def normalize_trade(self, raw: dict, **kwargs) -> Trade:
        """Convert Kalshi fill to Trade object.

        Uses non-deprecated _fixed/_fp fields:
          yes_price_fixed, no_price_fixed: dollar strings (e.g. "0.5600")
          count_fp: fixed-point count (e.g. "10.00")
          fee_cost: fee in dollars
        """
        side_str = (raw.get("side") or "yes").upper()

        # Determine price using field presence (not magnitude heuristic).
        # _fixed fields are dollar strings (e.g. "0.5600") — use directly.
        # Legacy integer-cent fields (e.g. 56) — always divide by 100.
        if side_str == "YES":
            fixed = raw.get("yes_price_fixed")
            legacy = raw.get("yes_price")
        else:
            fixed = raw.get("no_price_fixed")
            legacy = raw.get("no_price")

        fill_id = raw.get("fill_id") or raw.get("order_id") or "?"

        if fixed is not None and str(fixed).strip():
            try:
                price = float(fixed)
            except (ValueError, TypeError):
                logger.warning(
                    "Kalshi fill %s: bad %s_price_fixed=%r, falling back to legacy",
                    fill_id,
                    side_str.lower(),
                    fixed,
                )
                fixed = None

        if fixed is None or not str(fixed).strip():
            try:
                price = float(legacy or 0) / 100.0
            except (ValueError, TypeError):
                logger.warning(
                    "Kalshi fill %s: bad legacy price=%r, defaulting to 0", fill_id, legacy
                )
                price = 0.0

        count_str = raw.get("count_fp") or str(raw.get("count") or 0)
        try:
            count = float(count_str)
        except (ValueError, TypeError):
            logger.warning("Kalshi fill %s: bad count=%r, defaulting to 0", fill_id, count_str)
            count = 0.0

        fee_str = raw.get("fee_cost", "0")
        try:
            fee = float(fee_str)
        except (ValueError, TypeError):
            logger.warning("Kalshi fill %s: bad fee_cost=%r, defaulting to 0", fill_id, fee_str)
            fee = 0.0

        action = (raw.get("action") or "buy").title()
        is_sell = action.lower() in ("sell", "market sell", "limit sell")
        # For buys, cost = price*count + fee (total outlay)
        # For sells, cost = price*count - fee (net proceeds)
        cost = (price * count) - fee if is_sell else (price * count) + fee

        return Trade(
            market=raw.get("ticker") or raw.get("market_ticker") or "Unknown",
            market_slug=raw.get("ticker") or raw.get("market_ticker") or "unknown",
            timestamp=_parse_timestamp(raw.get("created_time") or raw.get("ts") or 0),
            price=price,
            shares=count,
            cost=cost,
            type=action,
            side=side_str,
            pnl=0.0,  # Filled in later from positions endpoint
            pnl_is_set=False,
            tx_hash=raw.get("fill_id") or raw.get("order_id"),
            source="kalshi",
            currency="USD",
            fee=fee,
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market by ticker (public, no auth)."""
        try:
            resp = requests.get(f"{PROD_BASE_URL}/trade-api/v2/markets/{market_id}", timeout=10)
            if resp.status_code == 200:
                return resp.json().get("market")
        except Exception as exc:
            logger.warning("Failed to fetch Kalshi market %s: %s", market_id, exc)
        return None

    def detect_file_format(self, records: List[dict]) -> bool:
        """Kalshi format: ticker starting with KX, or yes_price/taker_side fields."""
        if not records:
            return False
        first = records[0]
        ticker = first.get("ticker") or first.get("market_ticker") or ""
        return (
            bool(ticker and "-" in ticker and ticker.startswith("KX"))
            or "yes_price" in first
            or "yes_price_fixed" in first
            or "taker_side" in first
        )
