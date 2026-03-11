# CLAUDE.md — Coding Agent Guide

This file provides context for AI coding agents (Claude Code, Cursor, etc.) working on this repository.

## Quick Reference

```bash
# Install (all extras)
pip install -e ".[api,mcp,dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=prediction_analyzer --cov=prediction_mcp

# Lint
flake8 prediction_analyzer prediction_mcp

# Format
black prediction_analyzer prediction_mcp tests

# Type check
mypy prediction_analyzer prediction_mcp

# Start MCP server (stdio)
python -m prediction_mcp

# Start web API
python run_api.py
```

## Project Structure

- `prediction_analyzer/` — Core library: trade loading, PnL, charts, filters, providers, FastAPI web app
- `prediction_mcp/` — MCP server: 18 tools across 7 modules, stdio + SSE transports
- `tests/` — pytest suite: `static_patterns/` (unit), `mcp/` (integration), `api/` (API)
- `gui.py` — Tkinter desktop GUI
- `run.py` / `run_gui.py` / `run_api.py` — Entry point scripts

## Critical Invariants

These invariants MUST be preserved. Breaking them causes cascading failures:

1. **Trade dataclass has exactly 13 fields** (in `trade_loader.py`):
   `market, market_slug, timestamp, price, shares, cost, type, side, pnl, pnl_is_set, tx_hash, source, currency`

2. **`pnl_is_set` semantics**: `True` means provider explicitly set PnL (including legitimate zero/breakeven). `False` means unset — FIFO calculator may update it. Never overwrite `pnl_is_set=True` trades.

3. **Currency separation in global summaries**: Top-level totals use real-money (USD/USDC) only. Play-money (MANA) is reported separately under `by_currency`. See `calculate_global_pnl_summary()`.

4. **`INF_CAP = 999999.99`** (in `trade_loader.py`): Shared ceiling for infinite values (profit factor, etc.). Import from `trade_loader`, don't hardcode.

5. **`sanitize_numeric()`**: Must be called on all float values before JSON serialization. Converts NaN → 0.0, Inf → ±INF_CAP.

6. **Provider auto-detection**: Key prefix determines provider — `lmts_` → Limitless, `0x` → Polymarket, `kalshi_` → Kalshi, `manifold_` → Manifold. File format detection uses field signatures.

7. **MCP stdio transport**: ALL logging MUST go to stderr. Any stdout output breaks the JSON-RPC protocol.

8. **DB monetary columns**: Use `Numeric(18, 8)`, never `Float`, for price/shares/cost/pnl in SQLAlchemy models.

## Common Pitfalls

- **Never log API keys or credentials**. Only log env var *names* in error messages.
- **Never use `float` cumsum** for PnL accumulation — use `decimal.Decimal` loop (see `pnl.py`).
- **Kalshi private key** must be cleared from memory after use (`self._private_key = None` in `finally` block).
- **MCP tool handlers** must be wrapped with `@safe_tool` decorator (from `prediction_mcp/errors.py`). Don't add try/except in tool handlers.
- **Filter parameters** must be validated through `prediction_mcp/validators.py` before use. LLMs send wrong cases, NaN, and garbage — the validators handle normalization.
- **Don't import from `prediction_mcp` inside `prediction_analyzer`**. The dependency is one-way: `prediction_mcp` → `prediction_analyzer`.

## Adding a New Provider

1. Create `prediction_analyzer/providers/<name>.py` implementing `MarketProvider` ABC
2. Register in `prediction_analyzer/providers/__init__.py`
3. Add config to `PROVIDER_CONFIGS` in `config.py`
4. Add env var to `utils/auth.py` mapping and `.env.example`
5. Add sample data to `data/samples/`
6. Update tests in `tests/static_patterns/test_config_integrity.py`

## Adding a New MCP Tool

1. Add tool definition to the appropriate `prediction_mcp/tools/<module>_tools.py`
2. Add handler function with `@safe_tool` decorator
3. Wire it into the module's `handle_tool()` dispatcher
4. If the tool modifies session state, add its name to `_STATE_MODIFYING_TOOLS` in `server.py`
5. Add tests in `tests/mcp/test_<module>_tools.py`

## Test Conventions

- Fixtures live in `tests/conftest.py` (shared) and `tests/mcp/conftest.py` (MCP-specific)
- Use `sample_trade_factory` fixture for creating trades with custom attributes
- MCP tool tests call `handle_tool(name, args)` directly — no network needed
- API tests use `TestClient` from FastAPI with an in-memory SQLite database
- All tests must pass with `pytest` from the project root

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `LIMITLESS_API_KEY` | Limitless Exchange API key (prefix: `lmts_`) |
| `POLYMARKET_WALLET` | Polymarket wallet address (prefix: `0x`) |
| `KALSHI_API_KEY_ID` | Kalshi API key ID |
| `KALSHI_PRIVATE_KEY_PATH` | Path to Kalshi RSA private key PEM file |
| `MANIFOLD_API_KEY` | Manifold Markets API key (prefix: `manifold_`) |
| `SECRET_KEY` | JWT signing key (auto-generated in dev, required in production) |
| `DATABASE_URL` | SQLAlchemy database URL (default: SQLite) |
| `PREDICTION_MCP_DB` | SQLite path for MCP session persistence |
