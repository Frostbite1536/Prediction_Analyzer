# Architecture Documentation

This document provides a comprehensive overview of the Prediction Analyzer architecture, including component design, data flow, and module dependencies.

## Overview

Prediction Analyzer is a modular Python application for analyzing prediction market trades. It supports multiple input formats, provides various visualization options, and offers both CLI and GUI interfaces.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User Interfaces                               │
├──────────────────────────────┬──────────────────────────────────────────┤
│        GUI (gui.py)          │           CLI (__main__.py)              │
│   - Tkinter desktop app      │   - argparse command-line interface      │
│   - Interactive filtering    │   - Batch processing support             │
│   - Point-and-click charts   │   - Automation-friendly                  │
└──────────────────────────────┴──────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Core Business Logic                              │
├─────────────────────────────────────────────────────────────────────────┤
│  trade_loader.py     │  pnl.py              │  filters.py               │
│  - Load JSON/CSV/XLS │  - PnL calculations  │  - Date/type/PnL filters  │
│  - Parse timestamps  │  - Market summaries  │  - Trade type filtering   │
│  - Trade dataclass   │  - ROI calculations  │  - Datetime normalization │
├──────────────────────┴──────────────────────┴───────────────────────────┤
│  trade_filter.py     │  inference.py        │  config.py                │
│  - Market filtering  │  - Outcome inference │  - API settings           │
│  - Fuzzy matching    │                      │  - Chart styling          │
│  - Deduplication     │                      │  - Constants              │
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
┌───────────────────────┐ ┌───────────────────┐ ┌────────────────────────┐
│       charts/         │ │    reporting/     │ │        utils/          │
├───────────────────────┤ ├───────────────────┤ ├────────────────────────┤
│ simple.py (matplotlib)│ │ report_text.py    │ │ auth.py (API auth)     │
│ pro.py (Plotly)       │ │ report_data.py    │ │ data.py (API fetch)    │
│ enhanced.py           │ │                   │ │ export.py              │
│ global_chart.py       │ │                   │ │ math_utils.py          │
│                       │ │                   │ │ time_utils.py          │
└───────────────────────┘ └───────────────────┘ └────────────────────────┘
```

## Project Structure

```
prediction_analyzer/
├── __init__.py              # Package initialization, version info
├── __main__.py              # CLI entry point with argparse
├── config.py                # Configuration constants (API URLs, chart styles)
├── trade_loader.py          # Trade loading and parsing (JSON/CSV/XLSX)
├── trade_filter.py          # Market filtering and deduplication
├── filters.py               # Advanced filters (date, type, PnL)
├── pnl.py                   # PnL calculation and analysis
├── inference.py             # Market outcome inference
│
├── charts/                  # Visualization modules
│   ├── __init__.py          # Chart exports
│   ├── simple.py            # Matplotlib-based simple charts
│   ├── pro.py               # Plotly interactive charts
│   ├── enhanced.py          # Battlefield-style visualization
│   └── global_chart.py      # Multi-market dashboard
│
├── reporting/               # Report generation
│   ├── __init__.py
│   ├── report_text.py       # Text/console reports
│   └── report_data.py       # CSV/Excel exports
│
├── utils/                   # Utility functions
│   ├── __init__.py
│   ├── auth.py              # API authentication (eth-account signing)
│   ├── data.py              # API data fetching
│   ├── export.py            # Export utilities
│   ├── math_utils.py        # Mathematical helpers
│   └── time_utils.py        # Time/date utilities
│
└── core/                    # Core interactive features
    ├── __init__.py
    └── interactive.py       # Interactive CLI menu system

Root Directory:
├── run.py                   # CLI launcher script
├── run_gui.py               # GUI launcher script
├── gui.py                   # Full GUI application (Tkinter)
├── requirements.txt         # Runtime dependencies
├── pyproject.toml           # Package configuration
└── setup.py                 # Legacy setup script
```

## Data Models

### Trade Dataclass

The central data structure is the `Trade` dataclass defined in `trade_loader.py`:

```python
@dataclass
class Trade:
    market: str           # Market title/name
    market_slug: str      # Market identifier slug
    timestamp: datetime   # Trade execution time
    price: float          # Trade price
    shares: float         # Number of shares
    cost: float           # Total cost in USDC
    type: str             # "Buy" or "Sell" (or variants)
    side: str             # "YES" or "NO"
    pnl: float            # Profit/loss (default: 0.0)
    tx_hash: str          # Transaction hash (optional)
