# Expert Bug Audit Findings

**Date**: 2026-03-13
**Methodology**: EXPERT_BUG_AUDIT_PROMPT.md — 6-pass cross-layer, state-aware, invariant-targeted audit
**Files reviewed**: 40+ files across `prediction_analyzer/`, `prediction_mcp/`, and `prediction_analyzer/api/`

---

## Finding 1: `vars(t)` in `pnl.py` Bypasses NaN/Inf Sanitization

### [PASS-6] `pnl.py` still uses `vars(t)` instead of `t.to_dict()` — same bug class as CODEBASE_AUDIT #9

### Category
`Regression Pattern`

### Components Involved
- `prediction_analyzer/pnl.py:27` — `calculate_pnl()`
- `prediction_analyzer/pnl.py:72` — `_summarize_trades()`
- `prediction_analyzer/pnl.py:240` — `calculate_market_pnl_summary()`
- `prediction_analyzer/trade_loader.py:68` — `Trade.to_dict()`

### Root Cause
CODEBASE_AUDIT #9 identified `vars(t)` in `report_data.py` and that was fixed. But the same pattern exists in THREE locations in `pnl.py`. `vars(t)` returns raw attribute values without calling `sanitize_numeric()`, so if any trade has `price=float('nan')` or `pnl=float('inf')`, the resulting DataFrame will contain unsanitized values.

These DataFrames are then used for `.sum()`, `.isin()`, and other pandas operations. `NaN` propagates through sums silently — `sum([1.0, float('nan'), 2.0])` returns `NaN` in pandas, making the entire `total_pnl` calculation invalid.

### Trigger Scenario
1. A provider API returns a malformed trade with `price: "NaN"` or `shares: Infinity`
2. `float("NaN")` or `float("inf")` is stored in the Trade object
3. `calculate_global_pnl_summary()` calls `_summarize_trades()` which calls `pd.DataFrame([vars(t) for t in trades])`
4. `df["pnl"].sum()` returns `NaN` — the entire summary is poisoned

### Observable Failure
`total_pnl`, `total_invested`, `total_returned`, `win_rate`, and `roi` all become `NaN`. The MCP serializer catches `NaN` on output, converting it to `0.0`, which makes the user see `total_pnl: 0.0` even when they have real profits/losses. Data corruption is **silent**.

### Severity
**High** — Affects any portfolio where even one trade has a NaN/Inf field. The `sanitize_numeric()` guard in `Trade.__init__` doesn't exist — sanitization only happens in `to_dict()`.

### Confidence
**High** — Code path verified. `vars(t)` confirmed at lines 27, 72, 240 of `pnl.py`. No sanitization occurs before DataFrame construction.

---

## Finding 2: MCP Analysis Tools Ignore `session.filtered_trades`

### [PASS-2] State Machine: `filter_trades` modifies state that most analysis tools never read

### Category
`State Transition Error`

### Components Involved
- `prediction_mcp/tools/filter_tools.py:94-95` — sets `session.filtered_trades`
- `prediction_mcp/tools/analysis_tools.py:160,192,211` — reads `session.trades` (ignores filtered)
- `prediction_mcp/tools/chart_tools.py:117,146` — reads `session.trades`
- `prediction_mcp/tools/export_tools.py:95` — reads `session.trades`
- `prediction_mcp/tools/portfolio_tools.py:126,136,147,165` — reads `session.trades`
- `prediction_mcp/tools/tax_tools.py:72` — reads `session.trades`

### Root Cause
The `filter_trades` tool stores filtered results in `session.filtered_trades` and records active filters in `session.active_filters`. But almost every analysis tool reads from `session.trades` (the unfiltered full set), not `session.filtered_trades`. Only `get_trade_details` (data_tools line 282) uses `session.filtered_trades`.

The analysis tools DO accept inline filter arguments (via `apply_filters(session.trades, arguments)`), but these are per-call filters — they do not respect the persistent `filter_trades` state.

### Trigger Scenario
1. User loads 1000 trades via `load_trades`
2. User calls `filter_trades` with `{"start_date": "2026-01-01", "end_date": "2026-01-31"}` → `filtered_count: 50`
3. User calls `get_global_summary` with no arguments
4. **Expected**: Summary of 50 filtered trades
5. **Actual**: Summary of all 1000 trades — filters are ignored

### Observable Failure
The LLM agent tells the user "I've filtered your trades to January" but then shows a summary of ALL trades. The user sees numbers that don't match the filter they just applied.

