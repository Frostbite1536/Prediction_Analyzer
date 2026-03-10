# Architecture Documentation

This document provides a comprehensive overview of the Prediction Analyzer architecture, including component design, data flow, and module dependencies.

## Overview

Prediction Analyzer is a modular Python application for analyzing prediction market trades across multiple platforms (Limitless Exchange, Polymarket, Kalshi, Manifold Markets). It supports multiple input formats, provides various visualization options, and offers CLI, GUI, MCP server, and Web API interfaces.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User Interfaces                               │
├───────────┬───────────┬────────────────────┬────────────────────────────┤
│ GUI       │ CLI       │ MCP Server         │ FastAPI Web App            │
│ (gui.py)  │(__main__) │(prediction_mcp/)   │(prediction_analyzer/api/) │
│ Tkinter   │ argparse  │ stdio + SSE        │ REST + JWT auth            │
│ Provider  │ --provider│ Claude Code /      │ Upload, query, export      │
│ dropdown  │ flag      │ Claude Desktop     │                            │
└───────────┴───────────┴────────────────────┴────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Provider Abstraction Layer                          │
├─────────────────────────────────────────────────────────────────────────┤
│  providers/base.py     │  MarketProvider ABC + ProviderRegistry         │
│  providers/limitless   │  API key auth, USDC micro-unit conversion      │
│  providers/polymarket  │  Public Data API, timestamp pagination         │
│  providers/kalshi      │  RSA-PSS request signing, position PnL         │
│  providers/manifold    │  Cursor pagination, batch market fetch          │
│  providers/pnl_calc    │  FIFO buy/sell matching for realized PnL       │
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Core Business Logic                              │
├─────────────────────────────────────────────────────────────────────────┤
│  trade_loader.py     │  pnl.py              │  filters.py               │
│  - Load JSON/CSV/XLS │  - PnL calculations  │  - Date/type/PnL filters  │
│  - Parse timestamps  │  - Market summaries  │  - Trade type filtering   │
│  - Trade dataclass   │  - Per-source breakdn│  - Datetime normalization │
│  - Auto-detect fmt   │  - ROI calculations  │                           │
├──────────────────────┴──────────────────────┴───────────────────────────┤
│  trade_filter.py     │  inference.py        │  config.py                │
│  - Market filtering  │  - Outcome inference │  - PROVIDER_CONFIGS       │
│  - Source filtering  │                      │  - API settings           │
│  - Fuzzy matching    │                      │  - Chart styling          │
│  - Deduplication     │                      │  - Constants              │
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
┌───────────────────────┐ ┌───────────────────┐ ┌────────────────────────┐
│       charts/         │ │    reporting/     │ │        utils/          │
├───────────────────────┤ ├───────────────────┤ ├────────────────────────┤
│ simple.py (matplotlib)│ │ report_text.py    │ │ auth.py (multi-provider│
│ pro.py (Plotly)       │ │ report_data.py    │ │   auth + key detect)   │
│ enhanced.py           │ │                   │ │ data.py (Limitless API)│
│ global_chart.py       │ │                   │ │ export.py              │
│                       │ │                   │ │ math_utils.py          │
│                       │ │                   │ │ time_utils.py          │
└───────────────────────┘ └───────────────────┘ └────────────────────────┘
```

## Project Structure

```
prediction_analyzer/
├── __init__.py              # Package initialization, version info
├── __main__.py              # CLI entry point with --provider flag
├── config.py                # Configuration (PROVIDER_CONFIGS, API URLs, chart styles)
├── trade_loader.py          # Trade loading and parsing (JSON/CSV/XLSX, auto-detect)
├── trade_filter.py          # Market filtering, source filtering, deduplication
├── filters.py               # Advanced filters (date, type, PnL)
├── pnl.py                   # PnL calculation and analysis (per-source breakdown)
├── inference.py             # Market outcome inference
│
├── providers/               # Multi-market provider abstraction layer
│   ├── __init__.py          # Auto-registers all 4 providers
│   ├── base.py              # MarketProvider ABC + ProviderRegistry
│   ├── limitless.py         # Limitless Exchange (USDC, lmts_ key)
│   ├── polymarket.py        # Polymarket (USDC, 0x wallet, public API)
│   ├── kalshi.py            # Kalshi (USD, RSA-PSS signing)
│   ├── manifold.py          # Manifold Markets (MANA, manifold_ key)
│   └── pnl_calculator.py    # FIFO PnL computation for providers without native PnL
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
│   ├── auth.py              # Multi-provider API key resolution + detection
│   ├── data.py              # Limitless API data fetching (legacy)
│   ├── export.py            # Export utilities
│   ├── math_utils.py        # Mathematical helpers
│   └── time_utils.py        # Time/date utilities
│
├── api/                     # FastAPI web application
│   ├── __init__.py
│   ├── main.py              # FastAPI app creation
│   ├── dependencies.py      # Dependency injection
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py          # User model
│   │   └── trade.py         # Trade model (with source/currency columns)
│   ├── routers/             # API route handlers
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── trades.py        # Trade CRUD + /providers endpoint
│   │   ├── analysis.py      # Analysis endpoints
│   │   └── charts.py        # Chart endpoints
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── trade.py         # Trade schemas (with source/currency fields)
│   │   └── user.py          # User schemas
│   └── services/            # Business logic services
│       └── trade_service.py # Trade service (source filter support)
│
└── core/                    # Core interactive features
    ├── __init__.py
    └── interactive.py       # Interactive CLI menu system

