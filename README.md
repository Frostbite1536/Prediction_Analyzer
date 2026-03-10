# Prediction Analyzer

A complete modular analysis tool for prediction market traders. Analyze past trades, calculate PnL, generate charts, and export reports across multiple prediction market platforms.

## Supported Platforms

| Platform | Currency | Auth Method | API Key Prefix |
|----------|----------|-------------|----------------|
| **Limitless Exchange** | USDC | API key | `lmts_` |
| **Polymarket** | USDC | Wallet address (public API) | `0x` |
| **Kalshi** | USD | RSA key pair (RSA-PSS signing) | `kalshi_` |
| **Manifold Markets** | MANA | API key | `manifold_` |

## Features

### For Everyone
- **Graphical User Interface (GUI)** - Easy-to-use desktop application with provider selection
- **Multi-platform support** - Load and analyze trades from 4 prediction market platforms
- Load trade history from JSON, CSV, or Excel (auto-detects provider format)
- Calculate global and market-specific PnL
- Filter trades by date, type, PnL thresholds, and source provider
- Export reports in multiple formats (CSV, Excel, TXT)
- Interactive CLI menu for easy navigation

### For Novice Traders
- Simple, easy-to-understand charts
- Step-by-step interactive menus
- Clear PnL summaries with per-provider breakdowns
- One-click analysis

### For Professional Traders
- Advanced interactive charts with Plotly
- Multi-market dashboards
- Cross-provider portfolio analysis
- Currency-separated PnL aggregation (real-money USD/USDC vs play-money MANA)
- FIFO PnL computation for providers without native PnL
- MCP server integration for Claude Code / Claude Desktop
- FastAPI web server with JWT authentication
- Command-line interface for automation

## Installation

**For detailed installation instructions, see [INSTALL.md](INSTALL.md)**
**For a step-by-step walkthrough, see [TUTORIAL.md](TUTORIAL.md)**

### Quick Start (3 Easy Steps)

#### Windows Users (Easiest):
1. Download/clone this repository
2. Double-click `install.bat` (or run it from command prompt)
3. Run `python run.py`

#### All Platforms:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the analyzer
python run.py --help
```

The `run.py` script will automatically check for missing dependencies and guide you if anything is missing!

### Full Installation (Optional)

If you want to install as a package and use `prediction-analyzer` command anywhere:

```bash
pip install -e .
```

After installation, you can use the `prediction-analyzer` command directly:
```bash
prediction-analyzer --file your_trades.json
```

## Quick Start

### GUI Mode (Easiest)
The easiest way to use Prediction Analyzer is through the graphical interface:

```bash
# Windows: Just double-click run_gui.bat
# Or run from command line:
python run_gui.py
```

The GUI provides:
- Provider selection dropdown (Limitless, Polymarket, Kalshi, Manifold)
- Point-and-click file loading with auto-format detection
- Visual trade statistics and summaries
- Easy market selection and analysis
- Interactive filters with form controls
- One-click chart generation and export

### Interactive CLI Mode (Terminal-Friendly)
```bash
# Without installation
python run.py --file your_trades.json

# Or with installation
prediction-analyzer --file your_trades.json
```

### Command-Line Mode (Pro Users)
```bash
# Global PnL summary
python run.py --file trades.json --global

# Analyze specific market with pro chart
python run.py --file trades.json --market "ETH-USD" --chart pro

# Multi-market dashboard
python run.py --file trades.json --dashboard

# Filter and export
python run.py --file trades.json \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --type Buy \
    --export filtered_trades.xlsx
```

**Note:** Replace `python run.py` with `prediction-analyzer` if you installed the package.

### Fetch Live Data from Prediction Markets

```bash
# Limitless Exchange
export LIMITLESS_API_KEY="lmts_your_api_key_here"
python run.py --fetch

# Polymarket (uses public Data API with wallet address)
python run.py --fetch --provider polymarket --key "0xYourWalletAddress"