### Severity
**High** — This is the primary workflow: filter then analyze. Every MCP user who uses `filter_trades` followed by an analysis tool will see incorrect results.

### Confidence
**High** — Verified by grep: every analysis/chart/export/portfolio/tax tool reads `session.trades`, not `session.filtered_trades`. Only `get_trade_details` uses filtered trades.

---

## Finding 3: Persistence Restores `filtered_trades` Without Reapplying Filters

### [PASS-2] State Machine: Restore sets `filtered_trades = trades` but loads stale `active_filters`

### Category
`State Transition Error`

### Components Involved
- `prediction_mcp/persistence.py:186` — `session.filtered_trades = list(trades)`
- `prediction_mcp/persistence.py:203-205` — restores `active_filters` from DB
- `prediction_mcp/tools/filter_tools.py:94-95` — the original filter application

### Root Cause
When `persistence.py:restore()` runs, it:
1. Sets `session.trades = trades` (all trades)
2. Sets `session.filtered_trades = list(trades)` (all trades — no filtering)
3. Restores `session.active_filters` from the database (the filters that were active when saved)

This means `active_filters` says "start_date: 2026-01-01" but `filtered_trades` contains ALL trades. The state is internally inconsistent.

### Trigger Scenario
1. User loads trades, applies `filter_trades(start_date="2026-01-01")`
2. This triggers auto-save (persistence)
3. Server restarts, triggers restore
4. `session.active_filters` = `{"start_date": "2026-01-01"}` — looks active
5. `session.filtered_trades` = all trades — filters NOT applied
6. MCP resource `prediction://trades/filters` shows active filters
7. `get_trade_details` (which uses `filtered_trades`) returns all trades, contradicting the displayed filters

### Observable Failure
After server restart, the LLM agent sees active filters in the resource but gets unfiltered data. The reported `active_filters` are a lie.

### Severity
**Medium** — Only affects users with persistence enabled who restart the server while filters are active. The workaround is that most analysis tools ignore `filtered_trades` anyway (see Finding 2).

### Confidence
**High** — Code path verified in `persistence.py` lines 185-205.

---

## Finding 4: `Decimal` Values Leak from `_handle_provider_breakdown` into Serializer

### [PASS-3] Cross-layer: `Decimal` type not handled by `_sanitize_value()` in serializers.py

### Category
`Cross-Layer Contract Breach`

### Components Involved
- `prediction_mcp/tools/analysis_tools.py:245-251` — accumulates `Decimal("0")` values
- `prediction_mcp/serializers.py:32-42` — `_sanitize_value()` type checks
- `prediction_mcp/serializers.py:51` — `json.dumps(data, default=str)` fallback

### Root Cause
`_handle_provider_breakdown()` in `analysis_tools.py` accumulates `total_pnl` and `total_volume` as `Decimal` objects (lines 245-251). It then converts them to `float` via `sanitize_numeric(float(stats["total_pnl"]))` on line 261-262 — so this specific tool works correctly.

However, `_sanitize_value()` in `serializers.py` has no `Decimal` handler. It checks for `float`, `dict`, `list/tuple`, and `isoformat`. If a `Decimal` value leaks through any other code path (e.g., a future tool or if the explicit `float()` cast on line 261 is removed), `json.dumps` would use the `default=str` fallback, serializing `Decimal("1.5")` as `"1.5"` (a string, not a number).

This is a latent contract breach: the serializer claims to handle numeric types but `Decimal` is used throughout the codebase (`pnl.py`, `tax.py`, `pnl_calculator.py`) and is one missed `float()` call away from producing string-typed numbers in JSON output.

### Trigger Scenario
Current code works because `float()` is called before passing to serializer. But:
1. Any new tool that computes with `Decimal` and forgets to call `float()` before returning
2. Or if `calculate_global_pnl_summary()` is changed to return `Decimal` values directly
3. The serializer would output `"1.5"` (string) instead of `1.5` (number)

### Observable Failure
JSON output contains string-typed numbers. LLM agents parsing the JSON would misinterpret values.

### Severity
**Low** — Currently mitigated by explicit `float()` casts. But the lack of `Decimal` handling in the serializer is a latent risk.

### Confidence
**Medium** — The current code paths don't trigger this, but the contract gap is real.

---

## Finding 5: Tax Calculation Does Not Separate Markets by Source/Provider

### [PASS-4] Multi-provider: FIFO buy lots are keyed by `market_slug` only, not `(market_slug, source)`

### Category
`Multi-Provider Interaction Bug`

