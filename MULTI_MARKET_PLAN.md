# Multi-Market Support Plan: Polymarket, Kalshi, Manifold Markets

## Overview

Add support for the three largest prediction markets alongside the existing Limitless Exchange integration:

1. **Polymarket** — Largest by global mindshare (~$10B+ in 2025). Crypto-based, binary outcomes on CLOB. USDC on Polygon.
2. **Kalshi** — Largest US-regulated exchange (~$23.8B volume in 2025, CFTC-regulated). USD-settled event contracts.
3. **Manifold Markets** — Largest play-money market. Fully open-source, most developer-friendly API.

Together Polymarket and Kalshi control ~97.5% of prediction market volume.

---

## Current Architecture (Limitless Exchange Only)

### Files with Limitless-Specific Code (Must Change)

| File | Lines | What's Hardcoded |
|------|-------|-----------------|
| `prediction_analyzer/config.py` | 7-8 | `API_BASE_URL = "https://api.limitless.exchange"`, `DEFAULT_TRADE_FILE = "limitless_trades.json"` |
| `prediction_analyzer/utils/auth.py` | 3-8, 18, 34 | Docstrings say "Limitless Exchange API", env var `LIMITLESS_API_KEY`, key prefix `lmts_` |
| `prediction_analyzer/utils/data.py` | 3, 16, 19, 36, 47-56 | Docstrings say "Limitless Exchange API", endpoint `/portfolio/history`, response format `data[]` + `totalCount` |
| `prediction_analyzer/trade_loader.py` | 205-216, 228-232 | `collateralAmount` detection for USDC micro-units (÷1M), `outcomeIndex` field parsing |
| `prediction_mcp/tools/data_tools.py` | 51-54, 60, 188-189 | Tool description says "Limitless Exchange", key prefix `lmts_` |
| `prediction_mcp/server.py` | 52 | Instructions mention "Limitless Exchange API" |
| `prediction_analyzer/__main__.py` | 40, 52, 88, 113 | Help text says "Limitless API key (lmts_...)", env var `LIMITLESS_API_KEY` |
| `gui.py` | 444+ | Dialog says "Limitless API key (lmts_...)" |

### Files That Need New Fields (source/currency)

| File | What to Add |
|------|------------|
| `prediction_analyzer/trade_loader.py` (Trade dataclass, lines 37-48) | `source: str = "limitless"`, `currency: str = "USD"` fields |
| `prediction_analyzer/api/schemas/trade.py` (TradeBase, lines 10-21) | `source: Optional[str] = "limitless"`, `currency: Optional[str] = "USD"` |
| `prediction_analyzer/api/models/trade.py` (Trade ORM, lines 32-66) | `source = Column(String(50), default='limitless')`, `currency = Column(String(10), default='USD')` |
| `prediction_analyzer/trade_filter.py` (lines 42-44, 79-90) | Add `filter_trades_by_source()` function, update `get_unique_markets()` to include source |
| `prediction_analyzer/api/routers/trades.py` (lines 27-55) | Add `source` query parameter to GET `/trades` |
| `prediction_mcp/state.py` (lines 14-42) | Change `source: Optional[str]` to `sources: List[str]` |

### Files That Need NO Changes

| File | Why |
|------|-----|
| `prediction_analyzer/pnl.py` | Uses generic Trade fields only |
| `prediction_analyzer/metrics.py` | Uses generic Trade fields only |
| `prediction_analyzer/filters.py` | Uses generic Trade fields only |

---

## Phase 1: Provider Abstraction Layer

### 1.1 New file: `prediction_analyzer/providers/__init__.py`

```python
from .base import MarketProvider, ProviderRegistry
from .limitless import LimitlessProvider
from .polymarket import PolymarketProvider
from .kalshi import KalshiProvider
from .manifold import ManifoldProvider

# Auto-register all providers
ProviderRegistry.register(LimitlessProvider())
ProviderRegistry.register(PolymarketProvider())
ProviderRegistry.register(KalshiProvider())
ProviderRegistry.register(ManifoldProvider())
```

### 1.2 New file: `prediction_analyzer/providers/base.py`

```python
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..trade_loader import Trade

logger = logging.getLogger(__name__)


class MarketProvider(ABC):
    """Base class for prediction market data providers."""

    name: str                    # e.g. "polymarket"
    display_name: str            # e.g. "Polymarket"
    api_key_prefix: str          # e.g. "poly_", "kalshi_", "lmts_"
    currency: str = "USD"        # Default currency for this provider

    @abstractmethod
    def fetch_trades(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        """Fetch user's trade history from this market.

        Args:
            api_key: Provider-specific API key or credential string.
            page_limit: Max trades per page for pagination.

        Returns:
            List of Trade objects with source and currency set.
        """
        ...

    @abstractmethod
    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch details for a specific market.

        Args:
            market_id: Provider-specific market identifier
                - Limitless: market slug (e.g. "btc-100k-2024")
                - Polymarket: conditionId or slug
                - Kalshi: ticker (e.g. "KXBTC-25MAR14-T85000")
                - Manifold: contractId or slug

        Returns:
            Market data dict or None on error.
        """
        ...

    @abstractmethod
    def normalize_trade(self, raw: dict) -> Trade:
        """Convert a raw API response dict into a Trade object.

        Must set trade.source = self.name and trade.currency = self.currency.
        """
        ...

    def detect_api_key(self, api_key: str) -> bool:
        """Check if an API key belongs to this provider."""
        return api_key.startswith(self.api_key_prefix)

    @abstractmethod
    def detect_file_format(self, records: List[dict]) -> bool:
        """Check if a list of raw dicts (from JSON/CSV) matches this provider's format.

        Used for auto-detecting provider when importing files.

        Args:
            records: First few records from the file.

        Returns:
            True if records match this provider's expected format.
        """
        ...


class ProviderRegistry:
    """Registry for market providers. Auto-detects provider from API key or file format."""

    _providers: Dict[str, MarketProvider] = {}

    @classmethod
    def register(cls, provider: MarketProvider):
        cls._providers[provider.name] = provider

    @classmethod
    def get(cls, name: str) -> MarketProvider:
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}. Available: {list(cls._providers.keys())}")
        return cls._providers[name]

    @classmethod
    def detect_from_key(cls, api_key: str) -> Optional[MarketProvider]:
        """Auto-detect provider from API key prefix."""
        for provider in cls._providers.values():
            if provider.detect_api_key(api_key):
                return provider
        return None

    @classmethod
    def detect_from_file(cls, records: List[dict]) -> Optional[MarketProvider]:
        """Auto-detect provider from file record format."""
        for provider in cls._providers.values():
            if provider.detect_file_format(records):
                return provider
        return None

    @classmethod
    def all(cls) -> List[MarketProvider]:
        return list(cls._providers.values())

    @classmethod
    def names(cls) -> List[str]:
        return list(cls._providers.keys())
```

### 1.3 New file: `prediction_analyzer/providers/limitless.py`

Refactor existing `utils/data.py` logic into provider class. Keep `utils/data.py` as a thin backward-compat wrapper.

