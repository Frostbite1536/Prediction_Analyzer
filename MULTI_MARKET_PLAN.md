# Multi-Market Support Plan: Polymarket, Kalshi, Manifold Markets

## Overview

Add support for the three largest prediction markets alongside the existing Limitless Exchange integration:

1. **Polymarket** — Largest by volume (~$1B+ monthly). Crypto-based, binary outcomes on CLOB (Central Limit Order Book). Uses USDC on Polygon.
2. **Kalshi** — Largest US-regulated exchange (CFTC-regulated). USD-settled event contracts. REST API with API key auth.
3. **Manifold Markets** — Largest play-money market. Open-source, generous free API. Supports binary, multi-choice, and numeric markets.

---

## Current Architecture (Limitless Exchange Only)

- **Config**: `config.py` hardcodes `API_BASE_URL = "https://api.limitless.exchange"`
- **Data fetch**: `utils/data.py` → `fetch_trade_history(api_key)` calls `/portfolio/history`
- **Trade model**: `trade_loader.py` → `Trade` dataclass (market, market_slug, timestamp, price, shares, cost, type, side, pnl, tx_hash)
- **Unit handling**: Detects `collateralAmount` field → divides by 1M (USDC 6 decimals)
- **Auth**: `utils/auth.py` expects `lmts_` prefixed API keys
- **MCP tools**: `prediction_mcp/tools/data_tools.py` → `fetch_trades` tool hardcoded to Limitless

---

## Phase 1: Market Provider Abstraction Layer

**Goal**: Create a pluggable provider system so each market has its own fetcher/normalizer.

### 1.1 New file: `prediction_analyzer/providers/__init__.py`

```python
from .base import MarketProvider, ProviderRegistry
from .limitless import LimitlessProvider
from .polymarket import PolymarketProvider
from .kalshi import KalshiProvider
from .manifold import ManifoldProvider
```

### 1.2 New file: `prediction_analyzer/providers/base.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..trade_loader import Trade