# Kalshi (RSA key pair)
export KALSHI_API_KEY_ID="your_key_id"
export KALSHI_PRIVATE_KEY_PATH="kalshi_private_key.pem"
python run.py --fetch --provider kalshi --key "kalshi_KEY_ID:key.pem"

# Manifold Markets
python run.py --fetch --provider manifold --key "manifold_your_key"

# Auto-detect provider from key format
python run.py --fetch --key "lmts_your_api_key_here"
```

### MCP Server (for Claude Code / Claude Desktop)

```bash
# stdio transport (default, for Claude Code)
python -m prediction_mcp

# HTTP/SSE transport (for web agents)
python -m prediction_mcp --sse --port 8000

# With SQLite session persistence
python -m prediction_mcp --persist session.db
```

## Usage Examples

### Example 1: Multi-Provider Analysis
```bash
# Fetch from multiple providers sequentially
python run.py --fetch --provider limitless --key "lmts_..."
python run.py --fetch --provider polymarket --key "0x..."

# Load a file with auto-detected format
python run.py --file polymarket_trades.json --global
```

### Example 2: Quick Market Analysis
```bash
python run.py --file trades.json --market "BTC-USD" --chart simple
```

### Example 3: Professional Dashboard
```bash
python run.py --file trades.json --dashboard
```

### Example 4: Filtered Export
```bash
python run.py --file trades.json \
    --start-date 2024-06-01 \
    --min-pnl 10 \
    --export profitable_trades.csv
```

### Example 5: Advanced Metrics
```bash
python run.py --file trades.json --metrics
```

## Python API

You can also use the package programmatically:

```python
from prediction_analyzer.trade_loader import load_trades
from prediction_analyzer.pnl import calculate_global_pnl_summary
from prediction_analyzer.charts.pro import generate_pro_chart

# Load trades (auto-detects provider format)
trades = load_trades("trades.json")

# Calculate PnL
summary = calculate_global_pnl_summary(trades)
print(f"Total PnL: ${summary['total_pnl']:.2f}")

# Fetch from a specific provider
from prediction_analyzer.providers import ProviderRegistry
provider = ProviderRegistry.get("polymarket")
trades = provider.fetch_trades("0xYourWallet")

# Apply FIFO PnL computation
from prediction_analyzer.providers.pnl_calculator import compute_realized_pnl
trades = compute_realized_pnl(trades)

# Filter by source provider
from prediction_analyzer.trade_filter import filter_trades_by_source
poly_trades = filter_trades_by_source(trades, "polymarket")
```

## CLI Options

### Data Source
- `--file FILE` - Load trades from file (JSON/CSV/XLSX) with auto-format detection
- `--fetch` - Fetch live trades from prediction market API
- `--key KEY` - API key/credential (format depends on provider)
- `--provider {auto,limitless,polymarket,kalshi,manifold}` - Provider selection (default: auto-detect from key)

### Analysis
- `--market MARKET` - Analyze specific market
- `--global` - Show global PnL summary
- `--chart {simple,pro,enhanced}` - Chart type (default: simple)
- `--dashboard` - Generate multi-market dashboard
- `--metrics` - Show advanced trading metrics (Sharpe, drawdown, streaks)

### Filters
- `--start-date DATE` - Filter from date (YYYY-MM-DD)
- `--end-date DATE` - Filter to date (YYYY-MM-DD)
- `--type {Buy,Sell}` - Filter by trade type
- `--min-pnl PNL` - Minimum PnL threshold
- `--max-pnl PNL` - Maximum PnL threshold

### Export
- `--export FILE` - Export filtered trades (.csv or .xlsx)
- `--report` - Generate detailed text report

## Project Structure

```
prediction_analyzer/
├── __init__.py              # Package initialization
├── __main__.py              # CLI entry point (multi-provider)
├── config.py                # Configuration constants + PROVIDER_CONFIGS
├── trade_loader.py          # Trade loading (JSON/CSV/XLSX) with auto-detection
├── trade_filter.py          # Trade filtering (market, source, dedup)
├── filters.py               # Advanced filters (date, type, PnL)
├── pnl.py                   # PnL calculations (with per-source breakdown)
├── inference.py             # Market outcome inference
├── providers/               # Multi-market provider abstraction
│   ├── base.py              # MarketProvider ABC + ProviderRegistry
│   ├── limitless.py         # Limitless Exchange provider
│   ├── polymarket.py        # Polymarket provider
│   ├── kalshi.py            # Kalshi provider (RSA-PSS auth)
│   ├── manifold.py          # Manifold Markets provider
│   └── pnl_calculator.py    # FIFO PnL computation
├── charts/                  # Chart generation modules
│   ├── simple.py            # Simple charts (matplotlib)
│   ├── pro.py               # Professional charts (Plotly)
│   ├── enhanced.py          # Battlefield-style visualization
│   └── global_chart.py      # Multi-market dashboard
├── reporting/               # Report generation
│   ├── report_text.py       # Text reports
│   └── report_data.py       # Data exports (CSV/Excel)
├── utils/                   # Utility functions
│   ├── auth.py              # Multi-provider API authentication
│   ├── data.py              # Limitless API data fetching
│   ├── time_utils.py        # Time utilities
│   ├── math_utils.py        # Math utilities
│   └── export.py            # Export utilities
├── api/                     # FastAPI web application
│   ├── models/              # SQLAlchemy ORM models
│   ├── routers/             # API route handlers
│   ├── schemas/             # Pydantic request/response schemas
│   └── services/            # Business logic services
└── core/                    # Core modules
    └── interactive.py       # Interactive CLI menu