prediction_mcp/              # MCP server package
├── __init__.py
├── server.py                # MCP server (stdio + SSE transports)
├── state.py                 # Session state (multi-source, backward compat)
├── persistence.py           # SQLite persistence (source/currency columns)
├── errors.py                # Error handling with @safe_tool decorator + recovery hints
├── serializers.py           # JSON serialization (NaN/Infinity/datetime safe)
├── validators.py            # Input validation (enums, dates, NaN guards, case normalization)
├── _apply_filters.py        # Shared filter application helper
└── tools/                   # MCP tool modules (18 tools total)
    ├── __init__.py
    ├── data_tools.py        # load_trades, fetch_trades, list_markets, get_trade_details
    ├── analysis_tools.py    # get_global_summary, get_market_summary, get_advanced_metrics, get_market_breakdown, get_provider_breakdown
    ├── filter_tools.py      # filter_trades (with clear=true to reset)
    ├── chart_tools.py       # generate_chart, generate_dashboard
    ├── export_tools.py      # export_trades (csv/xlsx/json, path traversal guard)
    ├── portfolio_tools.py   # get_open_positions, get_concentration_risk, get_drawdown_analysis, compare_periods
    └── tax_tools.py         # get_tax_report

Root Directory:
├── run.py                   # CLI launcher script
├── run_gui.py               # GUI launcher script
├── run_gui.bat              # Windows GUI launcher
├── gui.py                   # Full GUI application (Tkinter, provider dropdown)
├── requirements.txt         # Runtime dependencies (includes cryptography)
├── pyproject.toml           # Package configuration (AGPL-3.0)
├── setup.py                 # Legacy setup script (AGPL-3.0)
├── .env.example             # Environment variable template (all 4 providers)
└── tests/                   # Test suite
    ├── conftest.py          # Shared fixtures
    ├── test_package.py      # Package-level tests
    ├── mcp/                 # MCP server tests (18 test modules)
    └── static_patterns/     # Static analysis tests (9 test modules)
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
    cost: float           # Total cost
    type: str             # "Buy" or "Sell" (or variants)
    side: str             # "YES" or "NO"
    pnl: float            # Profit/loss (default: 0.0)
    pnl_is_set: bool      # True when pnl was explicitly set by provider
    tx_hash: str          # Transaction hash (optional)
    source: str           # Provider: "limitless", "polymarket", "kalshi", "manifold"
    currency: str         # "USD", "USDC", or "MANA"
```

### Provider Configuration

Provider settings are defined in `config.py`:

```python
PROVIDER_CONFIGS = {
    "limitless":  {"base_url": "...", "api_key_prefix": "lmts_",     "currency": "USDC"},
    "polymarket": {"data_url": "...", "api_key_prefix": "0x",        "currency": "USDC"},
    "kalshi":     {"base_url": "...", "api_key_prefix": "kalshi_",   "currency": "USD"},
    "manifold":   {"base_url": "...", "api_key_prefix": "manifold_", "currency": "MANA"},
}
```

### MCP Session State

```python
@dataclass
class SessionState:
    trades: List[Trade]              # All loaded trades (may span providers)
    filtered_trades: List[Trade]     # Currently filtered subset
    active_filters: Dict[str, Any]   # Applied filter parameters
    sources: List[str]               # Active provider sources (e.g. ["limitless", "polymarket"])