class MarketProvider(ABC):
    """Base class for prediction market data providers."""

    name: str                    # e.g. "polymarket"
    display_name: str            # e.g. "Polymarket"
    api_key_prefix: str          # e.g. "poly_", "kalshi_", "lmts_"

    @abstractmethod
    def fetch_trades(self, api_key: str, page_limit: int = 100) -> List[Trade]:
        """Fetch user's trade history from this market."""
        ...

    @abstractmethod
    def fetch_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch details for a specific market."""
        ...

    @abstractmethod
    def normalize_trade(self, raw: dict) -> Trade:
        """Convert a raw API response dict into a Trade object."""
        ...

    def detect_api_key(self, api_key: str) -> bool:
        """Check if an API key belongs to this provider."""
        return api_key.startswith(self.api_key_prefix)


class ProviderRegistry:
    """Registry for market providers. Auto-detects provider from API key."""

    _providers: Dict[str, MarketProvider] = {}

    @classmethod
    def register(cls, provider: MarketProvider):
        cls._providers[provider.name] = provider

    @classmethod
    def get(cls, name: str) -> MarketProvider:
        return cls._providers[name]

    @classmethod
    def detect(cls, api_key: str) -> Optional[MarketProvider]:
        for provider in cls._providers.values():
            if provider.detect_api_key(api_key):
                return provider
        return None

    @classmethod
    def all(cls) -> List[MarketProvider]:
        return list(cls._providers.values())
```

### 1.3 Move existing Limitless code → `prediction_analyzer/providers/limitless.py`

Refactor `utils/data.py` logic into the `LimitlessProvider` class. Keep backward compatibility — `utils/data.py` can delegate to the provider.

---

## Phase 2: Polymarket Provider

### API Details
- **Base URL**: `https://clob.polymarket.com` (CLOB API) + `https://data-api.polymarket.com` (Data API)
- **Auth**: API key via `POLY-ADDRESS`, `POLY-SIGNATURE`, `POLY-TIMESTAMP`, `POLY-NONCE` headers (EIP-712 signing) for private endpoints. Public market data needs no auth.
- **Trade history**: `GET /data/trade-history` (Data API, needs wallet-based auth)
- **Markets**: `GET /markets` (CLOB API, public)
- **Format**: REST/JSON, prices 0-1, amounts in USDC (6 decimals on Polygon)
- **Rate limits**: ~100 req/min for authenticated endpoints

### New file: `prediction_analyzer/providers/polymarket.py`

```python
class PolymarketProvider(MarketProvider):
    name = "polymarket"
    display_name = "Polymarket"
    api_key_prefix = "poly_"
    BASE_URL = "https://data-api.polymarket.com"
    CLOB_URL = "https://clob.polymarket.com"

    def normalize_trade(self, raw: dict) -> Trade:
        # Polymarket returns:
        # - market (slug/condition_id), title
        # - side: "BUY"/"SELL", outcome: "Yes"/"No"
        # - price: float 0-1
        # - size: token amount
        # - fee, timestamp (ISO 8601)
        return Trade(
            market=raw.get("market_title", raw.get("title", "Unknown")),
            market_slug=raw.get("market_slug", raw.get("condition_id", "unknown")),
            timestamp=_parse_timestamp(raw.get("timestamp") or raw.get("match_time")),
            price=float(raw.get("price", 0)),
            shares=float(raw.get("size", 0)),
            cost=float(raw.get("price", 0)) * float(raw.get("size", 0)),
            type=raw.get("side", "BUY").title(),  # "BUY" → "Buy"
            side=raw.get("outcome", "Yes").upper(),  # "Yes" → "YES"
            pnl=float(raw.get("pnl", 0)),
            tx_hash=raw.get("transaction_hash"),
        )
```

### Key considerations:
- Polymarket uses **condition IDs** (hex strings) as market identifiers, not slugs
- Trade history requires wallet-based authentication (CLOB API keys derived from wallet signature)
- Support both CLOB API key auth and CSV export file import (Polymarket lets users download trade history)

---

## Phase 3: Kalshi Provider

### API Details
- **Base URL**: `https://api.elections.kalshi.com/trade-api/v2` (production)
- **Auth**: RSA key pair or email/password → session token. API key via `Authorization: Bearer <token>` header.
- **Trade history**: `GET /portfolio/fills` (paginated, cursor-based)
- **Markets**: `GET /markets` or `GET /markets/{ticker}`
- **Format**: REST/JSON, prices in cents (1-99), amounts in cents
- **Rate limits**: 10 req/sec base tier, 100 req/sec for members

### New file: `prediction_analyzer/providers/kalshi.py`

```python
class KalshiProvider(MarketProvider):
    name = "kalshi"
    display_name = "Kalshi"
    api_key_prefix = "kalshi_"
    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def normalize_trade(self, raw: dict) -> Trade:
        # Kalshi returns:
        # - ticker: "KXBTC-25MAR14-T99999"
        # - action: "buy"/"sell"
        # - side: "yes"/"no"
        # - yes_price / no_price: int cents (1-99)
        # - count: number of contracts
        # - created_time: ISO 8601
        side_str = raw.get("side", "yes").upper()
        price_cents = raw.get("yes_price", 0) if side_str == "YES" else raw.get("no_price", 0)
        count = int(raw.get("count", 0))

        return Trade(
            market=raw.get("ticker", "Unknown"),
            market_slug=raw.get("ticker", "unknown"),
            timestamp=_parse_timestamp(raw.get("created_time")),
            price=price_cents / 100.0,  # cents → dollars
            shares=float(count),
            cost=(price_cents * count) / 100.0,  # cents → dollars
            type=raw.get("action", "buy").title(),
            side=side_str,
            pnl=0.0,  # Kalshi doesn't provide per-trade PnL; compute in post-processing
            tx_hash=raw.get("order_id"),
        )
```

### Key considerations:
- Kalshi uses **tickers** (e.g., `KXBTC-25MAR14-T99999`) as market identifiers
- Prices are in **cents** (1-99), not decimals (0.01-0.99)
- Auth requires RSA key signing or email/password login → session token
- PnL must be **computed** from fills (Kalshi doesn't return per-trade PnL)
- Pagination uses **cursor** (not page numbers)

---

## Phase 4: Manifold Markets Provider

### API Details
- **Base URL**: `https://api.manifold.markets/v0`
- **Auth**: API key via `Authorization: Key <api_key>` header. Many endpoints are public.
- **Trade history**: `GET /bets?userId=<id>` (paginated by `before` cursor)
- **Markets**: `GET /markets`, `GET /market/{slug}`
- **Format**: REST/JSON, probabilities 0-1, play-money (Mana currency)
- **Rate limits**: 1000 req/min (very generous)

### New file: `prediction_analyzer/providers/manifold.py`

```python
class ManifoldProvider(MarketProvider):
    name = "manifold"
    display_name = "Manifold Markets"
    api_key_prefix = "manifold_"
    BASE_URL = "https://api.manifold.markets/v0"

    def normalize_trade(self, raw: dict) -> Trade:
        # Manifold returns:
        # - contractId, contractSlug, contractQuestion
        # - outcome: "YES"/"NO"
        # - amount: mana spent (negative = sell)
        # - shares: tokens received
        # - probBefore, probAfter: probability shift
        # - createdTime: Unix ms
        amount = float(raw.get("amount", 0))

        return Trade(
            market=raw.get("contractQuestion", "Unknown"),
            market_slug=raw.get("contractSlug", raw.get("contractId", "unknown")),
            timestamp=_parse_timestamp(raw.get("createdTime")),
            price=float(raw.get("probAfter", 0)),
            shares=abs(float(raw.get("shares", 0))),
            cost=abs(amount),
            type="Buy" if amount > 0 else "Sell",
            side=raw.get("outcome", "YES").upper(),
            pnl=float(raw.get("profit", 0)),
            tx_hash=raw.get("id"),
        )
```

### Key considerations:
- Manifold uses **play money** (Mana), not real currency — may want a `currency` field on Trade
- Supports multi-choice markets (not just binary YES/NO)
- API is public and generous — easiest to integrate
- User ID needed for bet history (can fetch via `GET /me` with API key)

---

## Phase 5: Trade Model Enhancement

### 5.1 Add `source` field to Trade dataclass

```python
@dataclass
class Trade:
    market: str
    market_slug: str
    timestamp: datetime
    price: float
    shares: float
    cost: float
    type: str
    side: str
    pnl: float = 0.0
    tx_hash: Optional[str] = None
    source: str = "limitless"  # NEW: "polymarket", "kalshi", "manifold", "limitless"
    currency: str = "USD"      # NEW: "USD", "USDC", "MANA"
```

### 5.2 Update `to_dict()`, API schemas, and ORM models

- Add `source` and `currency` to `TradeBase` schema, `Trade` ORM model
- Add DB migration for new columns
- Update serializers

### 5.3 Compute PnL for providers that don't supply it

Create `prediction_analyzer/providers/pnl_calculator.py`:
- For Kalshi: Match buys/sells by market+side, compute realized PnL from price differences
- For Polymarket: Similar matching if PnL not provided in API response

---

## Phase 6: Config & Auth Updates

### 6.1 Update `config.py`

```python
PROVIDER_CONFIGS = {
    "limitless": {
        "base_url": "https://api.limitless.exchange",
        "api_key_prefix": "lmts_",
    },
    "polymarket": {
        "clob_url": "https://clob.polymarket.com",
        "data_url": "https://data-api.polymarket.com",
        "api_key_prefix": "poly_",
    },
    "kalshi": {
        "base_url": "https://api.elections.kalshi.com/trade-api/v2",
        "api_key_prefix": "kalshi_",
    },
    "manifold": {
        "base_url": "https://api.manifold.markets/v0",
        "api_key_prefix": "manifold_",
    },
}
```

### 6.2 Update `utils/auth.py`

- Support multiple API key formats
- Auto-detect provider from key prefix
- Provider-specific header generation (Kalshi RSA signing, Polymarket EIP-712, etc.)

### 6.3 Update `.env.example`

```
LIMITLESS_API_KEY=lmts_your_key_here
POLYMARKET_API_KEY=poly_your_key_here
KALSHI_API_KEY=kalshi_your_key_here
MANIFOLD_API_KEY=manifold_your_key_here
```

---

## Phase 7: MCP Server & API Updates

### 7.1 Update MCP `fetch_trades` tool

```python
@tool("fetch_trades")
async def fetch_trades(provider: str = "auto", api_key: str = "", page_limit: int = 100):
    """Fetch trades from a prediction market. Provider auto-detected from API key prefix."""
    if provider == "auto":
        detected = ProviderRegistry.detect(api_key)
    else:
        detected = ProviderRegistry.get(provider)

    trades = detected.fetch_trades(api_key, page_limit)
    session.trades.extend(trades)
    session.filtered_trades = list(session.trades)
```

### 7.2 Add `merge_trades` MCP tool

Allow loading trades from multiple providers into the same session for cross-market analysis.

### 7.3 Update `SessionState`

```python
@dataclass
class SessionState:
    trades: List[Trade]
    filtered_trades: List[Trade]
    active_filters: Dict[str, Any]
    sources: List[str]  # Changed from single source to list
```

### 7.4 Update FastAPI routes

- `POST /api/trades/fetch` — accept `provider` parameter
- `GET /api/providers` — list available providers and their status

---

## Phase 8: File Import Support

Each provider should support CSV/JSON file imports for users who export from the platform UI:

| Provider | Export Formats | Notes |
|----------|---------------|-------|
| Polymarket | CSV (trade history export) | Columns: Market, Side, Price, Size, Timestamp |
| Kalshi | CSV (settlement/fill history) | Columns: Ticker, Action, Side, Price, Count, Timestamp |
| Manifold | JSON (API dump) | Same format as API response |
| Limitless | JSON (existing support) | Already implemented |

Add format auto-detection in `load_trades()` — detect provider from column names/field patterns.

---

## Phase 9: Cross-Market Analysis Features

### 9.1 Portfolio-level metrics across markets

- Aggregate PnL across all providers
- Per-provider breakdowns in summaries
- Currency normalization (MANA → separate from USD/USDC)

### 9.2 Market comparison tools

- Compare performance across providers
- Identify arbitrage-like patterns (same event on multiple markets)
- Cross-market correlation analysis

---

## Implementation Order

| Priority | Phase | Effort | Description |
|----------|-------|--------|-------------|
| 1 | Phase 1 | Medium | Provider abstraction layer (unblocks everything) |
| 2 | Phase 5.1-5.2 | Small | Add `source`/`currency` to Trade model |
| 3 | Phase 4 | Small | Manifold provider (easiest API, good for testing pattern) |
| 4 | Phase 3 | Medium | Kalshi provider (RSA auth, PnL computation needed) |
| 5 | Phase 2 | Medium | Polymarket provider (EIP-712 auth complexity) |
| 6 | Phase 6 | Small | Config & auth updates |
| 7 | Phase 7 | Medium | MCP & API integration |
| 8 | Phase 8 | Small | File import auto-detection |
| 9 | Phase 9 | Large | Cross-market analysis features |

---

## New Files Summary

```
prediction_analyzer/providers/
├── __init__.py
├── base.py              # MarketProvider ABC + ProviderRegistry
├── limitless.py         # Existing Limitless Exchange (refactored)
├── polymarket.py        # Polymarket CLOB + Data API
├── kalshi.py            # Kalshi v2 API
├── manifold.py          # Manifold Markets API
└── pnl_calculator.py    # PnL computation for providers that don't supply it
```

## Modified Files Summary

```
prediction_analyzer/
├── trade_loader.py      # Add source/currency fields, auto-detect provider from file format
├── config.py            # Add PROVIDER_CONFIGS dict
├── utils/auth.py        # Multi-provider auth support
├── utils/data.py        # Delegate to provider, keep backward compat
├── api/schemas/trade.py # Add source/currency to schemas
├── api/models/trade.py  # Add source/currency columns
├── api/routers/trades.py # Add provider parameter to fetch endpoint
prediction_mcp/
├── tools/data_tools.py  # Update fetch_trades, add merge_trades
├── state.py             # sources list instead of single source
.env.example             # Add new API key placeholders
```