```python
import logging
import requests
from typing import List, Optional, Dict, Any
from .base import MarketProvider
from ..trade_loader import Trade, _parse_timestamp

logger = logging.getLogger(__name__)


class LimitlessProvider(MarketProvider):
    name = "limitless"
    display_name = "Limitless Exchange"
    api_key_prefix = "lmts_"
    currency = "USDC"
    BASE_URL = "https://api.limitless.exchange"

    def fetch_trades(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        all_trades = []
        page = 1
        headers = {"Authorization": f"Bearer {api_key}"}

        while True:
            params = {"page": page, "limit": page_limit}
            try:
                resp = requests.get(
                    f"{self.BASE_URL}/portfolio/history",
                    params=params, headers=headers, timeout=15
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

            logger.info("Downloaded page %d (%d trades)", page, len(all_trades))
            if len(all_trades) >= data.get("totalCount", 0):
                break
            page += 1

        return all_trades

    def normalize_trade(self, raw: dict) -> Trade:
        # Handle nested market object (API format)
        market_data = raw.get("market")
        if isinstance(market_data, dict):
            market_title = market_data.get("title") or "Unknown"
            market_slug = market_data.get("slug") or "unknown"
        else:
            market_title = raw.get("market") if isinstance(raw.get("market"), str) else "Unknown"
            market_slug = raw.get("market_slug") or "unknown"

        # Convert from micro-units (USDC 6 decimals) if API format
        if "collateralAmount" in raw:
            cost = float(raw.get("collateralAmount") or 0) / 1_000_000
            pnl = float(raw.get("pnl") or 0) / 1_000_000
            shares = float(raw.get("outcomeTokenAmount") or 0) / 1_000_000
        else:
            cost = float(raw.get("cost") or 0)
            pnl = float(raw.get("pnl") or 0)
            shares = float(raw.get("shares") or 0)

        trade_type = raw.get("type") or raw.get("strategy") or "Buy"
        side = raw.get("side")
        if not side:
            outcome_index = raw.get("outcomeIndex")
            side = "YES" if outcome_index == 0 or outcome_index is None else "NO"

        return Trade(
            market=market_title,
            market_slug=market_slug,
            timestamp=_parse_timestamp(raw.get("timestamp") or raw.get("blockTimestamp") or 0),
            price=float(raw.get("price") or 0),
            shares=shares,
            cost=cost,
            type=trade_type,
            side=side,
            pnl=pnl,
            tx_hash=raw.get("tx_hash") or raw.get("transactionHash"),
            source="limitless",
            currency="USDC",
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.BASE_URL}/markets/{market_id}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def detect_file_format(self, records: List[dict]) -> bool:
        """Limitless format: has collateralAmount or outcomeTokenAmount fields, or nested market object."""
        if not records:
            return False
        first = records[0]
        return (
            "collateralAmount" in first
            or "outcomeTokenAmount" in first
            or (isinstance(first.get("market"), dict) and "slug" in first["market"])
        )
```

---

## Phase 2: Polymarket Provider

### API Reference

| Endpoint | URL | Auth | Pagination |
|----------|-----|------|-----------|
| Public trades | `GET https://data-api.polymarket.com/trades` | None (pass `user` wallet address as query param) | `limit` max 500, time-window via `start`/`end` |
| User activity | `GET https://data-api.polymarket.com/activity` | None (pass `user` wallet address) | `limit` max 500, `start`/`end` Unix timestamps |
| User positions | `GET https://data-api.polymarket.com/positions` | None (pass `user` wallet address) | `limit` max 500 |
| Market list | `GET https://gamma-api.polymarket.com/markets` | None | `limit`/`offset` (offset-based) |
| CLOB trades (auth) | `GET https://clob.polymarket.com/data/trades` | L2 HMAC (py-clob-client) | cursor-based, initial `"MA=="`, end `"LTE="` |

### Exact API Response: `GET /trades` (Data API, public)

Query params: `user` (wallet address), `market` (conditionId), `limit` (max 500), `side` (BUY/SELL)

```json
{
  "side": "BUY",
  "asset": "71321044564545...",
  "conditionId": "0xabc123...",
  "size": 150.5,
  "usdcSize": 75.25,
  "price": 0.50,
  "timestamp": 1709827800,
  "transactionHash": "0xdef456...",
  "outcomeIndex": 0,
  "outcome": "Yes",
  "title": "Will Bitcoin reach $100k by end of 2025?",
  "slug": "will-bitcoin-reach-100k-by-end-of-2025",
  "icon": "https://...",
  "eventSlug": "bitcoin-100k",
  "proxyWallet": "0x...",
  "name": "trader_name",
  "pseudonym": "Trader123"
}
```

### Exact API Response: `GET /markets` (Gamma API, public)

```json
{
  "id": "12345",
  "question": "Will Bitcoin reach $100k?",
  "conditionId": "0xabc123...",
  "slug": "will-bitcoin-reach-100k",
  "outcomes": "[\"Yes\",\"No\"]",
  "outcomePrices": "[\"0.65\",\"0.35\"]",
  "volume": "1500000",
  "liquidity": "250000",
  "active": true,
  "closed": false,
  "endDate": "2025-12-31T23:59:59Z",
  "description": "...",
  "category": "Crypto",
  "negRisk": false,
  "image": "https://..."
}
```

**IMPORTANT**: `outcomes` and `outcomePrices` are **stringified JSON** — must call `json.loads()` on them.

### Authentication Options

**Option A — Public Data API (RECOMMENDED for MVP)**:
No auth needed. Just pass the user's Polymarket wallet address as `user` query param. This returns full trade history with market titles, prices, sizes, outcomes.

**Option B — CLOB API (for advanced features)**:
Requires `py-clob-client` package and user's Ethereum private key. Auth uses L2 HMAC-SHA256 signing with derived API credentials.

```python
# pip install py-clob-client
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import TradeParams

client = ClobClient("https://clob.polymarket.com", key="0xPRIVATE_KEY", chain_id=137)
client.set_api_creds(client.create_or_derive_api_creds())

# Headers set automatically by SDK:
# POLY_ADDRESS, POLY_SIGNATURE (HMAC), POLY_TIMESTAMP, POLY_API_KEY, POLY_PASSPHRASE
# HMAC message = timestamp + method + path + body
```

### New file: `prediction_analyzer/providers/polymarket.py`