prediction_mcp/              # MCP server for Claude integration
├── server.py                # MCP server entry point (stdio + SSE)
├── state.py                 # Session state (multi-source)
├── persistence.py           # SQLite session persistence
└── tools/                   # MCP tool modules
    ├── data_tools.py        # load_trades, fetch_trades, list_markets
    ├── analysis_tools.py    # PnL summaries, provider breakdown
    ├── filter_tools.py      # Trade filtering
    ├── chart_tools.py       # Chart generation
    ├── export_tools.py      # Data export
    ├── portfolio_tools.py   # Portfolio analysis
    └── tax_tools.py         # Tax reporting

Root directory:
├── run.py                   # CLI launcher
├── run_gui.py               # GUI launcher
├── run_gui.bat              # Windows GUI launcher
├── gui.py                   # GUI application (Tkinter, multi-provider)
├── requirements.txt         # Dependencies
├── .env.example             # Environment variable template (all providers)
└── tests/                   # Test suite (455 tests)
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=prediction_analyzer
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the LICENSE file for details.

## Troubleshooting

**For complete troubleshooting guide, see [INSTALL.md](INSTALL.md)**

### Missing Dependencies (pandas, numpy, cryptography, etc.)
The `run.py` script will now detect missing dependencies and show you exactly what's missing!

**Quick Fix:**
```bash
# Windows: Double-click install.bat or run:
install.bat

# All platforms:
pip install -r requirements.txt
```

### "ModuleNotFoundError: No module named 'setuptools'"
Don't use `python setup.py` directly. Instead:
```bash
pip install -r requirements.txt
```

### "ImportError: attempted relative import with no known parent package"
Don't run files from inside the `prediction_analyzer/` directory. Always use:
```bash
# From the project root directory:
python run.py --file your_trades.json
```

### Windows Path Issues
On Windows, use forward slashes or escape backslashes in file paths:
```powershell
# Good
python run.py --file "C:/Users/YourName/trades.json"

# Also good
python run.py --file "C:\\Users\\YourName\\trades.json"
```

### GUI Not Launching (Linux)
If the GUI doesn't launch on Linux, you may need to install tkinter:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

### Kalshi RSA Key Issues
If you get errors with Kalshi authentication:
```bash
# Ensure cryptography package is installed
pip install cryptography>=41.0.0

# Verify your PEM key file is readable
ls -la your_private_key.pem
```
