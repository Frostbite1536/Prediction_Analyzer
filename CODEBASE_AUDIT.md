# Codebase Audit Report

**Date**: 2026-03-10
**Scope**: Full audit of `prediction_analyzer/` package — 16 files reviewed

---

## Critical Bugs

### 1. ~~Limitless Provider: Breakeven PnL Sentinel Bug~~ — ALREADY FIXED
**File**: `prediction_analyzer/providers/limitless.py:82,122`

The code correctly uses `has_pnl = "pnl" in raw and raw["pnl"] is not None` and `pnl_is_set=has_pnl`. No action needed.

### 2. ~~Kalshi `_apply_position_pnl` Never Sets `pnl_is_set`~~ — ALREADY FIXED
**File**: `prediction_analyzer/providers/kalshi.py:202`

The code already sets `t.pnl_is_set = True` after distributing position PnL. No action needed.

---

## Correctness Issues

### 3. Sortino Ratio Uses Population Variance (ddof=0)
**File**: `prediction_analyzer/metrics.py:146`

The Sortino ratio uses `np.mean(downside_diffs ** 2)` (population variance, ddof=0), while the Sharpe ratio on line 139 correctly uses `np.std(arr, ddof=1)` (Bessel's correction). This inconsistency slightly inflates the Sortino ratio.

**Fix**: Use `ddof=1` for the downside deviation calculation to match the Sharpe ratio convention.

### 4. `filter_by_date` Adds 24 Hours to Arbitrary Datetimes
**File**: `prediction_analyzer/filters.py`

When `end` is a `datetime` object, the function adds `timedelta(days=1)` to make it inclusive. This is only correct if the datetime represents midnight. Passing `datetime(2025, 3, 10, 15, 0)` silently extends the range by a full day.

**Fix**: Only add the extra day when `end` is a `date` (not `datetime`), or document the midnight assumption.

### 5. `_empty_metrics` Returns 0.0 for Ratios
**File**: `prediction_analyzer/metrics.py`

A Sharpe/Sortino ratio of `0.0` is meaningful (mean equals risk-free rate), but it's used here to mean "not enough data." Consumers cannot distinguish "no data" from "genuinely zero."

**Fix**: Return `None` or `float('nan')` for insufficient-data cases.

### 6. Manifold: Zero-Amount Trades Classified as "Buy"
**File**: `prediction_analyzer/providers/manifold.py:136`

```python
type="Buy" if amount > 0 else ("Sell" if amount < 0 else "Buy")
```

A zero-amount trade is classified as a Buy. It should be flagged or skipped.

### 7. Hardcoded `$` in Market Breakdown Reports
**File**: `prediction_analyzer/reporting/report_text.py:62,127-128`

The per-market breakdown and top-markets section always use `$` even for non-USD trades (e.g., MANA). The global summary correctly uses `cur_symbol`, but the detail sections do not.

---

## Consistency Issues

### 8. Grouping Key Inconsistency (3 Different Strategies)

| Location | Grouping Key |
|---|---|
| `trade_filter.py` `group_trades_by_market` | `trade.market_slug or trade.market or "unknown"` |
| `pnl.py` `calculate_market_pnl` | `trade.market_slug` |
| `report_data.py` `export_to_excel` | `trade.market` (title) |

Three different grouping strategies for what should be the same concept. If `market_slug` is empty or two markets share a title, results will silently diverge.

**Fix**: Standardize on `market_slug` everywhere and ensure it is always populated.

### 9. `vars(t)` Used Instead of `Trade.to_dict()`
**File**: `prediction_analyzer/reporting/report_data.py:25,45,79`

The `Trade` class has a `to_dict()` method that sanitizes NaN/Inf values. Using `vars()` bypasses this, so NaN or Inf values could end up in CSV/Excel/JSON exports. (`NaN` in JSON is not valid JSON per the spec.)

**Fix**: Replace `vars(t)` with `t.to_dict()`.

---

## Code Smells & Fragility

### 10. Timezone Handling: Naive-UTC Pattern
**Files**: `filters.py`, `trade_loader.py`, `tax.py`

All datetimes are converted to UTC then stripped of tzinfo via `replace(tzinfo=None)`. This is internally consistent but fragile — there is no type-level enforcement that all datetimes are UTC. If any code path creates a naive datetime in local time, comparisons will be silently wrong.

### 11. Redundant `hasattr(t.timestamp, 'isoformat')` Checks
**Files**: `trade_loader.py:58`, `trade_filter.py:62`, `report_data.py:82`

`Trade.timestamp` is typed as `datetime`, which always has `.isoformat()`. The `_parse_timestamp` function guarantees this. These checks are dead code suggesting historical uncertainty about the type.

### 12. Exception Swallowing (Silent `except Exception: pass`)
**Files**: All four providers (`polymarket.py`, `limitless.py`, `manifold.py`, `kalshi.py`) plus `trade_loader.py`

At least 8 bare `except Exception: pass` blocks across the codebase, primarily in `fetch_market_details` and `_fetch_market_metadata`. These make debugging network and data issues extremely difficult.

**Fix**: At minimum, log the exception. Prefer `logger.exception("...")` or `logger.warning("...", exc_info=True)`.

### 13. N+1 Query Problem in Market Metadata Fetching
**Files**: `manifold.py:39-57`, `kalshi.py:203-221`

Each unique market triggers a separate HTTP request. For a user with bets on 500 markets, this is 500 sequential HTTP requests with no batching or parallelism.

### 14. Kalshi Thread Safety
**File**: `prediction_analyzer/providers/kalshi.py`

`_load_credentials` sets `self._private_key` and `self._base_url` as instance state on what is a singleton. If two threads call `fetch_trades` with different credentials, they will clobber each other's state.

---

## Minor Issues

| Issue | File | Description |
|---|---|---|
| Placeholder author | `__init__.py` | `__author__ = "Your Name"` never updated |
| Inference docstring wrong | `inference.py:15` | Says threshold default is 0.5, actual is 0.85 |
| List instead of set | `inference.py` | `trade.type in ["Claim", "Won", "Loss"]` should be a set |
| Tax lot mutation | `tax.py:124` | `lot["shares"] -= matched_shares` mutates in-place |
| `_sign_request` timezone | `kalshi.py:74` | Uses `datetime.now()` without timezone (works by accident) |
| Provider ABC enforcement | `providers/base.py` | Class attributes (`name`, etc.) not enforced at definition time |

---

## Prioritized Fix List

1. **P0 — Data Correctness**: Fix Limitless breakeven PnL bug (#1) and Kalshi `pnl_is_set` bug (#2)
2. **P1 — Correctness**: Fix Sortino ddof inconsistency (#3), hardcoded `$` (#7), `vars()` vs `to_dict()` (#9)
3. **P1 — Consistency**: Standardize grouping keys (#8)
4. **P2 — Robustness**: Replace exception swallowing with logging (#12), fix `filter_by_date` edge case (#4)
5. **P3 — Performance**: Batch market metadata requests (#13)
6. **P3 — Code Quality**: Remove dead `hasattr` checks (#11), fix minor issues
