# prediction_analyzer/trade_loader.py
"""
Trade loading functionality - supports JSON, CSV, XLSX
"""

import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Union, Optional, Dict, Any

import pandas as pd

from .exceptions import TradeLoadError
from .utils.time_utils import parse_timestamp as _parse_timestamp  # noqa: F401
from .utils.export import sanitize_filename as _sanitize_filename  # noqa: F401

logger = logging.getLogger(__name__)

# Sentinel cap for infinite values — used throughout the codebase to replace
# float('inf') with a finite number safe for JSON serialization and display.
INF_CAP = 999999.99


def sanitize_numeric(value: Union[float, Decimal, int]) -> float:
    """Guard against NaN/Infinity in numeric values for JSON serialization."""
    if isinstance(value, float):
        if math.isnan(value):
            return 0.0
        if math.isinf(value):
            return INF_CAP if value > 0 else -INF_CAP
    elif hasattr(value, "is_nan"):
        if value.is_nan():
            return 0.0
        if value.is_infinite():
            return INF_CAP if value > 0 else -INF_CAP
        return float(value)
    return float(value)


@dataclass
class Trade:
    """Data class representing a single trade"""

    market: str
    market_slug: str
    timestamp: datetime
    price: float
    shares: float
    cost: float
    type: str  # "Buy" or "Sell"
    side: str  # "YES" or "NO"
    pnl: float = 0.0
    pnl_is_set: bool = False  # True when pnl was explicitly set by provider
    tx_hash: Optional[str] = None
    source: str = "limitless"  # "limitless", "polymarket", "kalshi", "manifold"
    currency: str = "USD"  # "USD", "USDC", "MANA"
    fee: float = 0.0  # Trading fee (available from Kalshi; other providers bundle into cost)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "market": self.market,
            "market_slug": self.market_slug,
            "timestamp": (
                self.timestamp.isoformat()
                if hasattr(self.timestamp, "isoformat")
                else str(self.timestamp)
            ),
            "price": sanitize_numeric(self.price),
            "shares": sanitize_numeric(self.shares),
            "cost": sanitize_numeric(self.cost),
            "type": self.type,
            "side": self.side,
            "pnl": sanitize_numeric(self.pnl),
            "pnl_is_set": self.pnl_is_set,
            "tx_hash": self.tx_hash,
            "source": self.source,
            "currency": self.currency,
            "fee": sanitize_numeric(self.fee),
        }


def load_trades(file_path: str) -> List[Trade]:
    """
    Load trades from JSON, CSV, or XLSX file

    Args:
        file_path: Path to the trade file

    Returns:
        List of Trade objects
    """
    trades = []

    try:
        if file_path.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                raw_trades = json.load(f)
        elif file_path.endswith(".csv"):
            raw_trades = pd.read_csv(file_path).to_dict(orient="records")
        elif file_path.endswith(".xlsx"):
            raw_trades = pd.read_excel(file_path).to_dict(orient="records")
        else:
            raise ValueError("Unsupported file type. Use JSON, CSV, or XLSX.")

        # Auto-detect provider from file format
        try:
            from .providers import ProviderRegistry

            sample = raw_trades[:5] if raw_trades else []
            provider = ProviderRegistry.detect_from_file(sample)
            if provider and provider.name != "limitless":
                logger.info("Auto-detected file format: %s", provider.display_name)
                return [provider.normalize_trade(t) for t in raw_trades]
        except ImportError as exc:
            logger.debug("Provider auto-detection skipped (import): %s", exc)
        except Exception as exc:
            logger.warning("Provider auto-detection failed: %s", exc)

        # Default: Limitless / generic parsing (backward compat)
        for t in raw_trades:
            # Handle both old and new format for market data
            # Also handle null values properly
            market_data = t.get("market")
            if market_data is not None and isinstance(market_data, dict):
                market_title = market_data.get("title") or "Unknown"
                market_slug = market_data.get("slug") or "unknown"
            else:
                # Fallback: use top-level fields or defaults
                market_title = t.get("market") if isinstance(t.get("market"), str) else "Unknown"
                market_slug = t.get("market_slug") or "unknown"

            # Ensure market_title is never None or empty
            if not market_title:
                market_title = "Unknown"
            if not market_slug:
                market_slug = "unknown"

            # Convert from micro-units (USDC uses 6 decimal places)
            # If data comes from API (has collateralAmount), values are in micro-units
            USDC_DECIMALS = 1_000_000
            has_pnl = "pnl" in t and t["pnl"] is not None
            if "collateralAmount" in t:
                # API data - convert from micro-units to regular units
                raw_cost = float(t.get("collateralAmount") or 0) / USDC_DECIMALS
                raw_pnl = float(t.get("pnl") or 0) / USDC_DECIMALS
                raw_shares = float(t.get("outcomeTokenAmount") or 0) / USDC_DECIMALS
            else:
                # File data - already in regular units
                raw_cost = float(t.get("cost") or 0)
                raw_pnl = float(t.get("pnl") or 0)
                raw_shares = float(t.get("shares") or 0)

            # Parse timestamp using robust parser (handles RFC 3339, Unix epoch, etc.)
            raw_timestamp = t.get("timestamp") or t.get("blockTimestamp") or 0
            parsed_timestamp = _parse_timestamp(raw_timestamp)

            # Get trade type with fallback
            trade_type = t.get("type") or t.get("strategy") or "Buy"

            # Get side with proper outcomeIndex handling
            side = t.get("side")
            if not side:
                outcome_index = t.get("outcomeIndex")
                if outcome_index is not None:
                    side = "YES" if outcome_index == 0 else "NO"
                else:
                    side = "YES"  # Default

            trade = Trade(
                market=market_title,
                market_slug=market_slug,
                timestamp=parsed_timestamp,
                price=float(t.get("price") or 0),
                shares=raw_shares,
                cost=raw_cost,
                type=trade_type,
                side=side,
                pnl=raw_pnl,
                pnl_is_set=has_pnl,
                tx_hash=t.get("tx_hash") or t.get("transactionHash"),
            )
            trades.append(trade)

    except Exception as e:
        logger.error("Error loading trades: %s", e)
        raise TradeLoadError(f"Failed to load trades from {file_path}: {e}") from e

    return trades


def save_trades(trades: List[Union[Trade, dict]], file_path: str):
    """Save trades to JSON file"""
    # Handle both Trade objects and raw dictionaries
    trades_dict = []
    for t in trades:
        if isinstance(t, dict):
            trades_dict.append(t)
        else:
            # It's a Trade object, convert using to_dict() for NaN/Inf sanitization
            trades_dict.append(t.to_dict())

    # Convert datetime to string for JSON serialization
    for t in trades_dict:
        if "timestamp" in t and isinstance(t["timestamp"], datetime):
            t["timestamp"] = t["timestamp"].isoformat()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(trades_dict, f, indent=2)