```python
import json
import logging
import requests
from typing import List, Optional, Dict, Any
from .base import MarketProvider
from ..trade_loader import Trade, _parse_timestamp

logger = logging.getLogger(__name__)


class PolymarketProvider(MarketProvider):
    name = "polymarket"
    display_name = "Polymarket"
    api_key_prefix = "0x"  # Wallet addresses start with 0x
    currency = "USDC"
    DATA_API_URL = "https://data-api.polymarket.com"
    GAMMA_API_URL = "https://gamma-api.polymarket.com"

    def fetch_trades(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        """Fetch trades using the public Data API.

        Args:
            api_key: Polymarket wallet address (0x...).
            page_limit: Trades per request (max 500).
        """
        all_trades = []
        limit = min(page_limit, 500)

        # Data API has no cursor — paginate by narrowing timestamp windows
        # First fetch: get most recent trades
        params = {"user": api_key, "limit": limit, "type": "TRADE"}
        url = f"{self.DATA_API_URL}/activity"

        while True:
            try:
                resp = requests.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as exc:
                logger.error("Polymarket API error: %s", exc)
                break

            if not data:
                break

            for raw in data:
                all_trades.append(self.normalize_trade(raw))

            logger.info("Downloaded %d Polymarket trades so far", len(all_trades))

            # Paginate by setting end timestamp to oldest trade's timestamp - 1
            if len(data) < limit:
                break  # No more pages

            oldest_ts = min(t.get("timestamp", 0) for t in data)
            if oldest_ts <= 0:
                break
            params["end"] = oldest_ts - 1

        return all_trades

    def normalize_trade(self, raw: dict) -> Trade:
        """Convert Polymarket Data API trade/activity to Trade object.

        Data API /activity response fields:
            side: "BUY" or "SELL"
            asset: token ID string
            conditionId: hex string (market condition)
            size: float (token quantity)
            usdcSize: float (USDC amount)
            price: float (0-1)
            timestamp: int (Unix seconds)
            transactionHash: hex string
            outcomeIndex: int (0=Yes, 1=No)
            outcome: "Yes" or "No"
            title: market question string
            slug: URL-friendly market slug
            eventSlug: parent event slug
        """
        return Trade(
            market=raw.get("title") or "Unknown",
            market_slug=raw.get("slug") or raw.get("conditionId") or "unknown",
            timestamp=_parse_timestamp(raw.get("timestamp") or 0),
            price=float(raw.get("price") or 0),
            shares=float(raw.get("size") or 0),
            cost=float(raw.get("usdcSize") or 0),
            type=(raw.get("side") or "BUY").title(),  # "BUY" → "Buy", "SELL" → "Sell"
            side=(raw.get("outcome") or "Yes").upper(),  # "Yes" → "YES", "No" → "NO"
            pnl=0.0,  # Data API does not provide per-trade PnL — compute in post-processing
            tx_hash=raw.get("transactionHash"),
            source="polymarket",
            currency="USDC",
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market from Gamma API. market_id can be slug or conditionId."""
        try:
            resp = requests.get(
                f"{self.GAMMA_API_URL}/markets",
                params={"slug": market_id, "limit": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                markets = resp.json()
                if markets:
                    market = markets[0]
                    # Parse stringified JSON fields
                    for field in ("outcomes", "outcomePrices"):
                        if isinstance(market.get(field), str):
                            market[field] = json.loads(market[field])
                    return market
        except Exception:
            pass
        return None

    def detect_file_format(self, records: List[dict]) -> bool:
        """Polymarket format: has conditionId, or (outcome + usdcSize), or slug + side with BUY/SELL."""
        if not records:
            return False
        first = records[0]
        return (
            "conditionId" in first
            or "usdcSize" in first
            or ("eventSlug" in first and "outcome" in first)
        )
```

### New pip dependency

```
py-clob-client>=0.1.0  # Optional: only needed for CLOB authenticated endpoints
```

For MVP, the public Data API needs **no extra dependencies** beyond `requests`.

---

## Phase 3: Kalshi Provider

### API Reference

| Endpoint | URL | Auth | Pagination |
|----------|-----|------|-----------|
| Get fills (user trades) | `GET /trade-api/v2/portfolio/fills` | RSA-PSS signing | cursor-based, `limit` 1-1000, `cursor` string |
| Get positions | `GET /trade-api/v2/portfolio/positions` | RSA-PSS signing | cursor-based |
| Get markets | `GET /trade-api/v2/markets` | None | cursor-based |
| Get single market | `GET /trade-api/v2/markets/{ticker}` | None | N/A |
| Get public trades | `GET /trade-api/v2/markets/trades` | None | cursor-based |

Base URL: `https://api.elections.kalshi.com` (serves ALL markets despite subdomain name)
Demo URL: `https://demo-api.kalshi.co`

### Exact API Response: `GET /trade-api/v2/portfolio/fills`

Query params: `ticker`, `order_id`, `min_ts`, `max_ts`, `limit`, `cursor`

```json
{
  "fills": [
    {
      "fill_id": "abc123",
      "trade_id": "trade-456",
      "order_id": "order-789",
      "ticker": "KXBTC-25MAR14-T85000",
      "market_ticker": "KXBTC-25MAR14-T85000",
      "side": "yes",
      "action": "buy",
      "count": 10,
      "count_fp": "10.00",
      "price": 56,
      "yes_price": 56,
      "no_price": 44,
      "yes_price_fixed": "0.5600",
      "no_price_fixed": "0.4400",
      "is_taker": true,
      "fee_cost": "0.5600",
      "client_order_id": "client-order-1",
      "created_time": "2025-03-07T15:30:00Z",
      "subaccount_number": 0,
      "ts": 1709827800
    }
  ],
  "cursor": "next_page_cursor_string_or_empty"
}
```

**DEPRECATION WARNING**: By March 12, 2026, integer fields (`price`, `yes_price`, `no_price`, `count`, `volume`) will be REMOVED. Use `_fixed`/`_fp`/`_dollars` string equivalents instead.

### Exact API Response: `GET /trade-api/v2/markets`

Query params: `limit`, `cursor`, `event_ticker`, `series_ticker`, `status` (unopened/open/closed/settled)

```json
{
  "markets": [
    {
      "ticker": "KXHIGHNY-24JAN01-T60",
      "event_ticker": "KXHIGHNY-24JAN01",
      "market_type": "binary",
      "title": "Will the high in NYC be above 60F?",
      "subtitle": "...",
      "yes_sub_title": "Above 60",
      "no_sub_title": "60 or below",
      "status": "open",
      "yes_bid_dollars": "0.5500",
      "yes_ask_dollars": "0.5800",
      "no_bid_dollars": "0.4200",
      "no_ask_dollars": "0.4500",
      "last_price_dollars": "0.5600",
      "volume_fp": "15000.00",
      "volume_24h_fp": "500.00",
      "open_interest": 3000,
      "result": "",
      "created_time": "2024-12-15T00:00:00Z",
      "close_time": "2025-01-01T23:59:59Z"
    }
  ],
  "cursor": ""
}
```

### Exact API Response: `GET /trade-api/v2/markets/trades` (public)

Query params: `ticker`, `limit`, `cursor`, `min_ts`, `max_ts`

```json
{
  "trades": [
    {
      "trade_id": "trade-abc123",
      "ticker": "KXHIGHNY-24JAN01-T60",
      "count_fp": "10.00",
      "yes_price_dollars": "0.5600",
      "no_price_dollars": "0.4400",
      "taker_side": "yes",
      "created_time": "2025-03-07T15:30:00Z"
    }
  ],
  "cursor": ""
}
```

### Authentication: RSA-PSS Request Signing

**No login/session endpoint.** Every authenticated request is individually signed.

Required headers on every authenticated request:

| Header | Value |
|--------|-------|
| `KALSHI-ACCESS-KEY` | API Key ID string (from Kalshi dashboard Settings → API Keys) |
| `KALSHI-ACCESS-TIMESTAMP` | Current time in **milliseconds** as string |
| `KALSHI-ACCESS-SIGNATURE` | Base64-encoded RSA-PSS signature |

**Message to sign**: `timestamp_ms_string + HTTP_METHOD_UPPERCASE + request_path_without_query_params`

Example: For `GET /trade-api/v2/portfolio/fills?limit=5&cursor=abc`:
```
sign("1709123456789" + "GET" + "/trade-api/v2/portfolio/fills")
```

**Complete signing implementation**:

```python
import base64
import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


def load_kalshi_private_key(file_path: str):
    """Load RSA private key from PEM file."""
    with open(file_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )


def kalshi_sign_request(private_key, method: str, path: str) -> dict:
    """Build Kalshi auth headers for a request.

    Args:
        private_key: Loaded RSA private key object
        method: "GET", "POST", etc.
        path: Full path including query string, e.g. "/trade-api/v2/portfolio/fills?limit=100"

    Returns:
        Dict of auth headers to merge into request headers.
    """
    timestamp_ms = str(int(datetime.datetime.now().timestamp() * 1000))

    # Strip query params before signing
    path_without_query = path.split("?")[0]
    message = (timestamp_ms + method.upper() + path_without_query).encode("utf-8")

    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )

    return {
        "KALSHI-ACCESS-KEY": "",        # Set by caller from config
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
    }
```

**Required pip package**: `cryptography`

### API Key Format for Auto-Detection

Kalshi doesn't use a standard prefix. For auto-detection, require users to prefix their key ID:
- Store as `kalshi_<KEY_ID>:<PATH_TO_PEM_FILE>` in config
- Or: Accept `KALSHI_API_KEY_ID` + `KALSHI_PRIVATE_KEY_PATH` as separate env vars

### New file: `prediction_analyzer/providers/kalshi.py`

```python
import base64
import datetime
import logging
import requests
from typing import List, Optional, Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from .base import MarketProvider
from ..trade_loader import Trade, _parse_timestamp

logger = logging.getLogger(__name__)

BASE_URL = "https://api.elections.kalshi.com"


class KalshiProvider(MarketProvider):
    name = "kalshi"
    display_name = "Kalshi"
    api_key_prefix = "kalshi_"
    currency = "USD"

    def __init__(self):
        self._private_key = None
        self._api_key_id = None

    def _load_credentials(self, api_key: str):
        """Parse Kalshi credentials.

        Accepts format: "kalshi_<KEY_ID>:<PEM_FILE_PATH>"
        Or just the key ID if KALSHI_PRIVATE_KEY_PATH env var is set.
        """
        import os
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

    def _sign_request(self, method: str, path: str) -> dict:
        """Build auth headers with RSA-PSS signature."""
        timestamp_ms = str(int(datetime.datetime.now().timestamp() * 1000))
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
        """Fetch user's fill history from Kalshi.

        Args:
            api_key: "kalshi_<KEY_ID>:<PEM_PATH>" or "kalshi_<KEY_ID>" with env var.
            page_limit: Fills per page (max 1000).
        """
        self._load_credentials(api_key)
        all_trades = []
        cursor = None
        limit = min(page_limit, 1000)

        while True:
            path = f"/trade-api/v2/portfolio/fills?limit={limit}"
            if cursor:
                path += f"&cursor={cursor}"

            headers = self._sign_request("GET", path)
            try:
                resp = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=15)
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
            if not cursor:  # Empty string = no more pages
                break

        return all_trades

    def normalize_trade(self, raw: dict) -> Trade:
        """Convert Kalshi fill to Trade object.

        Fill fields used:
            ticker/market_ticker: str — market ticker (e.g. "KXBTC-25MAR14-T85000")
            side: "yes" or "no"
            action: "buy" or "sell"
            yes_price_fixed: str — dollar price (e.g. "0.5600")
            no_price_fixed: str — dollar price
            count_fp: str — fixed-point contract count (e.g. "10.00")
            fee_cost: str — fee in dollars
            created_time: str — ISO 8601 timestamp
            ts: int — POSIX timestamp
            fill_id: str — unique fill ID
            order_id: str — associated order ID
        """
        side_str = (raw.get("side") or "yes").upper()  # "yes" → "YES"

        # Use _fixed/_fp fields (non-deprecated)
        if side_str == "YES":
            price_str = raw.get("yes_price_fixed") or raw.get("yes_price_dollars", "0")
        else:
            price_str = raw.get("no_price_fixed") or raw.get("no_price_dollars", "0")
        price = float(price_str)

        count_str = raw.get("count_fp", "0")
        count = float(count_str)

        fee_str = raw.get("fee_cost", "0")
        fee = float(fee_str)

        return Trade(
            market=raw.get("ticker") or raw.get("market_ticker") or "Unknown",
            market_slug=raw.get("ticker") or raw.get("market_ticker") or "unknown",
            timestamp=_parse_timestamp(raw.get("created_time") or raw.get("ts") or 0),
            price=price,
            shares=count,
            cost=(price * count) + fee,  # Total cost including fee
            type=(raw.get("action") or "buy").title(),  # "buy" → "Buy"
            side=side_str,
            pnl=0.0,  # Must be computed in post-processing from fills
            tx_hash=raw.get("fill_id") or raw.get("order_id"),
            source="kalshi",
            currency="USD",
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market by ticker (public, no auth)."""
        try:
            resp = requests.get(
                f"{BASE_URL}/trade-api/v2/markets/{market_id}", timeout=10
            )
            if resp.status_code == 200:
                return resp.json().get("market")
        except Exception:
            pass
        return None

    def detect_file_format(self, records: List[dict]) -> bool:
        """Kalshi format: has ticker field with pattern like KXABC-YYMMDD-T..."""
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
```

### Kalshi Positions Endpoint (for PnL computation)

Instead of computing PnL from fills, we can fetch realized PnL directly from positions:

`GET /trade-api/v2/portfolio/positions` returns `realized_pnl_dollars` per market. After fetching fills, also fetch positions and merge PnL data:

```python
def fetch_position_pnl(self, api_key: str) -> Dict[str, float]:
    """Fetch realized PnL per ticker from positions endpoint."""
    self._load_credentials(api_key)
    pnl_map = {}
    cursor = None

    while True:
        path = "/trade-api/v2/portfolio/positions?limit=1000"
        if cursor:
            path += f"&cursor={cursor}"
        headers = self._sign_request("GET", path)
        resp = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=15)
        data = resp.json()

        for pos in data.get("market_positions", []):
            ticker = pos.get("ticker", "")
            pnl_map[ticker] = float(pos.get("realized_pnl_dollars", "0"))

        cursor = data.get("cursor", "")
        if not cursor:
            break

    return pnl_map  # Dict[ticker → realized_pnl as float]
```

---

## Phase 4: Manifold Markets Provider

### API Reference