```

### Trade Type Variants

The system handles multiple trade type formats:
- Standard: `Buy`, `Sell`
- Market orders: `Market Buy`, `Market Sell`
- Limit orders: `Limit Buy`, `Limit Sell`

## Data Flow

### 1. Data Ingestion

```
External Sources              Trade Loader              Internal Format
─────────────────────────────────────────────────────────────────────────
JSON File ─────┐
               │
CSV File ──────┼───► load_trades() ───► List[Trade]
               │    (trade_loader.py)
XLSX File ─────┤
               │
API Response ──┘
    └──► fetch_trade_history() ───► raw dict ───► load_trades()
        (utils/data.py)
```

### 2. Processing Pipeline

```
List[Trade]
    │
    ├──► filter_by_date()           ──┐
    ├──► filter_by_trade_type()       ├──► Filtered List[Trade]
    ├──► filter_by_pnl()              │
    └──► filter_trades_by_market()  ──┘
                                      │
                                      ▼
              ┌───────────────────────┴───────────────────────┐
              │                                               │
              ▼                                               ▼
    calculate_global_pnl_summary()              calculate_market_pnl_summary()
              │                                               │
              ▼                                               ▼
         Dict[stats]                                    Dict[stats]
```

### 3. Output Generation

```
Filtered Trades + Stats
         │
         ├──► Charts ───────┬──► generate_simple_chart()   ──► matplotlib figure
         │                  ├──► generate_pro_chart()      ──► Plotly HTML
         │                  ├──► generate_enhanced_chart() ──► Enhanced viz
         │                  └──► generate_global_dashboard() ──► Multi-chart
         │
         ├──► Reports ──────┬──► print_global_summary()    ──► Console output
         │                  └──► generate_text_report()    ──► Text report
         │
         └──► Exports ──────┬──► export_to_csv()           ──► CSV file
                            └──► export_to_excel()         ──► XLSX file
```

## Component Details

### Trade Loader (`trade_loader.py`)

Responsible for loading and normalizing trade data from multiple sources:

- **Supported formats**: JSON, CSV, XLSX
- **Timestamp parsing**: Handles Unix epochs (seconds/milliseconds), RFC 3339, ISO 8601
- **Unit conversion**: Converts API micro-units (6 decimals) to standard units
- **Field mapping**: Maps various API field names to internal format

Key functions:
- `load_trades(file_path)`: Main entry point for loading trade files
- `save_trades(trades, file_path)`: Save trades to JSON
- `_parse_timestamp(value)`: Robust timestamp parsing

### PnL Calculator (`pnl.py`)

Calculates profit/loss metrics:

- `calculate_pnl(trades)`: Returns DataFrame with cumulative PnL
- `calculate_global_pnl_summary(trades)`: Aggregate statistics
- `calculate_market_pnl_summary(trades)`: Per-market statistics
- `calculate_market_pnl(trades)`: Breakdown by market

Metrics calculated:
- Total PnL, Average PnL
- Win rate (excluding breakeven trades)
- ROI percentage
- Winning/Losing trade counts
- Total invested/returned

### Filters (`filters.py`)

Advanced filtering capabilities:

- `filter_by_date(trades, start, end)`: Date range filtering
- `filter_by_trade_type(trades, types)`: Buy/Sell filtering
- `filter_by_side(trades, sides)`: YES/NO filtering
- `filter_by_pnl(trades, min_pnl, max_pnl)`: PnL threshold filtering

### Trade Filter (`trade_filter.py`)

Market-specific filtering:

- `filter_trades(trades, market_name, fuzzy)`: Fuzzy market matching
- `filter_trades_by_market_slug(trades, slug)`: Exact slug match
- `deduplicate_trades(trades)`: Remove duplicate entries
- `get_unique_markets(trades)`: Get market slug→name mapping
- `group_trades_by_market(trades)`: Group trades by market

### Charts Module (`charts/`)

Four chart types with different use cases:

| Chart Type | Library | Use Case |
|------------|---------|----------|
| `simple` | matplotlib | Quick static visualization |
| `pro` | Plotly | Interactive web-based charts |
| `enhanced` | matplotlib | Battlefield-style view |
| `global_chart` | Plotly | Multi-market dashboard |

### Reporting Module (`reporting/`)

- **report_text.py**: Console/text output formatting
- **report_data.py**: CSV and Excel export functionality

### Utils Module (`utils/`)

Supporting utilities:

- **auth.py**: Ethereum wallet authentication using eth-account
- **data.py**: API communication for fetching live trades
- **export.py**: File export helpers
- **math_utils.py**: Mathematical calculations
- **time_utils.py**: Time/date manipulation

## User Interfaces

### CLI (`__main__.py`)

Command-line interface with argparse:

```
Data Source:
  --file FILE       Load from JSON/CSV/XLSX file
  --fetch           Fetch from API
  --key KEY         Private key for API auth