```

### Trade Type Variants

The system handles multiple trade type formats:
- Standard: `Buy`, `Sell`
- Market orders: `Market Buy`, `Market Sell`
- Limit orders: `Limit Buy`, `Limit Sell`

## Data Flow

### 1. Data Ingestion

```
External Sources              Provider Layer              Internal Format
─────────────────────────────────────────────────────────────────────────
JSON File ─────┐
               │
CSV File ──────┼─► load_trades() ──► auto-detect ──► List[Trade]
               │   (trade_loader)    provider fmt     (with source field)
XLSX File ─────┘

Limitless API ─── LimitlessProvider.fetch_trades() ──┐
                                                      │
Polymarket API ── PolymarketProvider.fetch_trades() ──┼──► List[Trade]
                                                      │    (source set)
Kalshi API ────── KalshiProvider.fetch_trades() ──────┤
                  (RSA-PSS signed requests)           │
Manifold API ──── ManifoldProvider.fetch_trades() ────┘
                                                      │
                                              ┌───────┘
                                              ▼
                              FIFO PnL Calculator
                              (for providers without
                               native PnL support)
```

### 2. Processing Pipeline

```
List[Trade]
    │
    ├──► filter_by_date()           ──┐
    ├──► filter_by_trade_type()       ├──► Filtered List[Trade]
    ├──► filter_by_pnl()              │
    ├──► filter_trades_by_market()    │
    └──► filter_trades_by_source() ──┘
                                      │
                                      ▼
              ┌───────────────────────┴───────────────────────┐
              │                                               │
              ▼                                               ▼
    calculate_global_pnl_summary()              calculate_market_pnl_summary()
    (currency-separated: real-money              (per-market statistics)
     USD/USDC vs play-money MANA;
     by_currency + by_source breakdowns)
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

### Provider Abstraction (`providers/`)

The provider layer abstracts platform-specific details behind a common interface:

```python
class MarketProvider(ABC):
    name: str              # e.g. "polymarket"
    display_name: str      # e.g. "Polymarket"
    api_key_prefix: str    # e.g. "0x"
    currency: str          # e.g. "USDC"

    def fetch_trades(api_key, **kwargs) -> List[Trade]
    def fetch_market_details(api_key, market_id) -> dict
    def normalize_trade(raw_trade: dict) -> Trade
    def detect_file_format(sample_records: list) -> bool
```

**ProviderRegistry** manages provider instances:
- `register(provider)` - Register a provider
- `get(name)` - Get by name
- `detect_from_key(api_key)` - Auto-detect from key prefix
- `detect_from_file(sample)` - Auto-detect from file record fields
- `all()` / `names()` - List registered providers

**Provider-specific details:**

| Provider | Auth | Pagination | PnL Source |
|----------|------|-----------|------------|
| Limitless | `X-API-Key` header | Page-based (`page` param) | Native (API provides PnL) |
| Polymarket | None (public API, wallet as query param) | Timestamp window narrowing | FIFO calculator |
| Kalshi | RSA-PSS per-request signing | Cursor-based (`cursor` param) | Position endpoint + distribution |
| Manifold | `Authorization: Key ...` header | Cursor-based (`before` param) | FIFO calculator |

### FIFO PnL Calculator (`providers/pnl_calculator.py`)

For providers that don't supply per-trade PnL (Polymarket, Manifold), the FIFO calculator matches buy/sell pairs per (market_slug, side, source) key and computes realized PnL. Only updates trades where `pnl_is_set` is `False`, preserving provider-supplied PnL (including legitimate zero/breakeven values).

### Trade Loader (`trade_loader.py`)

Responsible for loading and normalizing trade data from multiple sources:

- **Supported formats**: JSON, CSV, XLSX
- **Auto-detection**: Uses ProviderRegistry to detect file format from field signatures
- **Timestamp parsing**: Handles Unix epochs (seconds/milliseconds), RFC 3339, ISO 8601
- **Unit conversion**: Converts API micro-units (6 decimals) to standard units
- **Field mapping**: Maps various API field names to internal format