| Endpoint | URL | Auth | Pagination |
|----------|-----|------|-----------|
| User profile | `GET /v0/me` | Required (`Key` header) | N/A |
| Bet history | `GET /v0/bets` | Optional | cursor: `before` (bet ID), `limit` max 50000 (default 10000) |
| Markets list | `GET /v0/markets` | Optional | cursor: `before` (market ID), `limit` max 1000 (default 500) |
| Single market | `GET /v0/market/{id}` or `GET /v0/slug/{slug}` | Optional | N/A |

Base URL: `https://api.manifold.markets`

### Exact API Response: `GET /v0/bets`

Query params: `userId`, `username`, `contractId`, `contractSlug`, `limit` (max 50000), `before` (bet ID cursor), `after`, `beforeTime`, `afterTime`, `order` (asc/desc), `filterRedemptions` (boolean)

```json
[
  {
    "id": "betId123",
    "userId": "userId456",
    "contractId": "contractId789",
    "answerId": "answerId000",
    "createdTime": 1672531200000,
    "updatedTime": 1672531200000,
    "amount": 100.0,
    "loanAmount": 0.0,
    "outcome": "YES",
    "shares": 150.5,
    "probBefore": 0.45,
    "probAfter": 0.52,
    "fees": {
      "creatorFee": 0,
      "platformFee": 0,
      "liquidityFee": 0
    },
    "isRedemption": false,
    "isApi": true,
    "orderAmount": 100.0,
    "limitProb": 0.50,
    "isFilled": true,
    "isCancelled": false,
    "fills": [
      {
        "matchedBetId": "...",
        "amount": 50,
        "shares": 75,
        "timestamp": 1672531200000
      }
    ],
    "expiresAt": 1672617600000
  }
]
```

**CRITICAL NOTES**:
- **NO `profit`/`pnl` field** on individual bets. Must compute client-side.
- **NO `contractSlug` or `contractQuestion`** in bet response. Only `contractId`. Must separately fetch market to get question/slug.
- `amount` is **negative for SELL** bets.
- `shares` is **negative for SELL** bets.
- `createdTime` is **milliseconds since Unix epoch**.
- Filter out `isRedemption: true` bets (internal bookkeeping for multi-outcome markets).
- `answerId` only present for MULTIPLE_CHOICE markets.
- Limit order fields (`orderAmount`, `limitProb`, `isFilled`, `isCancelled`, `fills`, `expiresAt`) are optional.

### Exact API Response: `GET /v0/me`

```json
{
  "id": "abc123",
  "username": "johndoe",
  "name": "John Doe",
  "balance": 1000.0,
  "totalDeposits": 500.0,
  "createdTime": 1672531200000
}
```

Key field: `id` is the `userId` needed for `/v0/bets?userId=...`.

### Exact API Response: `GET /v0/markets`

```json
[
  {
    "id": "marketId789",
    "slug": "will-x-happen",
    "url": "https://manifold.markets/creator/will-x-happen",
    "question": "Will X happen by 2025?",
    "creatorId": "userId456",
    "creatorUsername": "johndoe",
    "createdTime": 1672531200000,
    "closeTime": 1703980800000,
    "outcomeType": "BINARY",
    "mechanism": "cpmm-1",
    "probability": 0.65,
    "pool": {"YES": 1000, "NO": 538},
    "volume": 25000,
    "volume24Hours": 150,
    "isResolved": false,
    "resolution": null,
    "uniqueBettorCount": 42,
    "answers": []
  }
]
```

Market types by `outcomeType`: `"BINARY"` (Yes/No), `"MULTIPLE_CHOICE"` (has `answers[]`), `"PSEUDO_NUMERIC"`, `"STONK"`, `"POLL"`, `"BOUNTIED_QUESTION"`.

### Pagination Pattern

```
# Page 1: newest bets first (default desc order)
GET /v0/bets?userId=xyz&limit=1000&filterRedemptions=true

# Page 2: use `id` of the LAST bet from page 1 as `before` cursor
GET /v0/bets?userId=xyz&limit=1000&filterRedemptions=true&before=<lastBetId>

# Stop when returned array length < limit (or empty)
```

### New file: `prediction_analyzer/providers/manifold.py`

```python
import logging
import requests
from typing import List, Optional, Dict, Any
from .base import MarketProvider
from ..trade_loader import Trade, _parse_timestamp

logger = logging.getLogger(__name__)


class ManifoldProvider(MarketProvider):
    name = "manifold"
    display_name = "Manifold Markets"
    api_key_prefix = "manifold_"  # User prefixes their key with "manifold_" for auto-detection
    currency = "MANA"
    BASE_URL = "https://api.manifold.markets"

    def _get_user_id(self, api_key: str) -> str:
        """Fetch the user's ID from /v0/me using their API key."""
        raw_key = api_key.removeprefix("manifold_")
        headers = {"Authorization": f"Key {raw_key}"}
        resp = requests.get(f"{self.BASE_URL}/v0/me", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()["id"]

    def _fetch_market_metadata(self, contract_ids: List[str]) -> Dict[str, dict]:
        """Batch-fetch market metadata for contractIds missing from bet responses.

        Returns dict of contractId → {question, slug, outcomeType, probability}.
        """
        metadata = {}
        for cid in contract_ids:
            if cid in metadata:
                continue
            try:
                resp = requests.get(f"{self.BASE_URL}/v0/market/{cid}", timeout=10)
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
            except Exception:
                metadata[cid] = {"question": "Unknown", "slug": cid}
        return metadata

    def fetch_trades(self, api_key: str, page_limit: int = 1000) -> List[Trade]:
        """Fetch user's bet history from Manifold Markets.

        Args:
            api_key: "manifold_<API_KEY>" — key from Manifold profile settings.
            page_limit: Bets per page (max 50000, default 1000).
        """
        user_id = self._get_user_id(api_key)
        all_bets = []
        cursor = None
        limit = min(page_limit, 10000)

        # Step 1: Fetch all bets (paginated)
        while True:
            params = {
                "userId": user_id,
                "limit": limit,
                "filterRedemptions": "true",
            }
            if cursor:
                params["before"] = cursor

            try:
                resp = requests.get(
                    f"{self.BASE_URL}/v0/bets", params=params, timeout=15
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

            cursor = bets[-1]["id"]  # Last bet ID as cursor

        # Step 2: Fetch market metadata for all unique contractIds
        contract_ids = list(set(b.get("contractId", "") for b in all_bets if b.get("contractId")))
        logger.info("Fetching metadata for %d Manifold markets...", len(contract_ids))
        market_meta = self._fetch_market_metadata(contract_ids)

        # Step 3: Normalize bets to Trade objects
        trades = []
        for raw in all_bets:
            meta = market_meta.get(raw.get("contractId", ""), {})
            trades.append(self.normalize_trade(raw, meta))

        return trades

    def normalize_trade(self, raw: dict, market_meta: Optional[dict] = None) -> Trade:
        """Convert Manifold bet to Trade object.

        Bet fields used:
            id: str — unique bet ID
            contractId: str — market ID (no slug/question in bet response!)
            answerId: str (optional) — for MULTIPLE_CHOICE markets
            createdTime: int — milliseconds since epoch
            amount: float — mana spent (NEGATIVE for sells)
            shares: float — tokens received (NEGATIVE for sells)
            outcome: "YES" or "NO"
            probBefore: float (0-1)
            probAfter: float (0-1)
            isRedemption: bool — filter these out
            fees: {creatorFee, platformFee, liquidityFee}

        market_meta (from separate API call):
            question: str — market question text
            slug: str — URL-friendly slug
            outcomeType: str — "BINARY", "MULTIPLE_CHOICE", etc.
            probability: float — current probability
            isResolved: bool
            resolution: str or null
        """
        if market_meta is None:
            market_meta = {}

        amount = float(raw.get("amount", 0))

        return Trade(
            market=market_meta.get("question", "Unknown"),
            market_slug=market_meta.get("slug", raw.get("contractId", "unknown")),
            timestamp=_parse_timestamp(raw.get("createdTime", 0)),
            price=float(raw.get("probAfter", 0)),
            shares=abs(float(raw.get("shares", 0))),
            cost=abs(amount),
            type="Buy" if amount > 0 else "Sell",
            side=(raw.get("outcome") or "YES").upper(),
            pnl=0.0,  # Must compute client-side (no profit field in API)
            tx_hash=raw.get("id"),
            source="manifold",
            currency="MANA",
        )

    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market by ID or slug."""
        # Try by ID first, then by slug
        for endpoint in [f"/v0/market/{market_id}", f"/v0/slug/{market_id}"]:
            try:
                resp = requests.get(f"{self.BASE_URL}{endpoint}", timeout=10)
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass
        return None

    def detect_file_format(self, records: List[dict]) -> bool:
        """Manifold format: has contractId, probBefore/probAfter, or outcome + shares with no ticker."""
        if not records:
            return False
        first = records[0]
        return (
            "contractId" in first
            or ("probBefore" in first and "probAfter" in first)
            or ("outcome" in first and "shares" in first and "ticker" not in first and "conditionId" not in first)
        )
```

