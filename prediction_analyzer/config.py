# prediction_analyzer/config.py
"""
Configuration constants for the prediction analyzer
"""

# API Configuration
API_BASE_URL = "https://api.limitless.exchange"
DEFAULT_TRADE_FILE = "limitless_trades.json"

# Chart Styling
STYLES = {
    ("Buy", "YES"):   ("#008f00", "x", "Buy YES"),   # strong green
    ("Sell", "YES"):  ("#00c800", "o", "Sell YES"),  # vivid lime
    ("Buy", "NO"):    ("#d000d0", "x", "Buy NO"),    # strong magenta
    ("Sell", "NO"):   ("#d40000", "o", "Sell NO")    # strong red
}

# Analysis Parameters
PRICE_RESOLUTION_THRESHOLD = 0.5
