# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-03-12

### Added
- GUI: Trade Browser tab with sortable treeview columns and market search
- GUI: Portfolio tab with open positions, concentration risk (HHI), and drawdown analysis
- GUI: Tax Report tab with FIFO/LIFO/average cost basis and wash sale detection
- GUI: Side filter (YES/NO) in Filters tab
- GUI: Period comparison dialog for comparing two date ranges
- GUI: JSON export support alongside CSV and Excel
- GUI: Keyboard shortcuts (Ctrl+O, Ctrl+S, Ctrl+F, Ctrl+Q)
- GUI: Currency and provider breakdowns in Global Summary

### Fixed
- GUI: Fixed compare_periods() dict key mismatches (total_trades→trades, total_pnl→pnl, sharpe_ratio→sharpe)
- GUI: Fixed concentration risk pct_of_total key (was exposure_pct)
- GUI: Fixed drawdown period date keys (start_date/end_date→start/end)
- GUI: Fixed HHI thresholds from 0-1 scale to correct 0-10000 scale
- GUI: Fixed empty date validation in period comparison dialog
- GUI: Replaced redundant manual provider calculation with API's by_source data

## [1.0.0] - 2026-03-10

### Added
- Multi-provider support: Limitless Exchange, Polymarket, Kalshi, Manifold Markets
- Provider auto-detection from API key prefix and file field signatures
- FIFO PnL calculator for providers without native PnL (Polymarket, Manifold)
- MCP server with 18 tools across 7 modules (stdio + SSE transports)
- FastAPI web application with JWT authentication
- SQLite session persistence for the MCP server
- Interactive CLI menu system for novice users
- Tkinter desktop GUI with provider selection
- Four chart types: simple (matplotlib), pro (Plotly), enhanced, global dashboard
- Advanced trading metrics: Sharpe, Sortino, drawdown, profit factor, streaks
- Portfolio tools: open positions, concentration risk, drawdown analysis, period comparison
- Tax reporting with FIFO/LIFO/average cost basis methods
- CSV, XLSX, and JSON export
- LLM-friendly error handling with recovery hints
- Input validation with case normalization for LLM agents
- NaN/Infinity sanitization across all serialization boundaries

### Security
- Security headers middleware (X-Frame-Options, X-Content-Type-Options, HSTS, etc.)
- Per-IP rate limiting with key eviction (5 req/min auth, 60 req/min general)
- 10 MB file upload limit with SHA-256 deduplication
- Argon2 password hashing (minimum 8 characters)
- SECRET_KEY auto-generated in dev, required in production
- Kalshi RSA private key cleared from memory after use
- `Numeric(18,8)` for all DB monetary columns (replacing Float)
- `decimal.Decimal` accumulation for cumulative PnL
- CORS with restricted methods/headers
- All endpoints authenticated (including `/trades/providers`)
- API keys never logged; only env var names in error messages
