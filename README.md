# Prediction Analyzer

A complete modular analysis tool for prediction market traders. Analyze past trades, calculate PnL, generate charts, and export reports. Supports both novice and professional traders.

## 🚀 Features

### For Everyone
- **NEW: Graphical User Interface (GUI)** - Easy-to-use desktop application
- Load trade history from JSON, CSV, or Excel
- Calculate global and market-specific PnL
- Filter trades by date, type, and PnL thresholds
- Export reports in multiple formats (CSV, Excel, TXT)
- Interactive CLI menu for easy navigation

### For Novice Traders
- Simple, easy-to-understand charts
- Step-by-step interactive menus
- Clear PnL summaries
- One-click analysis

### For Professional Traders
- Advanced interactive charts with Plotly
- Multi-market dashboards
- Detailed trade-by-trade analysis
- Command-line interface for automation
- Customizable filters and exports

## 📦 Installation

**📖 For detailed installation instructions, see [INSTALL.md](INSTALL.md)**

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

## 🎯 Quick Start

### GUI Mode (Easiest - NEW!)
The easiest way to use Prediction Analyzer is through the graphical interface:

```bash
# Windows: Just double-click run_gui.bat
# Or run from command line:
python run_gui.py
```

The GUI provides:
- Point-and-click file loading
- Visual trade statistics and summaries
- Easy market selection and analysis
- Interactive filters with form controls
- One-click chart generation
- Simple export functionality

**Perfect for users who prefer a visual interface over command-line!**

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

### Fetch Live Data
```bash
# Fetch trades from API (first time)
python run.py --fetch --key "0xYOURPRIVATEKEY"

# After fetching, use local file
python run.py --file limitless_trades.json
```

## 📊 Usage Examples

### Example 0: Using the GUI
```bash
# Launch the GUI
python run_gui.py

# Then use the interface to:
# 1. Click "Load Trades File" to select your data file
# 2. View the "Global Summary" tab for overall statistics
# 3. Go to "Market Analysis" tab to analyze specific markets
# 4. Use "Filters" tab to refine your data
# 5. Generate charts with one click
# 6. Export data via File menu or quick action buttons
```

### Example 1: Quick Market Analysis
```bash
python run.py --file trades.json --market "BTC-USD" --chart simple
```

### Example 2: Professional Dashboard
```bash
python run.py --file trades.json --dashboard
```

### Example 3: Filtered Export
```bash
python run.py --file trades.json \
    --start-date 2024-06-01 \
    --min-pnl 10 \
    --export profitable_trades.csv
```

### Example 4: Generate Full Report
```bash
python run.py --file trades.json --report
```

## 🛠️ Python API

You can also use the package programmatically:

```python
from prediction_analyzer.trade_loader import load_trades
from prediction_analyzer.pnl import calculate_global_pnl_summary
from prediction_analyzer.charts.pro import generate_pro_chart

# Load trades
trades = load_trades("trades.json")

# Calculate PnL
summary = calculate_global_pnl_summary(trades)
print(f"Total PnL: ${summary['total_pnl']:.2f}")

# Generate chart for specific market
from prediction_analyzer.trade_filter import filter_trades_by_market_slug
market_trades = filter_trades_by_market_slug(trades, "ETH-USD")
generate_pro_chart(market_trades, "ETH-USD")
```

## 📂 CLI Options

### Data Source
- `--file FILE` - Load trades from file (JSON/CSV/XLSX)
- `--fetch` - Fetch live trades from API
- `--key KEY` - Private key for API authentication

### Analysis
- `--market MARKET` - Analyze specific market
- `--global` - Show global PnL summary
- `--chart {simple,pro}` - Chart type (default: simple)
- `--dashboard` - Generate multi-market dashboard

### Filters
- `--start-date DATE` - Filter from date (YYYY-MM-DD)
- `--end-date DATE` - Filter to date (YYYY-MM-DD)
- `--type {Buy,Sell}` - Filter by trade type
- `--min-pnl PNL` - Minimum PnL threshold
- `--max-pnl PNL` - Maximum PnL threshold

### Export
- `--export FILE` - Export filtered trades (.csv or .xlsx)
- `--report` - Generate detailed text report

## 🏗️ Project Structure

```
prediction_analyzer/
├── __init__.py              # Package initialization
├── __main__.py              # CLI entry point
├── config.py                # Configuration constants
├── trade_loader.py          # Trade loading (JSON/CSV/XLSX)
├── trade_filter.py          # Trade filtering utilities
├── filters.py               # Advanced filters (date, type, PnL)
├── pnl.py                   # PnL calculations
├── inference.py             # Market outcome inference
├── charts/                  # Chart generation modules
│   ├── simple.py            # Simple charts (matplotlib)
│   ├── pro.py               # Professional charts (Plotly)
│   └── global_chart.py      # Multi-market dashboard
├── reporting/               # Report generation
│   ├── report_text.py       # Text reports
│   └── report_data.py       # Data exports (CSV/Excel)
├── utils/                   # Utility functions
│   ├── auth.py              # API authentication
│   ├── data.py              # Data fetching
│   ├── time_utils.py        # Time utilities
│   ├── math_utils.py        # Math utilities
│   └── export.py            # Export utilities
└── core/                    # Core modules
    └── interactive.py       # Interactive CLI menu

Root directory:
├── run.py                   # CLI launcher
├── run_gui.py               # GUI launcher
├── run_gui.bat              # Windows GUI launcher
├── gui.py                   # GUI application
└── requirements.txt         # Dependencies
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=prediction_analyzer
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔧 Troubleshooting

**📖 For complete troubleshooting guide, see [INSTALL.md](INSTALL.md)**

### Missing Dependencies (pandas, numpy, etc.)
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
# Windows users - easiest method:
install.bat

# All platforms:
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