**No extra pip dependencies** — uses only `requests`.

---

## Phase 5: Trade Model Enhancement

### 5.1 Update Trade dataclass in `trade_loader.py` (line 37-48)

Add two new fields with defaults for backward compatibility:

```python
@dataclass
class Trade:
    market: str
    market_slug: str
    timestamp: datetime
    price: float
    shares: float
    cost: float
    type: str           # "Buy" or "Sell"
    side: str           # "YES" or "NO"
    pnl: float = 0.0
    tx_hash: Optional[str] = None
    source: str = "limitless"   # NEW: "polymarket", "kalshi", "manifold", "limitless"
    currency: str = "USD"       # NEW: "USD", "USDC", "MANA"
```

### 5.2 Update `to_dict()` in `trade_loader.py` (line 50-63)

Add the new fields to the dict output:

```python
def to_dict(self) -> Dict[str, Any]:
    return {
        "market": self.market,
        "market_slug": self.market_slug,
        "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
        "price": sanitize_numeric(self.price),
        "shares": sanitize_numeric(self.shares),
        "cost": sanitize_numeric(self.cost),
        "type": self.type,
        "side": self.side,
        "pnl": sanitize_numeric(self.pnl),
        "tx_hash": self.tx_hash,
        "source": self.source,          # NEW
        "currency": self.currency,      # NEW
    }
```

### 5.3 Update API schema in `api/schemas/trade.py` (TradeBase, line 10-21)

```python
class TradeBase(BaseModel):
    market: str
    market_slug: str
    timestamp: datetime
    price: float = 0.0
    shares: float = 0.0
    cost: float = 0.0
    type: str
    side: str
    pnl: float = 0.0
    tx_hash: Optional[str] = None
    source: str = "limitless"       # NEW
    currency: str = "USD"           # NEW
```

### 5.4 Update ORM model in `api/models/trade.py` (Trade model, lines 32-66)

Add columns:

```python
source = Column(String(50), nullable=False, default="limitless", index=True)
currency = Column(String(10), nullable=False, default="USD")
```

Update the composite index:

```python
Index("ix_trades_user_source_market", "user_id", "source", "market_slug")
```

### 5.5 Update `load_trades()` in `trade_loader.py` (lines 164-252)

Add provider auto-detection for file imports:

```python
def load_trades(file_path: str) -> List[Trade]:
    # ... existing file loading code ...

    # NEW: Auto-detect provider from file format
    from .providers import ProviderRegistry
    provider = ProviderRegistry.detect_from_file(raw_trades[:5])

    if provider:
        # Use provider-specific normalization
        trades = [provider.normalize_trade(t) for t in raw_trades]
    else:
        # Fallback: existing Limitless parsing logic (for backward compat)
        for t in raw_trades:
            # ... existing parsing code, unchanged ...
```

### 5.6 PnL Post-Processing

New file: `prediction_analyzer/providers/pnl_calculator.py`

```python
"""Compute PnL for providers that don't supply it (Kalshi, Manifold, Polymarket)."""
from typing import List, Dict
from collections import defaultdict
from ..trade_loader import Trade


def compute_realized_pnl(trades: List[Trade]) -> List[Trade]:
    """Compute realized PnL from buy/sell pairs per market+side.

    Uses FIFO matching: earliest buys are matched against earliest sells.

    Args:
        trades: List of trades sorted by timestamp (ascending).

    Returns:
        Same list with pnl field updated on sell trades.
    """
    # Group buys by (market_slug, side, source)
    buy_queues: Dict[tuple, list] = defaultdict(list)  # key → [(price, shares_remaining)]
    result = []

    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    for trade in sorted_trades:
        key = (trade.market_slug, trade.side, trade.source)

        if trade.type.lower().endswith("buy"):
            buy_queues[key].append([trade.price, trade.shares])
            result.append(trade)
        elif trade.type.lower().endswith("sell"):
            # Match against buy queue (FIFO)
            remaining_shares = trade.shares
            total_buy_cost = 0.0

            queue = buy_queues[key]
            while remaining_shares > 0 and queue:
                buy_price, buy_shares = queue[0]
                matched = min(remaining_shares, buy_shares)
                total_buy_cost += matched * buy_price
                remaining_shares -= matched
                queue[0][1] -= matched
                if queue[0][1] <= 0:
                    queue.pop(0)

            sell_revenue = (trade.shares - remaining_shares) * trade.price
            trade.pnl = sell_revenue - total_buy_cost
            result.append(trade)
        else:
            result.append(trade)

    return result


def apply_position_pnl(trades: List[Trade], pnl_map: Dict[str, float]) -> List[Trade]:
    """Apply realized PnL from positions endpoint (e.g. Kalshi) to trades.

    Distributes the total realized PnL for each market proportionally
    across sell trades in that market.

    Args:
        trades: List of trades.
        pnl_map: Dict of market_slug → total realized PnL.

    Returns:
        Updated trades list.
    """
    from collections import defaultdict

    # Count sell trades per market to distribute PnL
    sell_counts = defaultdict(int)
    for t in trades:
        if t.type.lower().endswith("sell") and t.market_slug in pnl_map:
            sell_counts[t.market_slug] += 1

    for t in trades:
        if t.type.lower().endswith("sell") and t.market_slug in pnl_map:
            count = sell_counts[t.market_slug]
            if count > 0:
                t.pnl = pnl_map[t.market_slug] / count

    return trades
```

