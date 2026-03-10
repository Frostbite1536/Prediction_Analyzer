# MCP Server Readiness Plan — Prediction Analyzer

This plan prepares the Prediction Analyzer codebase for its own MCP server, following
the guidelines in [MCP_DEVELOPMENT.md](https://github.com/Frostbite1536/Safe-Vibe-Coding/blob/claude/vibe-coding-guide-OpMMi/docs/MCP_DEVELOPMENT.md).

The MCP server will let an LLM agent load trades, run analyses, generate charts,
manage portfolios, and answer trading questions — all through structured tool calls.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Phase 1 — Internal API Hardening](#2-phase-1--internal-api-hardening)
3. [Phase 2 — MCP Server Skeleton](#3-phase-2--mcp-server-skeleton)
4. [Phase 3 — Core Tools (Existing Features)](#4-phase-3--core-tools-existing-features)
5. [Phase 4 — New Feature Tools](#5-phase-4--new-feature-tools)
6. [Phase 5 — Serialization & Transport Safety](#6-phase-5--serialization--transport-safety)
7. [Phase 6 — Error Handling & Validation](#7-phase-6--error-handling--validation)
8. [Phase 7 — Testing](#8-phase-7--testing)
9. [Phase 8 — Documentation & Packaging](#9-phase-8--documentation--packaging)
10. [Tool Inventory](#10-tool-inventory)
11. [Implementation Checklist](#11-implementation-checklist)

---

## 1. Architecture Overview

```
┌──────────────────┐     JSON-RPC (stdio/HTTP)     ┌──────────────────────┐
│   LLM Client     │ ◄──────────────────────────► │  MCP Server           │
│   (Claude Code,  │                               │  prediction_mcp/      │
│    Claude Agent   │                               │    server.py          │
│    SDK, etc.)    │                               │    tools/             │
└──────────────────┘                               │    serializers.py     │
                                                   │    validators.py      │
                                                   └──────────┬───────────┘
                                                              │
                                          ┌───────────────────┼───────────────────┐
                                          │                   │                   │
                                   ┌──────▼──────┐   ┌───────▼───────┐   ┌───────▼──────┐
                                   │ Core Library │   │  FastAPI/DB   │   │  Limitless   │
                                   │ (pnl, filter │   │  (SQLAlchemy  │   │  Exchange    │
                                   │  metrics,    │   │   models,     │   │  REST API    │
                                   │  charts)     │   │   services)   │   │              │
                                   └──────────────┘   └───────────────┘   └──────────────┘
```

**Key decisions:**

- The MCP server is a **new package** (`prediction_mcp/`) alongside the existing `prediction_analyzer/` package
- It reuses the existing core library and API services — no duplication
- Transport: **stdio** (primary, for Claude Code) and **HTTP/SSE** (secondary, for web agents) — both implemented
- State: in-memory per-session with optional **SQLite persistence** (`--persist` flag or `PREDICTION_MCP_DB` env var)
- Python 3.8+ compatible (`Optional[X]` not `X | None`)

---

## 2. Phase 1 — Internal API Hardening

**Goal:** Make the existing codebase MCP-safe per the guide's "Design Your Internal APIs for MCP from Day One" section.

### 1.1 Eliminate stdout pollution

Every `print()` call in the execution path is a potential transport corruption bug.

| File | Issue | Fix |
|------|-------|-----|
| `charts/simple.py` | `print("✅ Chart saved...")` | Replace with `logging.info()` |
| `charts/pro.py` | `print("✅ Interactive chart...")` | Replace with `logging.info()` |
| `charts/enhanced.py` | `print("✅ Enhanced battlefield...")` | Replace with `logging.info()` |
| `charts/global_chart.py` | `print("✅ Global dashboard...")` | Replace with `logging.info()` |
| `trade_loader.py` | `print("❌ Failed to load...")` | Raise exceptions instead |
| `pnl.py` | Any print calls | Replace with `logging.info()` |
| `reporting/report_text.py` | `print()` for console output | Add `stream` parameter (default stderr) |

**Action:** Create `prediction_analyzer/logging_config.py` that configures a logger writing to stderr. All modules use `logger = logging.getLogger(__name__)`.

### 1.2 Return serializable types everywhere

| Function | Current Return | Fix |
|----------|---------------|-----|
| `calculate_pnl()` | `pd.DataFrame` | Add `.to_dict("records")` wrapper |
| `calculate_global_pnl_summary()` | `dict` (already good) | Verify all values are primitives |
| `calculate_advanced_metrics()` | `dict` (already good) | Add `NaN`/`Infinity` guard |
| `load_trades()` | `List[Trade]` dataclass | Add `Trade.to_dict()` method |
| `filter_*()` functions | `List[Trade]` | Same — rely on `Trade.to_dict()` |

**Action:** Add `to_dict()` to the `Trade` dataclass. Add a `sanitize_numeric(value)` helper that replaces `NaN`/`Infinity` with `0.0`/`999.99`.

### 1.3 Descriptive parameter names audit

| Function | Current Name | MCP-Friendly Name |
|----------|-------------|-------------------|
| `filter_by_pnl(trades, min_pnl, max_pnl)` | Already good | — |
| `filter_by_date(trades, start, end)` | `start`, `end` | `start_date`, `end_date` (accept both) |
| `_sanitize_filename(name, max_length)` | Already good | — |
| `generate_simple_chart(trades, market_name, ...)` | Already good | — |

### 1.4 Consistent error handling

Replace bare `print("❌ ...")` + `return` patterns with proper exceptions:

```python
class PredictionAnalyzerError(Exception):
    """Base exception for all prediction analyzer errors"""
    pass

class NoTradesError(PredictionAnalyzerError):
    """Raised when an operation requires trades but none exist"""
    pass

class InvalidFilterError(PredictionAnalyzerError):
    """Raised when filter parameters are invalid"""
    pass

class MarketNotFoundError(PredictionAnalyzerError):
    """Raised when a market slug doesn't match any trades"""
    pass
```

---

## 3. Phase 2 — MCP Server Skeleton

### 2.1 Package structure

```
prediction_mcp/
├── __init__.py
├── server.py              # MCP server entry point (stdio + HTTP)
├── tools/
│   ├── __init__.py
│   ├── data_tools.py      # load_trades, fetch_trades, list_markets
│   ├── analysis_tools.py  # global_summary, market_summary, advanced_metrics
│   ├── filter_tools.py    # filter_trades (composite)
│   ├── chart_tools.py     # generate_chart (all types)
│   ├── portfolio_tools.py # open_positions, unrealized_pnl (new feature)
│   ├── export_tools.py    # export_csv, export_excel, export_json
│   └── tax_tools.py       # capital_gains, cost_basis (new feature)
├── serializers.py         # Trade, metrics, chart data → JSON-safe dicts
├── validators.py          # Input validation, enum checking, NaN guards
├── errors.py              # Structured error responses with recovery hints
└── state.py               # In-memory session state (loaded trades, active filters)
```

### 2.2 Dependencies

```toml
# In pyproject.toml [project.optional-dependencies]
mcp = [
    "mcp>=1.0.0",          # MCP SDK
    "pydantic>=2.5.0",      # Already in [api] extras
]
```

### 2.3 Server entry point

```python
# prediction_mcp/server.py
import sys
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Configure ALL logging to stderr (critical for stdio transport)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

app = Server("prediction-analyzer")

# Register all tool modules
from .tools import data_tools, analysis_tools, filter_tools, chart_tools
from .tools import portfolio_tools, export_tools, tax_tools
```

### 2.4 Session state

The MCP server maintains lightweight in-memory state per session:

```python
# prediction_mcp/state.py
@dataclass
class SessionState:
    trades: List[Trade] = field(default_factory=list)
    filtered_trades: List[Trade] = field(default_factory=list)
    active_filters: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None  # "file:<path>" or "api:<key_prefix>"

session = SessionState()
```

This lets the LLM load trades once and then run multiple analyses without re-loading.

---

## 4. Phase 3 — Core Tools (Existing Features)

Each tool maps to existing library functions. The MCP layer adds validation, serialization, and descriptive tool descriptions.

### Tool: `load_trades`

```
Purpose: Load prediction market trades from a file (JSON, CSV, XLSX)
Parameters:
  - file_path (string, required): Absolute path to the trades file
Returns: { trade_count: int, markets: list[str], source: string }
```

Maps to: `trade_loader.load_trades()` → stores in `session.trades`

### Tool: `fetch_trades`

```
Purpose: Fetch trades from Limitless Exchange API using an API key
Parameters:
  - api_key (string, required): Limitless API key (starts with "lmts_")
  - page_limit (int, optional, default 100): Max pages to fetch
Returns: { trade_count: int, markets: list[str], source: string }
```

Maps to: `utils.data.fetch_trade_history()` → `trade_loader.load_trades()` → `session.trades`

### Tool: `list_markets`

```
Purpose: List all unique markets in the currently loaded trades
Parameters: none
Returns: [ { slug: string, title: string, trade_count: int } ]
```

Maps to: `trade_filter.get_unique_markets()`

### Tool: `get_global_summary`

```
Purpose: Calculate overall PnL summary across all loaded trades
Parameters:
  - start_date (string, optional): Filter start date "YYYY-MM-DD"
  - end_date (string, optional): Filter end date "YYYY-MM-DD"
  - trade_types (list[string], optional): Filter by type. Valid: "Buy", "Sell"
  - sides (list[string], optional): Filter by side. Valid: "YES", "NO"
  - min_pnl (float, optional): Minimum PnL threshold
  - max_pnl (float, optional): Maximum PnL threshold
Returns: {
  total_trades, total_pnl, win_rate, avg_pnl, winning_trades,
  losing_trades, breakeven_trades, total_invested, total_returned, roi
}
```

Maps to: `filters.*` → `pnl.calculate_global_pnl_summary()`

### Tool: `get_market_summary`

```
Purpose: Calculate PnL summary for a specific prediction market
Parameters:
  - market_slug (string, required): Market identifier slug
  - (same filter params as get_global_summary)
Returns: Same as global_summary + market_title, market_outcome
```

Maps to: `trade_filter.filter_trades_by_market_slug()` → `pnl.calculate_market_pnl_summary()`

### Tool: `get_advanced_metrics`

```
Purpose: Calculate risk-adjusted trading metrics: Sharpe ratio, Sortino ratio,
         max drawdown, profit factor, expectancy, win/loss streaks
Parameters:
  - market_slug (string, optional): Limit to specific market
  - (same filter params)
Returns: {
  sharpe_ratio, sortino_ratio, profit_factor, expectancy,
  avg_win, avg_loss, largest_win, largest_loss,
  max_drawdown, max_drawdown_pct, max_drawdown_duration_trades,
  max_win_streak, max_loss_streak, current_streak, current_streak_type,
  avg_trade_size, total_volume
}
```

Maps to: `metrics.calculate_advanced_metrics()`

### Tool: `get_market_breakdown`

```
Purpose: Get PnL breakdown by market showing which markets are profitable
Parameters: (filter params)
Returns: [ { market: string, market_slug: string, trade_count: int, pnl: float } ]
```

Maps to: `pnl.calculate_market_pnl()`

### Tool: `generate_chart`

```
Purpose: Generate a chart image or interactive HTML for a specific market
Parameters:
  - market_slug (string, required): Market to chart
  - chart_type (string, required): One of "simple", "pro", "enhanced"
  - output_dir (string, optional): Directory for chart output
Returns: { file_path: string, chart_type: string }
Note: Does NOT open the chart in a browser (show=False for MCP context)
```

Maps to: `charts.simple/pro/enhanced.generate_*_chart()` with `show=False` parameter (to be added)

### Tool: `generate_dashboard`

```
Purpose: Generate a multi-market PnL dashboard as interactive HTML
Parameters:
  - output_dir (string, optional): Directory for output
Returns: { file_path: string }
```

Maps to: `charts.global_chart.generate_global_dashboard()`

### Tool: `export_trades`

```
Purpose: Export trades to CSV, Excel, or JSON format
Parameters:
  - format (string, required): One of "csv", "xlsx", "json"
  - output_path (string, required): Full output file path
  - market_slug (string, optional): Export only trades for this market
Returns: { file_path: string, trade_count: int, format: string }
```

Maps to: `reporting.report_data.export_to_csv/excel/json()`

### Tool: `filter_trades`

```
Purpose: Apply filters to the loaded trades and store the filtered result.
         Subsequent analysis tools operate on the filtered set.
Parameters:
  - start_date, end_date, trade_types, sides, min_pnl, max_pnl (all optional)
  - market_slug (string, optional): Limit to specific market
  - clear (bool, optional, default false): Clear all filters and reset to full dataset
Returns: { original_count: int, filtered_count: int, active_filters: dict }
```

Maps to: `filters.filter_by_date/type/side/pnl()` chained → `session.filtered_trades`

### Tool: `get_trade_details`

```
Purpose: Get detailed information about individual trades, optionally filtered
Parameters:
  - market_slug (string, optional): Filter by market
  - limit (int, optional, default 50): Max trades to return
  - offset (int, optional, default 0): Pagination offset
  - sort_by (string, optional, default "timestamp"): Sort field. Valid: "timestamp", "pnl", "cost"
  - sort_order (string, optional, default "desc"): Valid: "asc", "desc"
Returns: { trades: [ { market, timestamp, price, shares, cost, type, side, pnl } ], total: int }
```

Maps to: direct iteration on `session.filtered_trades`

---

## 5. Phase 4 — New Feature Tools

These tools implement the high-priority features from the evaluation that the MCP server should expose.

### Tool: `get_open_positions` (NEW)

```
Purpose: Calculate current open positions with unrealized PnL using latest market prices
Parameters:
  - market_slug (string, optional): Check specific market only
Returns: [ {
  market, market_slug, net_shares, side, avg_entry_price,
  current_price, unrealized_pnl, cost_basis
} ]
```

**Implementation:** New module `prediction_analyzer/positions.py`
- Group trades by market
- Calculate net share position per market (buys add, sells subtract)
- Fetch current price via `utils.data.fetch_market_details()`
- Calculate unrealized PnL: `net_shares * (current_price - avg_entry_price)`

### Tool: `get_tax_report` (NEW)

```
Purpose: Generate capital gains/losses report for tax purposes
Parameters:
  - tax_year (int, required): Tax year (e.g., 2025)
  - cost_basis_method (string, optional, default "fifo"):
    Valid: "fifo", "lifo", "average"
Returns: {
  tax_year, method, short_term_gains, short_term_losses,
  long_term_gains, long_term_losses, net_gain_loss,
  transactions: [ { market, date_acquired, date_sold, proceeds, cost_basis, gain_loss, holding_period } ]
}
```

**Implementation:** New module `prediction_analyzer/tax.py`
- Implement FIFO, LIFO, average cost basis tracking
- Classify short-term vs long-term based on holding period (1 year threshold)
- Generate per-transaction gain/loss records

### Tool: `get_drawdown_analysis` (NEW)

```
Purpose: Analyze maximum drawdown periods including duration and recovery
Parameters:
  - market_slug (string, optional): Limit to specific market
Returns: {
  max_drawdown_amount, max_drawdown_pct, peak_value, trough_value,
  drawdown_start_date, drawdown_end_date, recovery_date,
  drawdown_duration_days, recovery_duration_days,
  current_drawdown, is_in_drawdown,
  drawdown_periods: [ { start, end, amount, pct, duration_days } ]
}
```

**Implementation:** Extends existing `metrics._drawdown_metrics()` with date-aware tracking.

### Tool: `compare_periods` (NEW)

```
Purpose: Compare trading performance between two time periods
Parameters:
  - period_1_start (string, required): "YYYY-MM-DD"
  - period_1_end (string, required): "YYYY-MM-DD"
  - period_2_start (string, required): "YYYY-MM-DD"
  - period_2_end (string, required): "YYYY-MM-DD"
Returns: {
  period_1: { trades, pnl, win_rate, sharpe, avg_pnl },
  period_2: { trades, pnl, win_rate, sharpe, avg_pnl },
  changes: { pnl_change_pct, win_rate_change, sharpe_change }
}
```

**Implementation:** Filter trades by each period, calculate metrics for each, diff.

### Tool: `get_concentration_risk` (NEW)

```
Purpose: Analyze portfolio concentration and diversification across markets
Parameters: none
Returns: {
  total_markets, total_exposure,
  markets: [ { market, slug, exposure, pct_of_total, trade_count } ],
  herfindahl_index, top_3_concentration_pct
}
```

**Implementation:** New function in `prediction_analyzer/positions.py`

---

## 6. Phase 5 — Serialization & Transport Safety

### 6.1 Central serializer

```python
# prediction_mcp/serializers.py

def serialize_trade(trade: Trade) -> dict:
    """Convert Trade dataclass to JSON-safe dict"""
    return {
        "market": trade.market,
        "market_slug": trade.market_slug,
        "timestamp": trade.timestamp.isoformat(),
        "price": _safe_float(trade.price),
        "shares": _safe_float(trade.shares),
        "cost": _safe_float(trade.cost),
        "type": trade.type,
        "side": trade.side,
        "pnl": _safe_float(trade.pnl),
        "tx_hash": trade.tx_hash,
    }

def _safe_float(value: float) -> float:
    """Guard against NaN/Infinity in JSON output"""
    if value != value:  # NaN check
        return 0.0
    if value == float('inf') or value == float('-inf'):
        return 999999.99 if value > 0 else -999999.99
    return round(value, 6)

def serialize_metrics(metrics: dict) -> dict:
    """Sanitize all numeric values in metrics dict"""
    return {k: _safe_float(v) if isinstance(v, float) else v for k, v in metrics.items()}
```

### 6.2 Suppress `plt.show()` and `fig.show()` for MCP

Add a `show` parameter (default `True`) to all chart functions. The MCP tools pass `show=False`.

```python
# In each chart function signature:
def generate_simple_chart(trades, market_name, resolved_outcome=None, output_dir=None, show=True):
    ...
    if show:
        plt.show()
    plt.close()
```

---

## 7. Phase 6 — Error Handling & Validation

### 7.1 Safe tool decorator

```python
# prediction_mcp/errors.py

def safe_tool(func):
    """Wrap every MCP tool handler to catch exceptions and return structured errors"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NoTradesError:
            return {"error": "No trades loaded. Use load_trades or fetch_trades first."}
        except MarketNotFoundError as e:
            markets = [s for s in get_available_market_slugs()]
            return {
                "error": str(e),
                "available_markets": markets[:20],
                "hint": "Use list_markets to see all available market slugs."
            }
        except InvalidFilterError as e:
            return {"error": str(e), "hint": "Check parameter formats. Dates: YYYY-MM-DD. Types: Buy, Sell."}
        except Exception as e:
            logging.exception("Unhandled error in MCP tool")
            return {"error": f"Internal error: {type(e).__name__}: {str(e)}"}
    return wrapper
```

### 7.2 Input validators

```python
# prediction_mcp/validators.py

VALID_TRADE_TYPES = ["Buy", "Sell"]
VALID_SIDES = ["YES", "NO"]
VALID_CHART_TYPES = ["simple", "pro", "enhanced"]
VALID_EXPORT_FORMATS = ["csv", "xlsx", "json"]
VALID_SORT_FIELDS = ["timestamp", "pnl", "cost"]
VALID_COST_BASIS_METHODS = ["fifo", "lifo", "average"]

def validate_enum(value: str, valid_values: list, param_name: str):
    """Validate a string parameter against allowed values"""
    if value not in valid_values:
        raise InvalidFilterError(
            f"Invalid {param_name}: '{value}'. Valid values: {valid_values}"
        )

def validate_date(date_str: str, param_name: str) -> str:
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise InvalidFilterError(
            f"Invalid {param_name}: '{date_str}'. Expected format: YYYY-MM-DD (e.g., 2025-01-15)"
        )

def validate_market_slug(slug: str, available_slugs: list):
    """Validate market slug exists"""
    if slug not in available_slugs:
        raise MarketNotFoundError(
            f"Market '{slug}' not found. Use list_markets to see available markets."
        )
```

---

## 8. Phase 7 — Testing

### 8.1 Unit tests for each tool

```
tests/mcp/
├── test_data_tools.py       # load_trades, fetch_trades, list_markets
├── test_analysis_tools.py   # summaries, metrics, breakdown
├── test_filter_tools.py     # filter application and clearing
├── test_chart_tools.py      # chart generation (file output, no show)
├── test_export_tools.py     # CSV/Excel/JSON export
├── test_portfolio_tools.py  # open positions, concentration
├── test_tax_tools.py        # capital gains, cost basis methods
├── test_serializers.py      # NaN/Infinity, datetime, Trade serialization
├── test_validators.py       # enum, date, market slug validation
├── test_errors.py           # safe_tool decorator, structured error responses
└── test_transport.py        # stdio end-to-end, no stdout leaks
```

### 8.2 Transport safety test

```python
def test_no_stdout_writes():
    """Verify no tool writes to stdout (would corrupt stdio transport)"""
    import io, contextlib
    stdout_capture = io.StringIO()
    with contextlib.redirect_stdout(stdout_capture):
        # Run every tool with sample data
        ...
    assert stdout_capture.getvalue() == "", f"Stdout pollution detected: {stdout_capture.getvalue()}"
```

### 8.3 LLM-style input tests

Test each tool with inputs an LLM might realistically send:
- Wrong parameter names (e.g., `market` instead of `market_slug`)
- Display-friendly enum values (e.g., `"buy"` lowercase)
- Missing required parameters
- Empty strings, null values
- `NaN` and `Infinity` as numeric inputs

---

## 9. Phase 8 — Documentation & Packaging

### 9.1 Claude Desktop / Claude Code configuration

```json
{
  "mcpServers": {
    "prediction-analyzer": {
      "command": "python",
      "args": ["-m", "prediction_mcp"],
      "env": {
        "LIMITLESS_API_KEY": "lmts_your_key_here"
      }
    }
  }
}
```

### 9.2 Package entry point

```python
# prediction_mcp/__main__.py
from .server import main
main()
```

### 9.3 setup.py extras

```python
extras_require={
    "mcp": [
        "mcp>=1.0.0",
        # all core deps inherited
    ],
}
```

---

## 10. Tool Inventory

### Core Tools (wrapping existing features)

| # | Tool Name | Category | Maps To |
|---|-----------|----------|---------|
| 1 | `load_trades` | Data | `trade_loader.load_trades()` |
| 2 | `fetch_trades` | Data | `utils.data.fetch_trade_history()` |
| 3 | `list_markets` | Data | `trade_filter.get_unique_markets()` |
| 4 | `get_trade_details` | Data | Direct iteration + sort |
| 5 | `filter_trades` | Filter | `filters.filter_by_*()` chain |
| 6 | `get_global_summary` | Analysis | `pnl.calculate_global_pnl_summary()` |
| 7 | `get_market_summary` | Analysis | `pnl.calculate_market_pnl_summary()` |
| 8 | `get_market_breakdown` | Analysis | `pnl.calculate_market_pnl()` |
| 9 | `get_advanced_metrics` | Analysis | `metrics.calculate_advanced_metrics()` |
| 10 | `generate_chart` | Chart | `charts.*.generate_*_chart()` |
| 11 | `generate_dashboard` | Chart | `charts.global_chart.generate_global_dashboard()` |
| 12 | `export_trades` | Export | `reporting.report_data.export_to_*()` |

### New Feature Tools

| # | Tool Name | Category | New Module |
|---|-----------|----------|------------|
| 13 | `get_open_positions` | Portfolio | `prediction_analyzer/positions.py` |
| 14 | `get_concentration_risk` | Portfolio | `prediction_analyzer/positions.py` |
| 15 | `get_drawdown_analysis` | Risk | `prediction_analyzer/drawdown.py` |
| 16 | `compare_periods` | Analysis | `prediction_analyzer/comparison.py` |
| 17 | `get_tax_report` | Tax | `prediction_analyzer/tax.py` |

**Total: 18 tools** (including `get_provider_breakdown`)

---

## 11. Implementation Checklist

Per the MCP_DEVELOPMENT.md checklist:

### Tool Descriptions
- [x] Every parameter listed with type, purpose, and valid values
- [x] Return type semantics documented (added return shapes to get_trade_details, export_trades, generate_chart, generate_dashboard)
- [x] No description says "see docs" — all info inline
- [x] Parameter names match what description leads consumer to expect
- [x] Consistent naming across all 18 tools

### Input Validation
- [x] Enum values validated (trade_types, sides, chart_type, format, cost_basis_method, sort_field, sort_order)
- [x] Case-insensitive normalization for trade_types ("buy" → "Buy") and sides ("yes" → "YES")
- [x] Numeric inputs checked for NaN/Infinity (min_pnl, max_pnl, limit via `validate_numeric`)
- [x] Market slugs verified to exist (with available list in error)
- [x] Dates validated as YYYY-MM-DD
- [x] Required vs optional parameters enforced
- [x] Sort order validated (was previously unvalidated — invalid values silently defaulted)
- [x] Path traversal prevention on export_trades output_path

### Error Handling
- [x] `@safe_tool` decorator on every handler
- [x] Error responses include valid options and expected formats
- [x] No error says "see the docs"
- [x] Unhandled exceptions never crash the server

### Serialization
- [x] All responses JSON-serializable
- [x] `datetime` → `.isoformat()`
- [x] `float` → `_safe_float()` (NaN/Infinity guard)
- [x] `Trade` dataclass → dict via `serialize_trade()`
- [x] `pd.DataFrame` → `.to_dict("records")`
- [x] Tested with real trade data

### Transport Safety
- [x] No `print()` in any execution path (all replaced with `logging`)
- [x] `plt.show()` / `fig.show()` suppressed (`show=False`)
- [x] All debug output to stderr
- [x] Existing chart/loader code audited for stdout writes

### Code Correctness
- [x] Every attribute access verified against Trade dataclass definition (13 fields)
- [x] Every function call uses correct parameter names from real signatures
- [x] All imports verified to resolve
- [x] Python 3.8+ compatible (no `X | None` syntax)
- [x] `dict` vs dataclass handling correct throughout

### Integration Testing
- [x] Each tool tested with realistic LLM inputs
- [x] Tools tested with wrong parameter names
- [x] Tools tested with edge cases (empty, null, boundary values)
- [x] NaN/Infinity inputs tested and rejected with clear errors
- [x] Case-insensitive enum inputs tested (normalized, not rejected)
- [x] Full stdio transport tested end-to-end
- [x] No stdout pollution test passes

---

## Implementation Order

1. **Phase 1** (Internal API Hardening) — ~2-3 hours
   - Replace all `print()` with logging
   - Add `Trade.to_dict()`, `_safe_float()`
   - Add custom exception classes
   - Add `show` parameter to chart functions

2. **Phase 2** (MCP Skeleton) — ~1-2 hours
   - Create `prediction_mcp/` package structure
   - Set up MCP server with stdio transport
   - Implement session state

3. **Phase 3** (Core Tools) — ~3-4 hours
   - Implement 12 core tools wrapping existing functions
   - Add serializers and validators
   - Add `@safe_tool` decorator

4. **Phase 4** (New Features) — ~4-6 hours
   - Implement `positions.py` (open positions, concentration)
   - Implement `tax.py` (FIFO/LIFO/average cost basis)
   - Implement `drawdown.py` (detailed drawdown analysis)
   - Implement `comparison.py` (period comparison)
   - Wire up as MCP tools

5. **Phase 5-6** (Safety & Errors) — ~1-2 hours
   - Audit all serialization paths
   - Finalize error messages with recovery hints

6. **Phase 7** (Testing) — ~2-3 hours
   - Write tool unit tests
   - Write transport safety tests
   - Write LLM-style input tests

7. **Phase 8** (Packaging) — ~1 hour
   - Add `__main__.py` entry point
   - Update `setup.py` / `pyproject.toml`
   - Write MCP server configuration examples
