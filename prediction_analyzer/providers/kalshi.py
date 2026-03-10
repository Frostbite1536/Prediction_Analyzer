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
from ..trade_loader import Trade, _parse_timestamp

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
            pem_path = os.environ.get(
                "KALSHI_PRIVATE_KEY_PATH", "kalshi_private_key.pem"
            )

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

        timestamp_ms = str(
            int(datetime.datetime.now().timestamp() * 1000)
        )
        path_without_query = path.split("?")[0]
        message = (timestamp_ms + method.upper() + path_without_query).encode("utf-8")

        signature = self._private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
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
                resp = requests.get(
                    f"{self._base_url}{path}", headers=headers, timeout=15
                )
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
                resp = requests.get(
                    f"{self._base_url}{path}", headers=headers, timeout=15
                )
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException:
                break

            for pos in data.get("market_positions", []):
                ticker = pos.get("ticker", "")
                pnl_map[ticker] = float(pos.get("realized_pnl_dollars", "0"))

            cursor = data.get("cursor", "")
            if not cursor:
                break

        return pnl_map

    @staticmethod
    def _apply_position_pnl(trades: List[Trade], pnl_map: Dict[str, float]):
        """Distribute realized PnL from positions across sell trades."""
        from collections import defaultdict

        sell_counts: Dict[str, int] = defaultdict(int)
        for t in trades:
            if t.type.lower() == "sell" and t.market_slug in pnl_map:
                sell_counts[t.market_slug] += 1

        for t in trades:
            if t.type.lower() == "sell" and t.market_slug in pnl_map:
                count = sell_counts[t.market_slug]
                if count > 0:
                    t.pnl = pnl_map[t.market_slug] / count

    def normalize_trade(self, raw: dict, **kwargs) -> Trade:
        """Convert Kalshi fill to Trade object.

        Uses non-deprecated _fixed/_fp fields:
          yes_price_fixed, no_price_fixed: dollar strings (e.g. "0.5600")
          count_fp: fixed-point count (e.g. "10.00")
          fee_cost: fee in dollars
        """
        side_str = (raw.get("side") or "yes").upper()

        if side_str == "YES":
            price_str = raw.get("yes_price_fixed") or str(
                raw.get("yes_price", 0)
            )
        else:
            price_str = raw.get("no_price_fixed") or str(
                raw.get("no_price", 0)
            )

        # Use _fixed fields; fall back to integer cents / 100
        try:
            price = float(price_str)
        except (ValueError, TypeError):
            price = 0.0

        # If price looks like cents (> 1), convert to dollars
        if price > 1:
            price = price / 100.0

        count_str = raw.get("count_fp", str(raw.get("count", 0)))
        try:
            count = float(count_str)
        except (ValueError, TypeError):
            count = 0.0

        fee_str = raw.get("fee_cost", "0")
        try:
            fee = float(fee_str)
        except (ValueError, TypeError):
            fee = 0.0

        return Trade(
            market=raw.get("ticker") or raw.get("market_ticker") or "Unknown",
            market_slug=raw.get("ticker") or raw.get("market_ticker") or "unknown",
            timestamp=_parse_timestamp(
                raw.get("created_time") or raw.get("ts") or 0
            ),
            price=price,
            shares=count,
            cost=(price * count) + fee,
            type=(raw.get("action") or "buy").title(),
            side=side_str,
            pnl=0.0,  # Filled in later from positions endpoint
            tx_hash=raw.get("fill_id") or raw.get("order_id"),
            source="kalshi",
            currency="USD",
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market by ticker (public, no auth)."""
        try:
            resp = requests.get(
                f"{PROD_BASE_URL}/trade-api/v2/markets/{market_id}", timeout=10
            )
            if resp.status_code == 200:
                return resp.json().get("market")
        except Exception:
            pass
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