---

## Phase 6: Config & Auth Updates

### 6.1 Update `config.py`

```python
# prediction_analyzer/config.py

# Legacy (kept for backward compat)
API_BASE_URL = "https://api.limitless.exchange"
DEFAULT_TRADE_FILE = "limitless_trades.json"

# Multi-market provider configuration
PROVIDER_CONFIGS = {
    "limitless": {
        "base_url": "https://api.limitless.exchange",
        "api_key_prefix": "lmts_",
        "currency": "USDC",
        "display_name": "Limitless Exchange",
    },
    "polymarket": {
        "data_url": "https://data-api.polymarket.com",
        "gamma_url": "https://gamma-api.polymarket.com",
        "clob_url": "https://clob.polymarket.com",
        "api_key_prefix": "0x",  # Wallet address
        "currency": "USDC",
        "display_name": "Polymarket",
    },
    "kalshi": {
        "base_url": "https://api.elections.kalshi.com",
        "demo_url": "https://demo-api.kalshi.co",
        "api_key_prefix": "kalshi_",
        "currency": "USD",
        "display_name": "Kalshi",
    },
    "manifold": {
        "base_url": "https://api.manifold.markets",
        "api_key_prefix": "manifold_",
        "currency": "MANA",
        "display_name": "Manifold Markets",
    },
}
```

### 6.2 Update `.env.example`

```
# Limitless Exchange (existing)
LIMITLESS_API_KEY=lmts_your_key_here

# Polymarket (wallet address for public Data API, or private key for CLOB)
POLYMARKET_WALLET=0xYourWalletAddress

# Kalshi (RSA key pair)
KALSHI_API_KEY_ID=your_api_key_id
KALSHI_PRIVATE_KEY_PATH=kalshi_private_key.pem

# Manifold Markets
MANIFOLD_API_KEY=manifold_your_key_here
```

### 6.3 Update `utils/auth.py`

Replace Limitless-specific logic with provider-aware auth:

```python
"""Authentication utilities for prediction market APIs."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_api_key(provider: str = "limitless") -> Optional[str]:
    """Get API key for a provider from environment.

    Env var mapping:
        limitless  → LIMITLESS_API_KEY
        polymarket → POLYMARKET_WALLET
        kalshi     → KALSHI_API_KEY_ID (also needs KALSHI_PRIVATE_KEY_PATH)
        manifold   → MANIFOLD_API_KEY
    """
    env_map = {
        "limitless": "LIMITLESS_API_KEY",
        "polymarket": "POLYMARKET_WALLET",
        "kalshi": "KALSHI_API_KEY_ID",
        "manifold": "MANIFOLD_API_KEY",
    }
    var_name = env_map.get(provider, f"{provider.upper()}_API_KEY")
    return os.environ.get(var_name)


def get_auth_headers(api_key: str) -> dict:
    """Legacy function for Limitless Exchange backward compat."""
    return {"Authorization": f"Bearer {api_key}"}


def detect_provider_from_key(api_key: str) -> str:
    """Detect provider name from API key format."""
    if api_key.startswith("lmts_"):
        return "limitless"
    elif api_key.startswith("0x"):
        return "polymarket"
    elif api_key.startswith("kalshi_"):
        return "kalshi"
    elif api_key.startswith("manifold_"):
        return "manifold"
    return "limitless"  # Default fallback
```

---

## Phase 7: MCP Server & API Updates

### 7.1 Update `prediction_mcp/tools/data_tools.py` — `fetch_trades` tool

Replace Limitless-specific implementation:

```python
@mcp.tool(
    name="fetch_trades",
    description="Fetch trades from a prediction market API. Supports: limitless, polymarket, kalshi, manifold. Provider is auto-detected from API key format.",
)
async def fetch_trades(
    api_key: str,
    provider: str = "auto",
    page_limit: int = 100,
) -> str:
    """
    Args:
        api_key: API key or credential for the market.
            - Limitless: starts with "lmts_"
            - Polymarket: wallet address starting with "0x"
            - Kalshi: "kalshi_<KEY_ID>:<PEM_PATH>"
            - Manifold: "manifold_<API_KEY>"
        provider: Provider name or "auto" to detect from key format.
        page_limit: Trades per page for pagination.
    """
    from prediction_analyzer.providers import ProviderRegistry

    if provider == "auto":
        detected = ProviderRegistry.detect_from_key(api_key)
        if not detected:
            return json.dumps({"error": "Could not detect provider from API key format."})
    else:
        detected = ProviderRegistry.get(provider)

    trades = detected.fetch_trades(api_key, page_limit)

    # Apply PnL computation if provider doesn't supply it
    if detected.name in ("kalshi", "manifold", "polymarket"):
        from prediction_analyzer.providers.pnl_calculator import compute_realized_pnl
        trades = compute_realized_pnl(trades)

    session.trades.extend(trades)
    session.filtered_trades = list(session.trades)
    if detected.name not in (session.sources or []):
        session.sources.append(detected.name)

    # ... rest of response formatting ...
```

### 7.2 Update `prediction_mcp/state.py`

```python
@dataclass
class SessionState:
    trades: List[Trade] = field(default_factory=list)
    filtered_trades: List[Trade] = field(default_factory=list)
    active_filters: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)  # Changed from single source
```

### 7.3 Update `prediction_mcp/server.py` line 52

Change instructions from "Limitless Exchange API" to "prediction market APIs (Limitless, Polymarket, Kalshi, Manifold)".

### 7.4 Update `prediction_mcp/tools/data_tools.py` lines 51-54, 60, 188-189

Remove all "lmts_" prefix assumptions and Limitless-specific descriptions.

### 7.5 Update FastAPI routes in `api/routers/trades.py`

Add `source` query parameter:

```python
@router.get("/trades")
async def get_trades(
    market_slug: Optional[str] = None,
    source: Optional[str] = None,  # NEW: filter by provider
    limit: int = 100,
    offset: int = 0,
    ...
):
```

Add new provider listing endpoint:

```python
@router.get("/providers")
async def list_providers():
    from prediction_analyzer.providers import ProviderRegistry
    return [
        {"name": p.name, "display_name": p.display_name, "currency": p.currency}
        for p in ProviderRegistry.all()
    ]
```

### 7.6 Update `__main__.py`

Add `--provider` CLI argument:

```python
parser.add_argument("--provider", choices=["limitless", "polymarket", "kalshi", "manifold", "auto"],
                    default="auto", help="Prediction market provider")
```

Update help text and env var references to be provider-agnostic.

### 7.7 Update `gui.py`

Add provider selection dropdown in the API fetch dialog. Change "Limitless API key" to "API Key / Wallet Address".

---

## Phase 8: File Import Auto-Detection