Key functions:
- `load_trades(file_path)`: Main entry point -- auto-detects provider format
- `save_trades(trades, file_path)`: Save trades to JSON
- `_parse_timestamp(value)`: Robust timestamp parsing

### PnL Calculator (`pnl.py`)

Calculates profit/loss metrics:

- `calculate_pnl(trades)`: Returns DataFrame with cumulative PnL
- `calculate_global_pnl_summary(trades)`: Aggregate statistics with currency separation -- top-level totals use real-money currencies (USD/USDC) only; play-money (MANA) reported separately under `by_currency`; also includes `by_source` breakdown
- `calculate_market_pnl_summary(trades)`: Per-market statistics
- `calculate_market_pnl(trades)`: Breakdown by market

Metrics calculated:
- Total PnL, Average PnL (currency-separated)
- Win rate (excluding breakeven trades)
- ROI percentage
- Winning/Losing trade counts
- Total invested/returned
- Per-currency and per-source breakdowns

### Filters (`filters.py` + `trade_filter.py`)

Advanced filtering capabilities:

- `filter_by_date(trades, start, end)`: Date range filtering
- `filter_by_trade_type(trades, types)`: Buy/Sell filtering
- `filter_by_side(trades, sides)`: YES/NO filtering
- `filter_by_pnl(trades, min_pnl, max_pnl)`: PnL threshold filtering
- `filter_trades_by_source(trades, source)`: Provider-based filtering
- `filter_trades_by_market_slug(trades, slug)`: Exact slug match
- `deduplicate_trades(trades)`: Remove duplicate entries
- `get_unique_markets(trades)`: Get market slug-to-name mapping

### Auth (`utils/auth.py`)

Multi-provider API key resolution:

- `get_api_key(api_key, provider)`: Resolves key from argument or env var
- `get_auth_headers(api_key)`: Build Limitless auth headers
- `detect_provider_from_key(api_key)`: Auto-detect provider from key prefix

Environment variable mapping:

| Provider | Env Var |
|----------|---------|
| Limitless | `LIMITLESS_API_KEY` |
| Polymarket | `POLYMARKET_WALLET` |
| Kalshi | `KALSHI_API_KEY_ID` + `KALSHI_PRIVATE_KEY_PATH` |
| Manifold | `MANIFOLD_API_KEY` |

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

### MCP Server (`prediction_mcp/`)

Model Context Protocol server providing 18 tools across 7 modules:

- **Transport**: stdio (Claude Code) or HTTP/SSE (web agents)
- **State**: In-memory session with optional SQLite persistence
- **Multi-source**: Session tracks multiple provider sources simultaneously
- **Tools**: data (4), analysis (5), filter (1), chart (2), export (1), portfolio (4), tax (1)

Key features:
- `fetch_trades` tool accepts `provider` parameter with auto-detection
- `list_markets` shows per-market source providers
- `get_provider_breakdown` tool for cross-provider analysis
- SQLite persistence includes source/currency columns with schema migration

### FastAPI Web App (`api/`)

REST API with JWT authentication:

- Trade upload with auto-detection of provider format
- Source-based filtering (`?source=polymarket`)
- `/trades/providers` endpoint listing available providers
- CSV/JSON export with source and currency fields
- SQLAlchemy models include `source` and `currency` columns

## User Interfaces

### CLI (`__main__.py`)

Command-line interface with argparse:

