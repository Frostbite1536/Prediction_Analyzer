# Prediction Analyzer Tutorial

A step-by-step guide to analyzing your prediction market trades across Limitless Exchange, Polymarket, Kalshi, and Manifold Markets.

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
12. [Using the MCP Server](#12-using-the-mcp-server)
13. [Tips for Traders](#13-tips-for-traders)

---

## 1. Getting Started

### Prerequisites

- Python 3.8 or higher
- An account on one or more prediction market platforms

### Supported Platforms

| Platform | What You Need | Currency |
|----------|---------------|----------|
| Limitless Exchange | API key (`lmts_...`) | USDC |
| Polymarket | Wallet address (`0x...`) | USDC |
| Kalshi | RSA key pair | USD |
| Manifold Markets | API key (`manifold_...`) | MANA |

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

You should see the full list of CLI options including the `--provider` flag. If you get import errors, run `pip install -r requirements.txt` again.

---

## 2. Setting Up API Access

Prediction Analyzer connects to multiple prediction market APIs. Set up credentials for the platforms you use.

### Limitless Exchange

1. Go to [limitless.exchange](https://limitless.exchange)
2. Connect your wallet and log in
3. Click your profile icon (top right)
4. Select **Api keys**
5. Click **Generate** to create a new key
6. Copy the key -- it starts with `lmts_`

```bash
export LIMITLESS_API_KEY="lmts_your_key_here"
```

### Polymarket

Polymarket uses a public Data API that only requires your wallet address:

```bash
export POLYMARKET_WALLET="0xYourEthereumWalletAddress"
```

No API key generation is needed -- just use the wallet address you trade with.

### Kalshi

Kalshi uses RSA key pair authentication with per-request RSA-PSS signing:

1. Go to [kalshi.com](https://kalshi.com) > Settings > API Keys
2. Generate an API key (you'll get a Key ID and a private key PEM file)
3. Save the private key file securely

```bash
export KALSHI_API_KEY_ID="your_key_id"
export KALSHI_PRIVATE_KEY_PATH="/path/to/kalshi_private_key.pem"
```

When using the CLI, pass both as a combined credential:
```bash
python run.py --fetch --provider kalshi --key "kalshi_KEY_ID:/path/to/key.pem"
```

### Manifold Markets

1. Go to [manifold.markets](https://manifold.markets)
2. Navigate to Profile > API Key
3. Copy your key

```bash
export MANIFOLD_API_KEY="manifold_your_key_here"
```

### Using a .env File (Recommended)

For persistence, copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```
LIMITLESS_API_KEY=lmts_your_key_here
POLYMARKET_WALLET=0xYourWalletAddress
KALSHI_API_KEY_ID=your_key_id
KALSHI_PRIVATE_KEY_PATH=kalshi_private_key.pem
MANIFOLD_API_KEY=manifold_your_key_here
```

### Security Notes

- Never commit API keys or private keys to version control
- Treat API keys like passwords -- rotate them periodically
- The `.gitignore` file already excludes `.env` files and `.pem` files
- Kalshi private keys should have restricted file permissions (`chmod 600`)

---

## 3. Loading Your Trades

### Method 1: Fetch from API (Recommended)

```bash
# Limitless (auto-detected from lmts_ prefix)
python run.py --fetch --key "lmts_your_key_here"

# Polymarket
python run.py --fetch --provider polymarket --key "0xYourWallet"

# Kalshi
python run.py --fetch --provider kalshi --key "kalshi_KEY_ID:key.pem"

# Manifold
python run.py --fetch --provider manifold --key "manifold_your_key"

# Auto-detect provider from key format
python run.py --fetch --key "lmts_your_key_here"
```

### Method 2: Load from a File

If you already have trade data exported:

```bash
# JSON format (auto-detects provider from field signatures)
python run.py --file my_trades.json

# CSV format
python run.py --file my_trades.csv

# Excel format
python run.py --file my_trades.xlsx
```

The analyzer auto-detects the provider format from file contents. You can load files from any supported platform without specifying the provider.

### Trade Data Formats

The analyzer understands trade data from all four platforms. Here are examples:

**Limitless Exchange (JSON):**
```json
[
  {
    "market": {"title": "Will Bitcoin reach $100k?", "slug": "btc-100k"},
    "timestamp": 1704067200,
    "strategy": "Buy",
    "outcomeIndex": 0,
    "outcomeTokenAmount": 100,
    "collateralAmount": 50,
    "pnl": 0
  }
]
```

**Polymarket (JSON):**
```json
[
  {
    "market": "Will ETH hit $5k?",
    "asset": "21742633143463906290569050155826241533067272736897614950488156847949938836455",
    "side": "BUY",
    "size": "10.5",
    "price": "0.65",
    "timestamp": "2024-03-15T14:30:00Z"
  }
]
```

**Kalshi (JSON):**
```json
[
  {
    "ticker": "KXBTC-24DEC31-T100000",
    "action": "buy",
    "yes_price": 65,
    "count": 10,
    "created_time": "2024-03-15T14:30:00Z"
  }
]
```

**Manifold (JSON):**
```json
[
  {
    "contractId": "abc123",
    "outcome": "YES",
    "amount": 50,
    "probBefore": 0.40,
    "probAfter": 0.45,
    "createdTime": 1710510600000
  }
]
```

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
- **Provider dropdown** - Select: auto, limitless, polymarket, kalshi, manifold
- **API Key / Wallet field** - Paste your credential here
- **Load from API** - Download trades using the selected provider
- **Load Trades File** - Browse for a local file (auto-detects format)
- **Global Summary** - Jump to the summary view
- **Generate Dashboard** - Create a multi-market overview
- **Export CSV / Export Excel** - Save your data

#### Tab 1: Global Summary
Shows aggregate statistics across all your trades:
- Total trades, total PnL, average PnL per trade
- Win/loss count and win rate
- Total invested, total returned, ROI percentage
- Per-provider breakdown (when trades from multiple providers are loaded)

#### Tab 2: Market Analysis
- Lists all markets you've traded (with source provider shown)
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

1. Select **polymarket** from the provider dropdown
2. Paste your wallet address and click **Load from API**
3. Check the **Global Summary** tab for your overall performance
4. Go to **Market Analysis** > select a market > click **Pro Chart**
5. Use **Filters** to focus on winning trades (`Min PnL: 0`)
6. Export filtered results via **Export CSV**

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
Loaded 150 trades from limitless, polymarket

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

# Fetch from Polymarket + analyze
python run.py --fetch --provider polymarket --key "0x..." --global --dashboard

# Advanced metrics (Sharpe ratio, drawdowns, streaks)
python run.py --file trades.json --metrics

# Filter + export
python run.py --file trades.json \
    --start-date 2024-06-01 \
    --end-date 2024-12-31 \
    --min-pnl -50 \
    --export filtered.csv
```

### All CLI Options

| Flag | Description |
|------|-------------|
| `--file FILE` | Load trades from JSON/CSV/XLSX file (auto-detects provider) |
| `--fetch` | Fetch trades from prediction market API |
| `--key KEY` | API key or credential (format depends on provider) |
| `--provider PROV` | Provider: `auto`, `limitless`, `polymarket`, `kalshi`, `manifold` |
| `--market SLUG` | Analyze a specific market by slug |
| `--global` | Show global PnL summary |
| `--chart TYPE` | Chart type: `simple`, `pro`, or `enhanced` |
| `--dashboard` | Generate multi-market dashboard |
| `--metrics` | Show advanced trading metrics |
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

When trades from multiple providers are loaded, you'll also see per-currency and per-source breakdowns. **Importantly, play-money currencies (MANA from Manifold) are never mixed into the real-money (USD/USDC) totals** -- they appear in a separate section:

```
PNL BY CURRENCY:
  MANA       42 trades  PnL: M$1,250.00  Win Rate: 62.5%
  USD        23 trades  PnL:    $185.40  Win Rate: 55.0%
  USDC       85 trades  PnL:    $342.50  Win Rate: 58.0%
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

---

## 7. Working with Filters

Filters let you slice your data to find patterns.

### Date Range Filtering

```bash
python run.py --file trades.json --start-date 2024-07-01 --end-date 2024-09-30 --global
```

### Trade Type Filtering

```bash
# Only buy trades
python run.py --file trades.json --type Buy --global

# Only sell trades
python run.py --file trades.json --type Sell --global
```

### PnL Filtering

```bash
# Only profitable trades
python run.py --file trades.json --min-pnl 0 --global

# Big winners (> $50 profit)
python run.py --file trades.json --min-pnl 50 --global

# Big losers (> $50 loss)
python run.py --file trades.json --max-pnl -50 --global
```

### Combining Filters

```bash
# Profitable buy trades in Q3 2024
python run.py --file trades.json \
    --start-date 2024-07-01 \
    --end-date 2024-09-30 \
    --type Buy \
    --min-pnl 0 \
    --global
```

### Source Filtering (Python API)

```python
from prediction_analyzer.trade_filter import filter_trades_by_source

# Only Polymarket trades
poly_trades = filter_trades_by_source(trades, "polymarket")
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

### Multi-Market Dashboard

Best for: Portfolio overview across all markets and providers.

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

Exported CSV includes `source` and `currency` columns for multi-provider data.

### Excel Export

```bash
python run.py --file trades.json --export my_trades.xlsx
```

### Filtered Export

```bash
# Export only profitable trades to Excel
python run.py --file trades.json --min-pnl 0 --export winners.xlsx
```

### Text Report

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

# Load trades (auto-detects provider format from file contents)
trades = load_trades("trades.json")

# Get summary
summary = calculate_global_pnl_summary(trades)
print(f"Total PnL: ${summary['total_pnl']:.2f}")
print(f"Win Rate: {summary['win_rate']:.1f}%")
print(f"ROI: {summary['roi']:.2f}%")
```

### Fetch Trades from Any Provider

```python
from prediction_analyzer.providers import ProviderRegistry

# List available providers
print(ProviderRegistry.names())  # ['limitless', 'polymarket', 'kalshi', 'manifold']

# Fetch from a specific provider
provider = ProviderRegistry.get("polymarket")
trades = provider.fetch_trades("0xYourWalletAddress")

# Auto-detect provider from key
provider = ProviderRegistry.detect_from_key("lmts_your_key")
trades = provider.fetch_trades("lmts_your_key")

# Apply FIFO PnL computation (for providers without native PnL)
from prediction_analyzer.providers.pnl_calculator import compute_realized_pnl
trades = compute_realized_pnl(trades)
```

### Legacy Limitless Fetch

```python
from prediction_analyzer.utils.auth import get_api_key, get_auth_headers
from prediction_analyzer.utils.data import fetch_trade_history

# API key from environment or explicit
api_key = get_api_key()  # reads LIMITLESS_API_KEY env var
raw_trades = fetch_trade_history(api_key)
```

### Market-Specific Analysis

```python
from prediction_analyzer.trade_filter import (
    filter_trades_by_market_slug,
    filter_trades_by_source,
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

# Filter by provider source
poly_trades = filter_trades_by_source(trades, "polymarket")
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
| POST | `/api/v1/auth/signup` | Create an account |
| POST | `/api/v1/auth/login` | Get JWT token |
| GET | `/api/v1/trades/` | List your trades |
| GET | `/api/v1/trades/?source=polymarket` | Filter by provider |
| GET | `/api/v1/trades/providers` | List available providers (auth required) |
| POST | `/api/v1/trades/upload` | Upload trade file (auto-detects format, 10 MB limit) |
| GET | `/api/v1/trades/export/csv` | Export trades as CSV |
| GET | `/api/v1/trades/export/json` | Export trades as JSON |
| GET | `/api/v1/analysis/global-summary` | Global PnL |
| GET | `/api/v1/analysis/market/{slug}` | Market summary |
| GET | `/api/v1/charts/{type}/{slug}` | Generate chart |

### Authentication

The web API uses its own JWT-based auth (separate from prediction market API keys).

**Password requirements:** minimum 8 characters, maximum 100 characters.

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "username": "trader", "password": "secure1234"}'

# Login (JSON endpoint)
curl -X POST http://localhost:8000/api/v1/auth/login/json \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "secure1234"}'
```

**Production deployment:** Set the `SECRET_KEY` environment variable to a strong random string. In development, a random ephemeral key is auto-generated on startup.

---

## 12. Using the MCP Server

The MCP (Model Context Protocol) server lets you use Prediction Analyzer with Claude Code or Claude Desktop.

### Starting the MCP Server

```bash
# stdio transport (for Claude Code / Claude Desktop)
python -m prediction_mcp

# HTTP/SSE transport (for web agents)
python -m prediction_mcp --sse --port 8000

# With SQLite session persistence
python -m prediction_mcp --persist session.db
```

### Available MCP Tools (18 total)

| Tool | Description |
|------|-------------|
| `load_trades` | Load trades from file (auto-detects provider format) |
| `fetch_trades` | Fetch from API (supports all 4 providers with auto-detection) |
| `list_markets` | List markets with trade counts and source providers |
| `get_trade_details` | Paginated trade details with sorting |
| `get_global_summary` | Global PnL analysis with optional filters |
| `get_market_summary` | Per-market PnL analysis |
| `get_advanced_metrics` | Risk-adjusted metrics (Sharpe, Sortino, drawdown) |
| `get_market_breakdown` | PnL breakdown by market |
| `get_provider_breakdown` | Cross-provider analysis |
| `filter_trades` | Apply date/type/PnL filters (use `clear=true` to reset) |
| `generate_chart` | Create market charts (simple/pro/enhanced) |
| `generate_dashboard` | Multi-market PnL dashboard |
| `export_trades` | Export to CSV, Excel, or JSON |
| `get_open_positions` | Current positions with unrealized PnL |
| `get_concentration_risk` | Portfolio concentration (HHI index) |
| `get_drawdown_analysis` | Drawdown periods and recovery analysis |
| `compare_periods` | Compare performance between two time periods |
| `get_tax_report` | Capital gains/losses with FIFO/LIFO/average cost basis |

### Claude Desktop Configuration

Add to your Claude Desktop MCP settings:

```json
{
  "mcpServers": {
    "prediction-analyzer": {
      "command": "python",
      "args": ["-m", "prediction_mcp"],
      "cwd": "/path/to/Prediction_Analyzer"
    }
  }
}
```

---

## 13. Tips for Traders

### Analyze Your Edge

1. **Check win rate by market type** - Are you better at crypto, politics, or sports predictions?
2. **Compare buy vs sell performance** - Filter by type to see if your entries or exits are the problem.
3. **Look at time patterns** - Filter by date ranges to see if you perform better at certain times.
4. **Compare across providers** - Use `--metrics` to see if you perform differently on different platforms.

### Common Patterns to Watch

- **High win rate but low ROI** - You're winning often but with small positions. Consider sizing up on high-conviction trades.
- **Low win rate but positive PnL** - Your winners are bigger than your losers. Keep cutting losses early.
- **Declining PnL over time** - Use date filters to spot when performance started dropping.
- **Provider-specific edge** - Some traders perform better on certain platforms due to liquidity or market selection.

### Workflow Suggestion

1. Fetch your latest trades: `python run.py --fetch --key "lmts_..."`
2. Check global summary: `python run.py --file limitless_trades.json --global`
3. Generate dashboard: `python run.py --file limitless_trades.json --dashboard`
4. Drill into underperforming markets with pro charts
5. Export filtered data for external analysis if needed

### Multi-Provider Workflow

1. Fetch from each platform you use
2. Load all trade files together for cross-platform analysis
3. Use the provider breakdown to compare performance across platforms
4. Focus your capital on the platform where your edge is strongest

### Keeping Data Fresh

Re-fetch periodically to include new trades:

```bash
export LIMITLESS_API_KEY="lmts_your_key"
python run.py --fetch --global --dashboard
```

This downloads the latest data and immediately shows your updated stats.

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
