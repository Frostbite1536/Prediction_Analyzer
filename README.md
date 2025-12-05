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

```bash
# Clone the repository
git clone https://github.com/yourusername/prediction_analyzer.git
cd prediction_analyzer

# Install the package
pip install .

# Or install in development mode
pip install -e .
```

## 🎯 Quick Start

### Interactive Mode (Novice-Friendly)
```bash
# Start the interactive analyzer
prediction-analyzer --file your_trades.json
```

### Command-Line Mode (Pro Users)
```bash
# Global PnL summary
prediction-analyzer --file trades.json --global

# Analyze specific market with pro chart
prediction-analyzer --file trades.json --market "ETH-USD" --chart pro

# Multi-market dashboard
prediction-analyzer --file trades.json --dashboard

# Filter and export
prediction-analyzer --file trades.json \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --type Buy \
    --export filtered_trades.xlsx
```

### Fetch Live Data
```bash
# Fetch trades from API (first time)
prediction-analyzer --fetch --key "0xYOURPRIVATEKEY"

# After fetching, use local file
prediction-analyzer --file limitless_trades.json
```

## 📊 Usage Examples

### Example 1: Quick Market Analysis
```bash
prediction-analyzer --file trades.json --market "BTC-USD" --chart simple
```

### Example 2: Professional Dashboard
```bash
prediction-analyzer --file trades.json --dashboard
```

### Example 3: Filtered Export
```bash
prediction-analyzer --file trades.json \
    --start-date 2024-06-01 \
    --min-pnl 10 \
    --export profitable_trades.csv
```

### Example 4: Generate Full Report
```bash
prediction-analyzer --file trades.json --report
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