```
Data Source:
  --file FILE         Load from JSON/CSV/XLSX file (auto-detects provider format)
  --fetch             Fetch from API
  --key KEY           API key/credential (format depends on provider)
  --provider PROV     Provider: auto, limitless, polymarket, kalshi, manifold

Analysis:
  --market MARKET     Analyze specific market
  --global            Show global PnL summary
  --chart TYPE        Chart type (simple/pro/enhanced)
  --dashboard         Multi-market dashboard
  --metrics           Advanced trading metrics

Filters:
  --start-date        Filter from date
  --end-date          Filter to date
  --type              Filter by trade type
  --min-pnl           Minimum PnL threshold
  --max-pnl           Maximum PnL threshold

Export:
  --export FILE       Export to CSV/XLSX
  --report            Generate text report
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
│ Provider: [▼ auto/limitless/polymarket/kalshi/manifold]         │
│ API Key / Wallet: [________________]                            │
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
- Provider selection dropdown (auto/limitless/polymarket/kalshi/manifold)
- File loading with dialog (auto-detects provider format)
- API authentication with provider-appropriate credentials
- Tabbed interface for different views
- Market listbox with selection preservation
- Filter controls with validation
- Chart generation buttons
- Export functionality

### MCP Server (`prediction_mcp/server.py`)

```bash
python -m prediction_mcp                        # stdio (default)
python -m prediction_mcp --sse                  # HTTP/SSE on port 8000
python -m prediction_mcp --sse --port 3000
python -m prediction_mcp --persist session.db   # SQLite persistence
```

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
| cryptography | >=41.0.0 | RSA-PSS signing for Kalshi API |

### Optional Dependencies

| Package | Group | Purpose |
|---------|-------|---------|
| fastapi | api | Web API framework |
| sqlalchemy | api | ORM for database |
| PyJWT | api | JWT authentication |
| pydantic | api | Request/response validation |
| mcp | mcp | MCP server SDK |
| starlette | mcp | SSE transport |

### Development Dependencies

| Package | Purpose |
|---------|---------|
| pytest | Testing framework |
| pytest-cov | Coverage reporting |
| black | Code formatting |
| flake8 | Linting |

## Configuration (`config.py`)

### Provider Configuration
- `PROVIDER_CONFIGS`: Dict of provider settings (URLs, key prefixes, currencies)

### API Configuration (Legacy)
- `API_BASE_URL`: Base URL for the Limitless Exchange API
- `DEFAULT_TRADE_FILE`: Default filename for fetched trades

### Chart Styling
- `STYLES`: Dictionary mapping (trade_type, side) to (color, marker, label)
- Consistent color scheme across all visualizations

### Analysis Parameters
- `PRICE_RESOLUTION_THRESHOLD`: Threshold for price-based analysis

## Entry Points

### Package Entry Points
```bash
# After pip install -e .
prediction-analyzer --file trades.json
prediction-mcp                                  # MCP server
```

### Script Entry Points
```bash
# CLI via run.py
python run.py --file trades.json

# GUI via run_gui.py
python run_gui.py

# Module execution
python -m prediction_analyzer --file trades.json
python -m prediction_mcp
```

## Testing

Tests are located in `tests/` with the following structure:

```
tests/
├── __init__.py
├── conftest.py                    # Shared pytest fixtures
├── test_package.py                # Package-level tests
├── mcp/                           # MCP server tests
│   ├── conftest.py                # MCP test fixtures
│   ├── test_data_tools.py         # Data tool tests
│   ├── test_analysis_tools.py     # Analysis tool tests
│   ├── test_filter_tools.py       # Filter tool tests
│   ├── test_chart_tools.py        # Chart tool tests
│   ├── test_export_tools.py       # Export tool tests
│   ├── test_portfolio_tools.py    # Portfolio tool tests
│   ├── test_tax_tools.py          # Tax tool tests
│   ├── test_server.py             # Server dispatch tests
│   ├── test_state.py              # Session state tests
│   ├── test_persistence.py        # SQLite persistence tests
│   ├── test_transport.py          # Transport tests
│   ├── test_sse_transport.py      # SSE transport tests
│   ├── test_serializers.py        # Serializer tests
│   ├── test_validators.py         # Validator tests
│   ├── test_errors.py             # Error handling tests
│   └── test_llm_inputs.py         # LLM input edge cases (wrong names, case, NaN)
└── static_patterns/               # Static analysis tests
    ├── test_api_contracts.py      # API contract validation
    ├── test_config_integrity.py   # Configuration tests
    ├── test_data_integrity.py     # Data handling tests
    ├── test_dataclass_contracts.py # Dataclass validation (13 fields)
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
2. **Provider abstraction**: Platform-specific details behind a common interface
3. **Auto-detection**: Provider format detected from API key prefix or file field signatures
4. **Backward compatibility**: Legacy Limitless-only code paths still work
5. **Flexibility**: Multiple input formats, output options, and interface choices
6. **User Levels**: Supports both novice (GUI/interactive) and pro (CLI/API) users
7. **Robustness**: Handles various data formats, edge cases, and schema migrations
8. **Extensibility**: New providers can be added by implementing MarketProvider ABC

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