Update `load_trades()` to auto-detect provider from file contents:

```python
def load_trades(file_path: str) -> List[Trade]:
    # ... existing file loading code to get raw_trades ...

    from .providers import ProviderRegistry

    # Sample first 5 records for format detection
    sample = raw_trades[:5] if raw_trades else []
    provider = ProviderRegistry.detect_from_file(sample)

    if provider:
        logger.info("Auto-detected file format: %s", provider.display_name)
        return [provider.normalize_trade(t) for t in raw_trades]

    # Fallback: existing Limitless parsing logic
    logger.info("Using default (Limitless) parsing for file")
    # ... existing code unchanged ...
```

### File Format Detection Rules

| Provider | Detection Heuristic |
|----------|-------------------|
| Limitless | `collateralAmount` field, or nested `market` dict with `slug` key |
| Polymarket | `conditionId` field, or `usdcSize` field, or `eventSlug` + `outcome` |
| Kalshi | `ticker` starting with "KX", or `yes_price`/`yes_price_fixed`/`taker_side` fields |
| Manifold | `contractId` field, or `probBefore`+`probAfter`, or `outcome`+`shares` without `ticker`/`conditionId` |

---

## Phase 9: Cross-Market Analysis

### 9.1 Add `filter_trades_by_source()` to `trade_filter.py`

```python
def filter_trades_by_source(trades: List[Trade], source: str) -> List[Trade]:
    return [t for t in trades if t.source == source]
```

### 9.2 Update `pnl.py` summaries

Add `source` breakdown to global summary output:

```python
def calculate_global_pnl_summary(trades):
    # ... existing code ...
    summary["by_source"] = {}
    for source in set(t.source for t in trades):
        source_trades = [t for t in trades if t.source == source]
        summary["by_source"][source] = {
            "total_trades": len(source_trades),
            "total_pnl": sum(t.pnl for t in source_trades),
            "currency": source_trades[0].currency if source_trades else "USD",
        }
    return summary
```

### 9.3 Add MCP tool: `get_provider_breakdown`

Returns per-provider stats when trades from multiple sources are loaded.

---

## Dependencies

### New pip packages needed

| Package | Required By | Purpose |
|---------|------------|---------|
| `cryptography` | Kalshi provider | RSA-PSS request signing |
| `py-clob-client` (optional) | Polymarket CLOB | Only for authenticated CLOB endpoints; public Data API needs no extra deps |

### Update `requirements.txt`

```
cryptography>=41.0.0
# py-clob-client>=0.1.0  # Optional: uncomment for Polymarket CLOB auth
```

### No changes needed to existing dependencies

`requests`, `pandas`, `numpy`, `fastapi`, `sqlalchemy` — all already present and sufficient.

---

## Implementation Order

| Step | Phase | Effort | Description |
|------|-------|--------|-------------|
| 1 | 5.1-5.2 | Small | Add `source`/`currency` fields to Trade dataclass + `to_dict()` |
| 2 | 1.1-1.2 | Medium | Create `providers/base.py` (ABC + Registry) |
| 3 | 1.3 | Medium | Create `providers/limitless.py` (refactor from utils/data.py) |
| 4 | 4 | Medium | Create `providers/manifold.py` (easiest API — good first test) |
| 5 | 3 | Medium | Create `providers/kalshi.py` (RSA auth) |
| 6 | 2 | Medium | Create `providers/polymarket.py` (public Data API) |
| 7 | 5.5-5.6 | Medium | File auto-detection + PnL calculator |
| 8 | 6 | Small | Config, auth, and env updates |
| 9 | 5.3-5.4 | Small | API schema + ORM model updates |
| 10 | 7 | Medium | MCP server + FastAPI + CLI + GUI updates |
| 11 | 8 | Small | File import auto-detection integration |
| 12 | 9 | Medium | Cross-market analysis features |

---

## New Files Summary

```
prediction_analyzer/providers/
├── __init__.py              # Register all providers
├── base.py                  # MarketProvider ABC + ProviderRegistry
├── limitless.py             # Limitless Exchange (refactored from utils/data.py)
├── polymarket.py            # Polymarket Data API + Gamma API
├── kalshi.py                # Kalshi v2 API with RSA-PSS signing
├── manifold.py              # Manifold Markets API
└── pnl_calculator.py        # FIFO PnL computation for providers without PnL
```

## Modified Files Summary

```
prediction_analyzer/
├── trade_loader.py           # Add source/currency fields, auto-detect in load_trades()
├── config.py                 # Add PROVIDER_CONFIGS dict
├── utils/auth.py             # Multi-provider auth, detect_provider_from_key()
├── utils/data.py             # Thin wrapper delegating to LimitlessProvider
├── trade_filter.py           # Add filter_trades_by_source()
├── pnl.py                    # Add by_source breakdown to summaries
├── api/schemas/trade.py      # Add source/currency to TradeBase
├── api/models/trade.py       # Add source/currency columns + index
├── api/routers/trades.py     # Add source param, /providers endpoint
├── __main__.py               # Add --provider arg, update help text
prediction_mcp/
├── tools/data_tools.py       # Provider-aware fetch_trades, remove Limitless refs
├── state.py                  # sources: List[str] instead of source: Optional[str]
├── server.py                 # Update instructions text
gui.py                        # Add provider dropdown, generic key prompt
.env.example                  # Add all provider env vars
requirements.txt              # Add cryptography
```

---

## Testing Strategy

### Unit Tests for Each Provider

Create `tests/providers/` directory:

```
tests/providers/
├── __init__.py
├── test_base.py              # Test ProviderRegistry detection
├── test_limitless.py         # Test normalize_trade with sample data
├── test_polymarket.py        # Test normalize_trade with sample data
├── test_kalshi.py            # Test normalize_trade, signing
├── test_manifold.py          # Test normalize_trade with sample data
├── test_pnl_calculator.py    # Test FIFO PnL matching
└── test_file_detection.py    # Test detect_file_format for all providers
```

### Sample Test Data (use in tests)

**Polymarket sample trade:**
```json
{"side": "BUY", "conditionId": "0xabc", "size": 100.0, "usdcSize": 50.0, "price": 0.50, "timestamp": 1709827800, "transactionHash": "0xdef", "outcomeIndex": 0, "outcome": "Yes", "title": "Test Market", "slug": "test-market"}
```

**Kalshi sample fill:**
```json
{"fill_id": "f1", "ticker": "KXTEST-25MAR-T50", "side": "yes", "action": "buy", "count_fp": "10.00", "yes_price_fixed": "0.5600", "no_price_fixed": "0.4400", "fee_cost": "0.56", "created_time": "2025-03-07T15:30:00Z", "ts": 1709827800}
```

**Manifold sample bet:**
```json
{"id": "bet1", "contractId": "cid1", "createdTime": 1672531200000, "amount": 100.0, "shares": 150.5, "outcome": "YES", "probBefore": 0.45, "probAfter": 0.52, "isRedemption": false, "fees": {"creatorFee": 0, "platformFee": 0, "liquidityFee": 0}}
```
