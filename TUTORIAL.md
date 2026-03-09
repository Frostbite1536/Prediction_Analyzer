# Prediction Analyzer Tutorial

A step-by-step guide to analyzing your Limitless Exchange prediction market trades.

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Setting Up API Access](#2-setting-up-api-access)
3. [Loading Your Trades](#3-loading-your-trades)
4. [Understanding the GUI](#4-understanding-the-gui)
5. [Using the CLI](#5-using-the-cli)
6. [Analyzing Your Performance](#6-analyzing-your-performance)
7. [Working with Filters](#7-working-with-filters)
8. [Generating Charts](#8-generating-charts)
9. [Exporting Data](#9-exporting-data)
10. [Using the Python API](#10-using-the-python-api)
11. [Using the Web API](#11-using-the-web-api)
12. [Tips for Traders](#12-tips-for-traders)

---

## 1. Getting Started

### Prerequisites

- Python 3.8 or higher
- A Limitless Exchange account (for live data fetching)

### Installation

```bash
# Clone the repository
git clone https://github.com/Frostbite1536/Prediction_Analyzer.git
cd Prediction_Analyzer

# Install dependencies
pip install -r requirements.txt
```

For detailed installation instructions, see [INSTALL.md](INSTALL.md).

### Verify Installation

```bash
python run.py --help
```

You should see the full list of CLI options. If you get import errors, run `pip install -r requirements.txt` again.

---

## 2. Setting Up API Access

Prediction Analyzer connects to the Limitless Exchange API to download your trade history. Authentication uses API keys.

### Step 1: Generate an API Key

1. Go to [limitless.exchange](https://limitless.exchange)
2. Connect your wallet and log in
3. Click your profile icon (top right)
4. Select **Api keys**
5. Click **Generate** to create a new key
6. Copy the key - it starts with `lmts_`

### Step 2: Configure Your Key

**Option A: Environment variable (recommended)**

```bash
# Linux/macOS
export LIMITLESS_API_KEY="lmts_your_key_here"

# Windows (Command Prompt)
set LIMITLESS_API_KEY=lmts_your_key_here

# Windows (PowerShell)
$env:LIMITLESS_API_KEY = "lmts_your_key_here"
```

For persistence, add it to a `.env` file (see `.env.example`):
```
LIMITLESS_API_KEY=lmts_your_key_here
```

**Option B: Pass directly on the command line**

```bash
python run.py --fetch --key "lmts_your_key_here"
```

**Option C: Enter in the GUI**

Paste the key into the "API Key" field in the GUI's Quick Actions panel.

### Security Notes

- Never commit your API key to version control
- API keys have full account access - treat them like passwords
- Rotate keys periodically via the Limitless profile page
- The `.gitignore` file already excludes `.env` files

---

## 3. Loading Your Trades

There are two ways to get your trade data into the analyzer.

### Method 1: Fetch from the Limitless API (Recommended)

```bash
# Using environment variable
export LIMITLESS_API_KEY="lmts_your_key_here"
python run.py --fetch

# Or pass key directly
python run.py --fetch --key "lmts_your_key_here"
```

This downloads all your trade history and saves it to `limitless_trades.json` for future use.

### Method 2: Load from a File

If you already have trade data exported:

```bash
# JSON format
python run.py --file my_trades.json

# CSV format
python run.py --file my_trades.csv

# Excel format
python run.py --file my_trades.xlsx
```

### Sample Data

A sample trade file is included for testing:

```bash
python run.py --file data/example_trades.json
```

### Trade Data Format

The analyzer understands trade data in this format (JSON example):

```json
[
  {
    "market": {
      "title": "Will Bitcoin reach $100k by end of 2024?",
      "slug": "btc-100k-2024"
    },
    "timestamp": 1704067200,
    "strategy": "Buy",
    "outcomeIndex": 0,
    "outcomeTokenAmount": 100,
    "collateralAmount": 50,
    "pnl": 0,
    "blockTimestamp": 1704067200
  }
]
```

Key fields:
- `market.title` / `market.slug` - Market identification
- `strategy` - "Buy" or "Sell" (also accepts "Market Buy", "Limit Sell", etc.)
- `outcomeIndex` - 0 = YES, 1 = NO
- `outcomeTokenAmount` - Number of shares (may be in micro-units from API)
- `collateralAmount` - Cost in USDC (may be in micro-units from API)
- `pnl` - Profit/loss for the trade

---

## 4. Understanding the GUI

Launch the GUI:

```bash
python run_gui.py

# Windows: double-click run_gui.bat
```

### Layout Overview

The GUI has four main tabs:

#### Quick Actions Panel (top)
- **API Key field** - Paste your `lmts_` key here
- **Load from API** - Download trades using the API key
- **Load Trades File** - Browse for a local file
- **Global Summary** - Jump to the summary view
- **Generate Dashboard** - Create a multi-market overview
- **Export CSV / Export Excel** - Save your data

#### Tab 1: Global Summary
Shows aggregate statistics across all your trades:
- Total trades, total PnL, average PnL per trade
- Win/loss count and win rate
- Total invested, total returned, ROI percentage

#### Tab 2: Market Analysis
- Lists all markets you've traded
- Select a market to see its individual PnL summary
- Generate Simple, Pro, or Enhanced charts per market

#### Tab 3: Filters
Apply filters to narrow your analysis:
- **Date range** - Start and end dates (YYYY-MM-DD format)
- **Trade type** - Buy only, Sell only, or both
- **PnL range** - Min/max PnL thresholds

Filters update the Global Summary and Market Analysis tabs automatically.

#### Tab 4: Charts
Information about chart types and a button to generate the multi-market dashboard.

### GUI Workflow Example

1. Paste your API key and click **Load from API**
2. Check the **Global Summary** tab for your overall performance
3. Go to **Market Analysis** -> select a market -> click **Pro Chart**
4. Use **Filters** to focus on winning trades (`Min PnL: 0`)
5. Export filtered results via **Export CSV**

---

## 5. Using the CLI

The CLI offers two modes: command-line flags for scripting, and an interactive menu for exploration.

### Interactive Mode

Just load your trades without specifying an action:

```bash
python run.py --file trades.json
```

This opens the interactive menu:
```
=== Prediction Market Trade Analyzer ===
Loaded 150 trades across 12 markets

[1] Global PnL Summary
[2] Analyze Specific Market
[3] Export Data
[4] Generate Report
[Q] Quit

Select: _
```

### Command-Line Mode

For scripting and automation:

```bash
# Global summary
python run.py --file trades.json --global

# Analyze a specific market
python run.py --file trades.json --market "btc-100k-2024" --chart pro

# Generate dashboard across all markets
python run.py --file trades.json --dashboard

# Filter + export
python run.py --file trades.json \
    --start-date 2024-06-01 \
    --end-date 2024-12-31 \
    --min-pnl -50 \
    --export filtered.csv

# Generate a text report
python run.py --file trades.json --report

# Fetch + analyze in one command
python run.py --fetch --key "lmts_..." --global --dashboard
```

### All CLI Options

| Flag | Description |
|------|-------------|
| `--file FILE` | Load trades from JSON/CSV/XLSX file |
| `--fetch` | Fetch trades from Limitless Exchange API |
| `--key KEY` | API key (`lmts_...`) or set `LIMITLESS_API_KEY` env var |
| `--market SLUG` | Analyze a specific market by slug |
| `--global` | Show global PnL summary |
| `--chart TYPE` | Chart type: `simple`, `pro`, or `enhanced` |
| `--dashboard` | Generate multi-market dashboard |
| `--start-date DATE` | Filter: start date (YYYY-MM-DD) |
| `--end-date DATE` | Filter: end date (YYYY-MM-DD) |
| `--type TYPE` | Filter: `Buy` or `Sell` |
| `--min-pnl N` | Filter: minimum PnL |
| `--max-pnl N` | Filter: maximum PnL |
| `--export FILE` | Export filtered trades to CSV or XLSX |
| `--report` | Generate detailed text report |
| `--no-interactive` | Skip interactive menu (batch mode) |

---

## 6. Analyzing Your Performance

### Global PnL Summary

The global summary gives you a bird's eye view:

```
============================================================
GLOBAL PnL SUMMARY
============================================================

Total Trades: 150
Total PnL: $342.50
Average PnL per Trade: $2.28

Winning Trades: 87
Losing Trades: 63
Win Rate: 58.0%

Total Invested: $5,230.00
Total Returned: $5,572.50
ROI: 6.55%
============================================================
```

**Key metrics to watch:**
- **Win Rate** - Percentage of trades that were profitable. Above 50% is good for binary prediction markets.
- **ROI** - Return on investment. Measures efficiency of your capital.
- **Average PnL per Trade** - Positive means you're profitable on average.

### Per-Market Analysis

Drill into individual markets to understand where you're making or losing money:

```bash
python run.py --file trades.json --market "btc-100k-2024"
```

This shows:
- Market-specific PnL breakdown
- Your trade history in that market
- Inferred market outcome (if resolved)

---

## 7. Working with Filters

Filters let you slice your data to find patterns.

### Date Range Filtering

Focus on a specific time period:

```bash
python run.py --file trades.json --start-date 2024-07-01 --end-date 2024-09-30 --global
```

### Trade Type Filtering

Analyze only your buys or sells:

```bash
# Only buy trades
python run.py --file trades.json --type Buy --global

# Only sell trades
python run.py --file trades.json --type Sell --global
```

### PnL Filtering

Find your best and worst trades:

```bash
# Only profitable trades
python run.py --file trades.json --min-pnl 0 --global

# Only losses
python run.py --file trades.json --max-pnl 0 --global

# Big winners (> $50 profit)
python run.py --file trades.json --min-pnl 50 --global

# Big losers (> $50 loss)
python run.py --file trades.json --max-pnl -50 --global
```

### Combining Filters

Stack filters for precise analysis:

```bash
# Profitable buy trades in Q3 2024
python run.py --file trades.json \
    --start-date 2024-07-01 \
    --end-date 2024-09-30 \
    --type Buy \
    --min-pnl 0 \
    --global
```

---

## 8. Generating Charts

Four chart types are available, each suited to different analysis needs.

### Simple Chart (Matplotlib)

Best for: Quick static screenshots, presentations.

```bash
python run.py --file trades.json --market "btc-100k-2024" --chart simple
```

Two-panel view showing:
- **Top panel**: Trade prices over time with buy/sell markers
- **Bottom panel**: Net exposure (position size) over time

### Pro Chart (Plotly)

Best for: Interactive exploration, detailed analysis.

```bash
python run.py --file trades.json --market "btc-100k-2024" --chart pro
```

Three-panel interactive HTML chart with:
- Trade prices with color-coded markers
- Cumulative PnL line
- Net exposure tracking
- Hover tooltips with trade details
- Zoom, pan, and screenshot tools

### Enhanced Chart (Battlefield)

Best for: Tactical visualization of trade battles.

```bash
python run.py --file trades.json --market "btc-100k-2024" --chart enhanced
```

Advanced visualization showing position dynamics and P&L progression.

### Multi-Market Dashboard

Best for: Portfolio overview across all markets.

```bash
python run.py --file trades.json --dashboard
```

Generates a Plotly dashboard with:
- PnL per market (bar chart)
- Win rate per market
- Portfolio allocation
- Cumulative PnL over time

---

## 9. Exporting Data

### CSV Export

```bash
python run.py --file trades.json --export my_trades.csv
```

### Excel Export

```bash
python run.py --file trades.json --export my_trades.xlsx
```

### Filtered Export

Combine filters with export:

```bash
# Export only profitable trades to Excel
python run.py --file trades.json --min-pnl 0 --export winners.xlsx
```

### Text Report

Generate a comprehensive text report:

```bash
python run.py --file trades.json --report
```

---

## 10. Using the Python API

For developers and advanced users who want to integrate the analyzer into their own scripts.

### Basic Usage

```python
from prediction_analyzer.trade_loader import load_trades
from prediction_analyzer.pnl import calculate_global_pnl_summary

# Load trades
trades = load_trades("trades.json")

# Get summary
summary = calculate_global_pnl_summary(trades)
print(f"Total PnL: ${summary['total_pnl']:.2f}")
print(f"Win Rate: {summary['win_rate']:.1f}%")
print(f"ROI: {summary['roi']:.2f}%")
```

### Fetch Trades Programmatically

```python
from prediction_analyzer.utils.auth import get_api_key, get_auth_headers
from prediction_analyzer.utils.data import fetch_trade_history

# API key from environment or explicit
api_key = get_api_key()  # reads LIMITLESS_API_KEY env var
# or: api_key = get_api_key("lmts_your_key")

raw_trades = fetch_trade_history(api_key)
```

### Market-Specific Analysis

```python
from prediction_analyzer.trade_filter import (
    filter_trades_by_market_slug,
    get_unique_markets,
    group_trades_by_market
)
from prediction_analyzer.pnl import calculate_market_pnl_summary

# List all markets
markets = get_unique_markets(trades)
for slug, title in markets.items():
    print(f"  {slug}: {title}")

# Analyze one market
market_trades = filter_trades_by_market_slug(trades, "btc-100k-2024")
summary = calculate_market_pnl_summary(market_trades)
print(f"Market PnL: ${summary['total_pnl']:.2f}")
```

### Filtering

```python
from prediction_analyzer.filters import filter_by_date, filter_by_pnl, filter_by_trade_type

# Date filter
recent = filter_by_date(trades, start_date="2024-06-01", end_date="2024-12-31")

# PnL filter
winners = filter_by_pnl(trades, min_pnl=0)

# Type filter
buys_only = filter_by_trade_type(trades, ["Buy"])
```

### Chart Generation

```python
from prediction_analyzer.charts.simple import generate_simple_chart
from prediction_analyzer.charts.pro import generate_pro_chart
from prediction_analyzer.charts.enhanced import generate_enhanced_chart
from prediction_analyzer.charts.global_chart import generate_global_dashboard

# Single market chart
generate_simple_chart(market_trades, "BTC $100k by 2024")
generate_pro_chart(market_trades, "BTC $100k by 2024")

# Multi-market dashboard
trades_by_market = group_trades_by_market(trades)
generate_global_dashboard(trades_by_market)
```

### Data Export

```python
from prediction_analyzer.reporting.report_data import export_to_csv, export_to_excel

export_to_csv(trades, "output.csv")
export_to_excel(trades, "output.xlsx")
```

---

## 11. Using the Web API

Prediction Analyzer includes a FastAPI web application for browser-based access.

### Starting the Server

```bash
python run_api.py
```

The server starts at `http://localhost:8000`. API docs are available at `http://localhost:8000/docs`.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create an account |
| POST | `/api/v1/auth/login` | Get JWT token |
| GET | `/api/v1/trades/` | List your trades |
| POST | `/api/v1/trades/upload` | Upload trade file |
| GET | `/api/v1/analysis/global-summary` | Global PnL |
| GET | `/api/v1/analysis/market/{slug}` | Market summary |
| GET | `/api/v1/charts/{type}/{slug}` | Generate chart |

### Authentication

The web API uses its own JWT-based auth (separate from the Limitless API key):

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "username": "trader", "password": "secure123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "secure123"}'
```

---

## 12. Tips for Traders

### Analyze Your Edge

1. **Check win rate by market type** - Are you better at crypto, politics, or sports predictions?
2. **Compare buy vs sell performance** - Filter by type to see if your entries or exits are the problem.
3. **Look at time patterns** - Filter by date ranges to see if you perform better at certain times.

### Common Patterns to Watch

- **High win rate but low ROI** - You're winning often but with small positions. Consider sizing up on high-conviction trades.
- **Low win rate but positive PnL** - Your winners are bigger than your losers. Keep cutting losses early.
- **Declining PnL over time** - Use date filters to spot when performance started dropping.

### Workflow Suggestion

1. Fetch your latest trades: `python run.py --fetch`
2. Check global summary: `python run.py --file limitless_trades.json --global`
3. Generate dashboard: `python run.py --file limitless_trades.json --dashboard`
4. Drill into underperforming markets with pro charts
5. Export filtered data for external analysis if needed

### Keeping Data Fresh

Re-fetch periodically to include new trades:

```bash
export LIMITLESS_API_KEY="lmts_your_key"
python run.py --fetch --global --dashboard
```

This downloads the latest data and immediately shows your updated stats.