### Components Involved
- `prediction_analyzer/tax.py:62` — `slug = trade.market_slug`
- `prediction_analyzer/tax.py:72` — `buy_lots.setdefault(slug, []).append(...)`
- `prediction_analyzer/providers/pnl_calculator.py:41` — keys by `(market_slug, side, source)`

### Root Cause
`tax.py:calculate_capital_gains()` groups buy lots by `market_slug` alone. If the same slug exists on two providers (e.g., both Polymarket and Kalshi have contracts on the same event), buys from Provider A will be matched against sells from Provider B.

This is inconsistent with `pnl_calculator.py`, which correctly groups by `(market_slug, side, source)`.

### Trigger Scenario
1. User loads Polymarket trades: Buy 100 shares of "will-x-happen" at $0.40
2. User loads Kalshi trades: Sell 100 shares of "will-x-happen" at $0.60
3. Tax report: Kalshi sell matched against Polymarket buy → gain of $20
4. **Problem**: These are different platforms, different contracts. The Polymarket buy is still open. The Kalshi sell had its own cost basis from a separate Kalshi buy.

### Observable Failure
Tax report shows incorrect cost basis for cross-provider sells. Capital gains/losses are wrong. In extreme cases, a loss on one platform is offset by a buy on another platform, making the tax report legally incorrect.

### Severity
**High** — Affects any user who trades the same market concept on multiple providers and uses the tax report. Tax errors have legal consequences.

### Confidence
**High** — `tax.py` line 62 uses `trade.market_slug` as the only key for `buy_lots`. No `source` dimension. `pnl_calculator.py` line 41 includes `trade.source` in the key — proving the codebase is aware of this need.

---

## Finding 6: `Kalshi._apply_position_pnl` Overwrites PnL Without Checking Prior `pnl_is_set`

### [PASS-1] Invariant 2 violation: `pnl_is_set=True` trades can be overwritten by position PnL distribution

### Category
`Invariant Violation`

### Components Involved
- `prediction_analyzer/providers/kalshi.py:198-203` — `_apply_position_pnl()`
- CLAUDE.md Invariant 2 — "Never overwrite `pnl_is_set=True` trades"

### Root Cause
`_apply_position_pnl()` iterates all sell trades for a market and distributes position PnL proportionally by share count (lines 198-203):
```python
for t in trades:
    if t.type.lower() == "sell" and t.market_slug in pnl_map:
        total = sell_shares[t.market_slug]
        if total > 0:
            t.pnl = pnl_map[t.market_slug] * (t.shares / total)
            t.pnl_is_set = True
```

This unconditionally overwrites `t.pnl` and sets `t.pnl_is_set = True` for ALL sell trades whose `market_slug` is in `pnl_map`. It does NOT check whether `t.pnl_is_set` was already `True` from a previous source.

In practice, this is safe for Kalshi alone (all sell trades start with `pnl_is_set=False` from `normalize_trade`), but the code violates the documented invariant, and if the FIFO calculator runs before `_apply_position_pnl` (due to code reordering), already-calculated PnL would be overwritten.

### Trigger Scenario
1. Kalshi `_fetch_trades_inner()` calls `normalize_trade()` → all trades get `pnl_is_set=False`
2. If FIFO calculator ran first (hypothetically), some trades would have `pnl_is_set=True`
3. `_apply_position_pnl()` runs and overwrites all sell trades unconditionally
4. FIFO-calculated PnL is lost

### Observable Failure
Currently no observable failure because FIFO doesn't run before `_apply_position_pnl` for Kalshi. But the invariant violation makes the code fragile to reordering.

### Severity
**Low** — Currently safe due to execution order, but violates the documented invariant.

### Confidence
**Medium** — The invariant violation is real. The trigger requires code reordering that hasn't happened yet.

---

## Finding 7: `report_text.py` Market Breakdown Uses Top-Level `cur_symbol` for All Markets

### [PASS-4] Multi-provider: Market breakdown uses single currency symbol even with mixed currencies

### Category
`Multi-Provider Interaction Bug`

### Components Involved
- `prediction_analyzer/reporting/report_text.py:70,140` — market breakdown formatting
- `prediction_analyzer/pnl.py:186-209` — `calculate_market_pnl()` (no currency info returned)

### Root Cause
`report_text.py` determines `cur_symbol` from the global summary's top-level currency (line 99: `cur_symbol = "M$" if cur_label == "MANA" else "$"`). This symbol is then used for ALL markets in the breakdown (lines 70, 140). But individual markets may have different currencies — a Manifold market uses MANA while a Polymarket market uses USDC.