Analysis:
  --market MARKET   Analyze specific market
  --global          Show global PnL summary
  --chart TYPE      Chart type (simple/pro/enhanced)
  --dashboard       Multi-market dashboard

Filters:
  --start-date      Filter from date
  --end-date        Filter to date
  --type            Filter by trade type
  --min-pnl         Minimum PnL threshold
  --max-pnl         Maximum PnL threshold

Export:
  --export FILE     Export to CSV/XLSX
  --report          Generate text report
```

### Interactive CLI (`core/interactive.py`)

Menu-driven interface for novice users:
- Main menu navigation
- Market selection with numbered list
- Interactive filter application
- Chart type selection

### GUI (`gui.py`)

Tkinter-based desktop application:

```
┌─────────────────────────────────────────────────────────────────┐
│ File │ Analysis │ Help                                          │
├─────────────────────────────────────────────────────────────────┤
│ Quick Actions: [Load File] [Load API] [Summary] [Dashboard]    │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Tabs: [Global Summary] [Market Analysis] [Filters] [Charts]│ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │                                                             │ │
│ │                     Tab Content Area                        │ │
│ │                                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

Features:
- File loading with dialog
- API authentication with private key input
- Tabbed interface for different views
- Market listbox with selection preservation
- Filter controls with validation
- Chart generation buttons
- Export functionality

## External Dependencies

### Required Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pandas | >=1.5.0 | Data manipulation, DataFrame operations |
| numpy | >=1.23.0 | Numerical operations |
| matplotlib | >=3.7.0 | Simple chart generation |
| plotly | >=5.20.0 | Interactive charts |
| openpyxl | >=3.1.0 | Excel file support |
| requests | >=2.28.0 | API communication |
| eth-account | >=0.8.0 | Ethereum wallet signing |

### Development Dependencies

| Package | Purpose |
|---------|---------|
| pytest | Testing framework |
| pytest-cov | Coverage reporting |
| black | Code formatting |
| flake8 | Linting |

## Configuration (`config.py`)

### API Configuration
- `API_BASE_URL`: Base URL for the Limitless Exchange API
- `DEFAULT_TRADE_FILE`: Default filename for fetched trades

### Chart Styling
- `STYLES`: Dictionary mapping (trade_type, side) to (color, marker, label)
- Consistent color scheme across all visualizations

### Analysis Parameters
- `PRICE_RESOLUTION_THRESHOLD`: Threshold for price-based analysis

## Entry Points

### Package Entry Point
```bash
# After pip install -e .
prediction-analyzer --file trades.json
```

### Script Entry Points
```bash
# CLI via run.py
python run.py --file trades.json

# GUI via run_gui.py
python run_gui.py

# Module execution
python -m prediction_analyzer --file trades.json
```

## Testing

Tests are located in `tests/` with the following structure:

```
tests/
├── __init__.py
├── conftest.py                    # Shared pytest fixtures
├── test_package.py                # Package-level tests
└── static_patterns/               # Static analysis tests
    ├── test_api_contracts.py      # API contract validation
    ├── test_config_integrity.py   # Configuration tests
    ├── test_data_integrity.py     # Data handling tests
    ├── test_dataclass_contracts.py # Dataclass validation
    ├── test_edge_cases.py         # Edge case handling
    ├── test_filter_contracts.py   # Filter function tests
    ├── test_imports.py            # Import validation
    ├── test_pnl_contracts.py      # PnL calculation tests
    └── test_utility_functions.py  # Utility function tests
```

Run tests with:
```bash
pytest                    # Run all tests
pytest --cov=prediction_analyzer  # With coverage
```

## Design Principles

1. **Modularity**: Each component has a single responsibility
2. **Flexibility**: Multiple input formats and output options
3. **User Levels**: Supports both novice (GUI/interactive) and pro (CLI) users
4. **Robustness**: Handles various data formats and edge cases
5. **Extensibility**: Easy to add new chart types or export formats
