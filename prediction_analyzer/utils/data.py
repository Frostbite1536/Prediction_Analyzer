# prediction_analyzer/utils/data.py
"""
Data fetching utilities
"""
import requests
from typing import List
from ..config import API_BASE_URL

def fetch_trade_history(session_cookie: str, page_limit: int = 100) -> List[dict]:
    """
    Fetch trade history from API

    Args:
        session_cookie: Session cookie from authentication
        page_limit: Number of trades per page

    Returns:
        List of trade dictionaries
    """
    all_trades = []
    page = 1

    print("⏳ Downloading trade history...")

    while True:
        params = {"page": page, "limit": page_limit}
        headers = {'Cookie': f'limitless_session={session_cookie}'}

        try:
            resp = requests.get(
                f"{API_BASE_URL}/portfolio/history",
                params=params,
                headers=headers,
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            print(f"❌ Error fetching page {page}: {exc}")
            break

        trades = data.get("data", [])
        if not trades:
            break

        all_trades.extend(trades)
        print(f"   Downloaded page {page} ({len(all_trades)} trades so far)")

        total_count = data.get("totalCount", 0)
        if len(all_trades) >= total_count:
            break
        page += 1

    print(f"✅ Downloaded {len(all_trades)} total trades")
    return all_trades

def fetch_market_details(market_slug: str):
    """
    Fetch live market details from API

    Args:
        market_slug: Market slug identifier

    Returns:
        Market data dictionary or None on error
    """
    url = f"{API_BASE_URL}/markets/{market_slug}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None