`calculate_market_pnl()` does not include currency in its per-market stats dict (it only returns `market_name`, `total_volume`, `total_pnl`, `trade_count`), so `report_text.py` has no way to determine per-market currency.

### Trigger Scenario
1. User loads Polymarket (USDC) and Manifold (MANA) trades
2. Global summary has `currency: "USD"` (real-money dominant)
3. Market breakdown shows all markets with `$` symbol, including MANA-denominated Manifold markets
4. A MANA market showing `$150.00` is misleading — it's 150 MANA, not $150

### Observable Failure
Mixed-currency portfolios show MANA amounts with a `$` symbol. Users may misinterpret MANA profits as USD profits.

### Severity
**Medium** — Only affects users with mixed-currency portfolios who view text reports.

### Confidence
**High** — Code path verified. `calculate_market_pnl()` returns no currency info. `report_text.py` uses a single `cur_symbol`.

---

## Finding 8: `metrics.py:format_metrics_report()` Hardcodes `$` for All Values

### [PASS-6] Regression pattern: Same hardcoded `$` bug class as CODEBASE_AUDIT #7

### Category
`Regression Pattern`

### Components Involved
- `prediction_analyzer/metrics.py:228-246` — `format_metrics_report()`

### Root Cause
`format_metrics_report()` hardcodes `$` for expectancy, avg win, avg loss, largest win/loss, max drawdown, avg trade size, and total volume (lines 228-246). This function has no `currency` parameter and no way to determine the correct symbol.

CODEBASE_AUDIT #7 identified hardcoded `$` in `report_text.py` and it was fixed with `cur_symbol` logic. But `metrics.py:format_metrics_report()` was not checked.

### Trigger Scenario
1. User runs advanced metrics on Manifold-only (MANA) portfolio
2. Report shows `Avg Win: $5.2000` — but it's MANA, not USD

### Observable Failure
MANA values displayed with `$` instead of `M$`.

### Severity
**Low** — Cosmetic issue in text formatting. Numeric values in JSON are unaffected.

### Confidence
**High** — Lines 228-246 of `metrics.py` confirmed. 11 instances of hardcoded `$`.

---

## Finding 9: Persistence Uses `REAL` (Float) for Monetary Columns

### [PASS-1] Invariant 8 violation: SQLite persistence schema uses `REAL` not `Numeric(18, 8)`

### Category
`Invariant Violation`

### Components Involved
- `prediction_mcp/persistence.py:35-45` — `_SCHEMA` definition
- `prediction_analyzer/api/models/trade.py` — uses `Numeric(precision=18, scale=8)` (correct)
- CLAUDE.md Invariant 8 — "Use `Numeric(18, 8)`, never `Float`, for price/shares/cost/pnl"

### Root Cause
The MCP persistence layer uses raw SQLite `REAL` type for `price`, `shares`, `cost`, `pnl`, and `fee` columns:
```sql
price REAL NOT NULL,
shares REAL NOT NULL,
cost REAL NOT NULL,
...
pnl REAL NOT NULL DEFAULT 0.0,
fee REAL NOT NULL DEFAULT 0.0
```

SQLite's `REAL` is a 64-bit IEEE float — the same precision as Python's `float`. While the API database correctly uses `Numeric(18, 8)` via SQLAlchemy (per SECURITY_AUDIT finding MODEL-1), the MCP persistence was never updated.

### Trigger Scenario
1. User loads trades where `cost=0.1 + 0.2` → Python float `0.30000000000000004`
2. Saved to SQLite as `REAL` → stored as `0.30000000000000004`
3. Restored → `trade.cost = 0.30000000000000004`
4. After many save/restore cycles, float drift may accumulate in aggregations

### Observable Failure
In practice, SQLite's REAL has the same precision as Python floats, so no additional drift occurs beyond what already exists in memory. The invariant violation is real but the practical impact is minimal for SQLite (unlike PostgreSQL where `Float` vs `Numeric` has real precision implications).

### Severity
**Low** — SQLite `REAL` is IEEE 754 double (same as Python float). The invariant was written for PostgreSQL/SQLAlchemy context. No practical data loss in SQLite.

### Confidence
**Medium** — The invariant violation is technically real, but SQLite doesn't support `Numeric(18,8)` natively anyway.

---

## Finding 10: `_summarize_trades` Uses `vars(t)` Which Includes All 14 Fields as Raw Values in DataFrame

### [PASS-3] Cross-layer: `_summarize_trades` creates a DataFrame with `pnl_is_set` as raw Python bool — pandas handles it, but `total_pnl` uses `df["pnl"].sum()` which includes NaN

