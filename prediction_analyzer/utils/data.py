# prediction_analyzer/utils/data.py
"""
Data fetching utilities for Limitless Exchange API.
"""

import logging
import requests
from typing import List
from ..config import API_BASE_URL
from .auth import get_auth_headers

logger = logging.getLogger(__name__)


def fetch_trade_history(api_key: str, page_limit: int = 100) -> List[dict]:
    """Fetch trade history from the Limitless Exchange API."""
    all_trades = []
    page = 1
    headers = get_auth_headers(api_key)

    logger.info("Downloading trade history...")

    while True:
        params = {"page": page, "limit": page_limit}

        try:
            resp = requests.get(
                f"{API_BASE_URL}/portfolio/history", params=params, headers=headers, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("Error fetching page %d: %s", page, exc)
            break

        trades = data.get("data", [])
        if not trades:
            break

        all_trades.extend(trades)
        logger.info("Downloaded page %d (%d trades so far)", page, len(all_trades))

        total_count = data.get("totalCount", 0)
        if len(all_trades) >= total_count:
            break
        page += 1

    logger.info("Downloaded %d total trades", len(all_trades))
    return all_trades


def fetch_market_details(market_slug: str):
    """Fetch live market details from API (public endpoint, no auth required)."""
    url = f"{API_BASE_URL}/markets/{market_slug}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException as exc:
        logger.debug("Failed to fetch market details for %s: %s", market_slug, exc)
    return None
