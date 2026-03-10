# prediction_analyzer/config.py
"""
Configuration constants for the prediction analyzer
"""

# API Configuration (legacy — kept for backward compat)
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
        "api_key_prefix": "0x",
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

# Chart Styling - includes all trade type variants
STYLES = {
    # Standard Buy/Sell
    ("Buy", "YES"):         ("#008f00", "x", "Buy YES"),   # strong green
    ("Sell", "YES"):        ("#00c800", "o", "Sell YES"),  # vivid lime
    ("Buy", "NO"):          ("#d000d0", "x", "Buy NO"),    # strong magenta
    ("Sell", "NO"):         ("#d40000", "o", "Sell NO"),   # strong red
    # Market orders
    ("Market Buy", "YES"):  ("#008f00", "x", "Buy YES"),   # same as Buy
    ("Market Sell", "YES"): ("#00c800", "o", "Sell YES"),  # same as Sell
    ("Market Buy", "NO"):   ("#d000d0", "x", "Buy NO"),
    ("Market Sell", "NO"):  ("#d40000", "o", "Sell NO"),
    # Limit orders
    ("Limit Buy", "YES"):   ("#008f00", "^", "Limit Buy YES"),
    ("Limit Sell", "YES"):  ("#00c800", "v", "Limit Sell YES"),
    ("Limit Buy", "NO"):    ("#d000d0", "^", "Limit Buy NO"),
    ("Limit Sell", "NO"):   ("#d40000", "v", "Limit Sell NO"),
}


def get_trade_style(trade_type: str, side: str) -> tuple:
    """
    Get the style for a trade, normalizing the trade type.

    Args:
        trade_type: The trade type (Buy, Sell, Market Buy, etc.)
        side: The side (YES, NO)

    Returns:
        Tuple of (color, marker, label)
    """
    key = (trade_type, side)
    if key in STYLES:
        return STYLES[key]

    # Normalize trade type - extract base type
    base_type = "Buy" if "Buy" in trade_type else ("Sell" if "Sell" in trade_type else "Buy")
    normalized_key = (base_type, side)

    return STYLES.get(normalized_key, ("#808080", "o", f"{trade_type} {side}"))


# Analysis Parameters
PRICE_RESOLUTION_THRESHOLD = 0.85