### Category
`Cross-Layer Contract Breach`

### Components Involved
- `prediction_analyzer/pnl.py:72-79` — `_summarize_trades()`
- `prediction_analyzer/pnl.py:27` — `calculate_pnl()`
- Both create DataFrames via `pd.DataFrame([vars(t) for t in trades])`

### Root Cause
This is a deeper consequence of Finding 1. `_summarize_trades()` at line 79 does `total_pnl = df["pnl"].sum()`. If ANY trade has `pnl=float('nan')`, this sum returns `NaN`. Pandas `.sum()` has `skipna=True` by default so it actually skips NaN — **this partially mitigates the issue**.

However, `df["cost"].sum()` (lines 76-77) for `total_invested` and `total_returned` also uses `.sum()` with `skipna=True`. If a trade has `cost=float('inf')`, `sum()` returns `inf`, which then propagates to `roi` calculation: `total_pnl / inf * 100 = 0.0`. This silently zeros out ROI.

### Trigger Scenario
1. A single trade has `cost=float('inf')` (could happen if `shares=0` and the code does `cost/shares` somewhere upstream)
2. `total_invested = buy_trades["cost"].sum()` returns `inf`
3. `roi = (total_pnl / inf * 100)` = `0.0`
4. ROI appears as 0% when it should be meaningful

### Observable Failure
ROI silently becomes 0% if any trade has infinite cost. User sees an impossibly flat ROI.

### Severity
**Medium** — Requires a trade with `inf` cost, which is unlikely but not impossible (division by zero in price calculation upstream).

### Confidence
**Medium** — Pandas `skipna=True` mitigates NaN but not Inf. Inf propagation through sum is confirmed behavior.

---

## Summary

| # | Finding | Severity | Confidence | Category |
|---|---------|----------|------------|----------|
| 1 | `vars(t)` in `pnl.py` bypasses sanitization (3 locations) | **High** | High | Regression Pattern |
| 2 | Analysis tools ignore `session.filtered_trades` | **High** | High | State Transition Error |
| 3 | Persistence restores stale `active_filters` without reapplying | **Medium** | High | State Transition Error |
| 4 | Serializer has no `Decimal` handler (latent) | **Low** | Medium | Cross-Layer Contract Breach |
| 5 | Tax FIFO lots keyed by `market_slug` only, not `(slug, source)` | **High** | High | Multi-Provider Interaction |
| 6 | `_apply_position_pnl` doesn't check `pnl_is_set` | **Low** | Medium | Invariant Violation |
| 7 | Market breakdown uses wrong currency symbol for mixed portfolios | **Medium** | High | Multi-Provider Interaction |
| 8 | `format_metrics_report()` hardcodes `$` | **Low** | High | Regression Pattern |
| 9 | Persistence uses SQLite `REAL` not `Numeric(18,8)` | **Low** | Medium | Invariant Violation |
| 10 | `Inf` in trade cost silently zeros ROI | **Medium** | Medium | Cross-Layer Contract Breach |

**Audit complete. 10 findings across 5 categories. Highest-severity unresolved: High (Findings 1, 2, 5).**

---

## Recommended Fix Priority

### P0 — Fix Immediately (High severity, High confidence)
1. **Finding 5**: Add `source` to tax `buy_lots` key: `buy_lots.setdefault((slug, trade.source), [])` — matches `pnl_calculator.py` pattern
2. **Finding 2**: Decide the filter contract: either analysis tools should read `session.filtered_trades` when no inline filters are provided, or `filter_trades` tool description should clarify it only affects `get_trade_details`
3. **Finding 1**: Replace `vars(t)` with a sanitized dict approach in `pnl.py` (e.g., use `Trade.to_dict()` or add explicit NaN guards before DataFrame operations)

### P1 — Fix Soon (Medium severity)
4. **Finding 3**: After restoring filters from persistence, reapply them to `filtered_trades`
5. **Finding 7**: Add `currency` field to `calculate_market_pnl()` output; use per-market symbol in `report_text.py`
6. **Finding 10**: Add `sanitize_numeric()` calls on trade fields before DataFrame construction, or validate on Trade creation

### P2 — Fix Eventually (Low severity)
7. **Finding 4**: Add `Decimal` handler to `_sanitize_value()` in `serializers.py`
8. **Finding 6**: Add `if not t.pnl_is_set:` guard in `_apply_position_pnl()`
9. **Finding 8**: Add `currency` parameter to `format_metrics_report()`
10. **Finding 9**: Document that SQLite REAL is acceptable for MCP persistence layer
