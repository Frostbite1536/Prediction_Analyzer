# Prediction Analyzer

A complete modular analysis tool for prediction market traders. Analyze past trades, calculate PnL, generate charts, and export reports. Supports both novice and professional traders.

## 🚀 Features

### For Everyone
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

### Option 1: Run Without Installation (Quickest)

If you want to try the package without installing it:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run directly using the run script
python run.py --help

# Example: Analyze trades
python run.py --file your_trades.json
```

**Windows Users:**
```powershell
# Install dependencies
pip install -r requirements.txt

# Run the analyzer
python run.py --file your_trades.json
```

### Option 2: Full Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/prediction_analyzer.git
cd prediction_analyzer

# Install the package
pip install .

# Or install in development mode
pip install -e .
```

After installation, you can use the `prediction-analyzer` command directly:
```bash
prediction-analyzer --file your_trades.json
```

## 🎯 Quick Start

### Interactive Mode (Novice-Friendly)
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

### "ModuleNotFoundError: No module named 'setuptools'"
Don't use `python setup.py` directly. Instead, use one of these methods:
```bash
# Method 1: Run without installation
pip install -r requirements.txt
python run.py --file your_trades.json

# Method 2: Install with pip (handles setuptools automatically)
pip install .
```

### "ImportError: attempted relative import with no known parent package"
Don't run files from inside the `prediction_analyzer/` directory. Instead, use:
```bash
# From the project root directory
python run.py --file your_trades.json
```

### Missing Dependencies
If you get import errors for pandas, numpy, etc.:
```bash
pip install -r requirements.txt
```

### Windows Path Issues
On Windows, use forward slashes or escape backslashes in file paths:
```powershell
# Good
python run.py --file "C:/Users/YourName/trades.json"

# Also good
python run.py --file "C:\\Users\\YourName\\trades.json"
```

## 🙏 Acknowledgments

- Built for prediction market traders
- Supports Limitless Exchange and similar platforms
- Inspired by the need for better trade analytics

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/prediction_analyzer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/prediction_analyzer/discussions)
- **Email**: you@example.com

## 🗺️ Roadmap

- [ ] Support for more prediction market platforms
- [ ] Machine learning insights
- [ ] Mobile app version
- [ ] Real-time trade tracking
- [ ] Social features (share analyses)
- [ ] Advanced risk metrics