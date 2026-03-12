# Expert Bug Audit — Cross-Layer, State-Aware, Invariant-Targeted

## Preamble

This audit prompt is designed by an engineer who has read every line of the architecture documentation, all 12 state machine diagrams, the CLAUDE.md invariants, and the findings from three prior audits (QA_AUDIT_PROMPT.md, CODEBASE_AUDIT.md, SECURITY_AUDIT.md). It intentionally **does not repeat** ground already covered by those audits. Instead, it targets the classes of bugs that survive conventional per-module reviews: cross-layer contract violations, state machine transition errors, invariant drift, and semantic correctness issues that only manifest when multiple components interact.

**Prior audit coverage (DO NOT re-audit):**
- Per-module data loading, parsing, NaN/Inf handling (QA_AUDIT_PROMPT.md)
- Security headers, JWT, CORS, rate limiting, password hashing (SECURITY_AUDIT.md)
- Sortino ddof, `filter_by_date` +24h, `_empty_metrics`, hardcoded `$`, grouping key inconsistency, `vars()` vs `to_dict()`, silent `except` blocks, N+1 queries (CODEBASE_AUDIT.md)

**This audit targets what those missed:** the spaces *between* components.

---

## Persona

You are a **Systems Integrity Engineer** — not a module reviewer. You think in terms of data contracts between layers, state machine invariant violations, and emergent bugs that only appear when Component A's output becomes Component B's input under conditions neither author anticipated.

Your mental model is the data pipeline:

```
Provider API/File → Trade Objects → Session State → Filters → Calculations → Serialization → Output
```

You are hunting for bugs that live on the **arrows**, not in the boxes.

---

## Required Reading (Before You Begin)

You MUST read these files in full before writing any findings. Do not skim. The bugs you are looking for require understanding the exact contracts between these components.

| Priority | File | Why |
|----------|------|-----|
| 1 | `CLAUDE.md` | The 8 critical invariants — your checklist |
| 2 | `docs/STATE_MACHINE_DIAGRAMS.md` | All 12 state machines — your map of legal transitions |
| 3 | `ARCHITECTURE.md` | Component boundaries and data flow |
| 4 | `prediction_analyzer/trade_loader.py` | The Trade dataclass contract (14 fields exactly) |
| 5 | `prediction_analyzer/pnl.py` | PnL calculation with Decimal accumulation |
| 6 | `prediction_analyzer/providers/pnl_calculator.py` | FIFO matching logic |
| 7 | `prediction_mcp/state.py` | Session state dataclass |
| 8 | `prediction_mcp/server.py` | Tool dispatch, `_STATE_MODIFYING_TOOLS` |
| 9 | `prediction_mcp/persistence.py` | SQLite save/restore round-trip |
| 10 | `prediction_mcp/serializers.py` | JSON sanitization |
| 11 | `prediction_mcp/validators.py` | Input normalization |
| 12 | `prediction_mcp/errors.py` | `@safe_tool` decorator |
| 13 | `prediction_analyzer/providers/*.py` | All 4 providers |
| 14 | `prediction_analyzer/metrics.py` | Advanced metrics |
| 15 | `prediction_analyzer/tax.py` | Tax calculations, FIFO/LIFO, wash sales |
| 16 | `prediction_analyzer/positions.py` | Open positions, concentration risk |
| 17 | `prediction_analyzer/filters.py` | All filter functions |
| 18 | `prediction_analyzer/trade_filter.py` | Market filtering, deduplication |
| 19 | `prediction_analyzer/api/` | FastAPI app, models, routers, services |

---

## Audit Strategy: Six Targeted Passes

### Pass 1 — Invariant Violation Audit

CLAUDE.md declares 8 invariants. For EACH invariant, trace every code path that could violate it. Specifically:

**Invariant 1: Trade dataclass has exactly 14 fields.**
- Can any provider's `normalize_trade()` or `_parse_trade()` produce a Trade with a missing or extra field?
- Does the SQLite persistence round-trip in `prediction_mcp/persistence.py` restore all 14 fields? Check the `INSERT` and `SELECT` column lists. If a column was added after the schema was created, does the migration actually handle it?
- Does the API's `TradeUpload` → `Trade` conversion in `api/services/trade_service.py` map all 14 fields?
- Does `Trade.to_dict()` serialize all 14 fields? Does any consumer assume a subset?

**Invariant 2: `pnl_is_set` semantics.**
- Does `pnl_calculator.py` respect `pnl_is_set=True`? The comment says it only updates trades where `pnl == 0.0`, but the *invariant* says it should check `pnl_is_set`, not `pnl`. A trade with `pnl=0.0` and `pnl_is_set=True` (legitimate breakeven) would be incorrectly overwritten.
- After persistence round-trip, is `pnl_is_set` preserved? Check the SQLite schema — is there a `pnl_is_set` column?
- When the API stores trades via `trade_service.py`, is `pnl_is_set` stored and restored?

**Invariant 3: Currency separation in global summaries.**
- Does `calculate_global_pnl_summary()` in `pnl.py` actually exclude MANA from top-level totals?
- If a user loads only MANA trades, are the top-level totals zero or does it fall back to including MANA?
- Does the MCP tool `get_global_summary` pass through the currency separation correctly, or does it flatten/merge before returning?

**Invariant 4: `INF_CAP = 999999.99`.**
- Is `INF_CAP` imported from `trade_loader.py` everywhere it's used, or are there any remaining hardcoded values (search for `999999`, `99999`, `float('inf')` capping)?
- Does `sanitize_numeric()` use `INF_CAP` or a separate hardcoded value?

**Invariant 5: `sanitize_numeric()` before JSON serialization.**
- Are there code paths that serialize Trade data to JSON *without* going through `sanitize_numeric()` or `Trade.to_dict()`? Check: `vars(t)`, `dataclasses.asdict(t)`, manual dict construction, `t.__dict__`.
- Does the MCP serializer in `serializers.py` call `sanitize_numeric()` or does it have its own NaN/Inf handling? If both exist, can they disagree?

**Invariant 6: Provider auto-detection.**
- What happens when a file has fields from TWO providers (e.g., a user manually merges Polymarket and Kalshi exports)? Does detection pick the first match or crash?
- What happens with an API key that starts with `0x` but is actually a Limitless key that happens to start with those characters?

**Invariant 7: MCP stdout purity.**
- Search for ANY `print()` statement in `prediction_mcp/`. Even one print to stdout breaks the JSON-RPC protocol.
- Do any imported libraries (from `prediction_analyzer/`) use `print()` in error paths that could bubble up during MCP tool execution?
- Does `@safe_tool` error recovery write to stdout or stderr?

**Invariant 8: DB monetary columns use `Numeric(18, 8)`.**
- Are there any new columns added after the security audit that use `Float` instead of `Numeric`?
- Does the `fee` column use `Numeric(18, 8)`?

---

### Pass 2 — State Machine Transition Audit

Reference `docs/STATE_MACHINE_DIAGRAMS.md` for all 12 state machines. For each, look for:

**Illegal state transitions:**
- Can the MCP session reach the `Filtering` state when `trades` is empty? What happens?
- Can a user call `get_global_summary` before any trades are loaded? Does the error come from the tool handler, `@safe_tool`, or does it crash in `pnl.py`?
- What happens when `filter_trades` is called with `clear=true` and then immediately followed by an analysis tool? Is `filtered_trades` reset to `all_trades` or to an empty list?

**State corruption on error:**
- If `load_trades` fails mid-parse (e.g., corrupt XLSX), does the session retain the previous trades or is it left in a partially-loaded state?
- If `fetch_trades` network request fails on page 3 of 5, are the trades from pages 1-2 kept or discarded?
- If `filter_trades` raises a `ValidationError` (bad date format), is `active_filters` left with the new (invalid) filters or rolled back to the previous state?

**Persistence state mismatch:**
- After a tool modifies state and `persistence.save()` runs, does the persisted state match the in-memory state? Specifically: are `filtered_trades` and `active_filters` persisted, or only `trades`? If a session is restored, are previously-active filters re-applied or lost?
- If two SSE connections exist simultaneously (using `contextvars`), can `persistence.save()` from one connection overwrite the other's state?

**FIFO calculator state machine (Diagram 12):**
- The FIFO calculator groups by `(market_slug, side, source)`. What happens when `market_slug` is `None` or empty string? All trades with missing slugs would be grouped together across different markets.
- If trades are loaded in multiple batches (e.g., load Limitless file, then fetch Polymarket API), does the FIFO calculator run on the combined set or only on the new batch? If only the new batch, existing trades' PnL won't account for earlier buys.

---

### Pass 3 — Cross-Layer Contract Audit

Examine the data as it crosses each boundary in the pipeline:

**Provider → Trade Object boundary:**
- Each provider produces Trade objects with different `type` string conventions. Limitless uses `"Buy"/"Sell"`, Polymarket uses `"Buy"/"Sell"`, Kalshi uses `"Buy"/"Sell"` (mapped from `"yes"/"no"` action), Manifold uses `"Buy"/"Sell"` (mapped from amount sign). Are these *actually* consistent? Read each provider's normalization code and list the exact `type` values produced.
- Verify that `currency` is set correctly: Limitless→USDC, Polymarket→USDC, Kalshi→USD, Manifold→MANA. If any provider omits `currency`, it falls back to the dataclass default. What is that default? Is it correct for all providers?

**Trade Object → Filter boundary:**
- `filter_by_trade_type()` in `filters.py` — what exact type strings does it accept? Does it handle `"Market Buy"`, `"Limit Buy"`, `"Claim"`, `"Won"`, `"Loss"`? Do any providers produce type strings that the filter doesn't recognize?
- `filter_by_side()` — does it handle case-insensitively? If a provider produces `"Yes"` instead of `"YES"`, does the filter miss it? Check what the MCP validator normalizes vs. what the filter expects.

**Filter → PnL Calculation boundary:**
- If `filtered_trades` is passed to `calculate_global_pnl_summary()`, the summary represents the filtered subset. But `calculate_market_pnl()` is called with... what? The filtered list or the full list? If the user filters to "only sells" and then views a market summary, are the PnL numbers meaningful (sells without their corresponding buys)?

**PnL Calculation → Serialization boundary:**
- `calculate_global_pnl_summary()` returns a dict. Does the MCP serializer handle every value type in that dict? Check for: `Decimal` objects (from the accumulation), `datetime` objects, `None` values, nested dicts with mixed types.
- Specifically: if `Decimal` is used in `pnl.py` for accumulation, is the final value converted back to `float` before returning, or does a `Decimal` leak into the summary dict? If so, can the JSON serializer handle `Decimal`?

**Serialization → MCP Response boundary:**
- Does `serializers.py` handle `Decimal` type? Search for `Decimal` in that file.
- Does `@safe_tool` catch `TypeError` from JSON serialization failures (e.g., `Decimal` not serializable)?

**API Database → Trade Object boundary:**
- When the web API stores trades via `trade_service.py` and retrieves them, does the round-trip preserve `pnl_is_set`? Is there a `pnl_is_set` column in the SQLAlchemy model? If not, all restored trades would have `pnl_is_set=False`, allowing the FIFO calculator to overwrite legitimate PnL values.

---

### Pass 4 — Multi-Provider Interaction Audit

The original audit prompt was written when only Limitless existed. This pass targets bugs that only appear with 2+ providers:

**Mixed-currency calculations:**
- If a user loads both Limitless (USDC) and Kalshi (USD) trades, are `total_invested` and `total_pnl` summing USDC and USD amounts as if they were the same? The global summary should use "real-money (USD/USDC) only" per invariant 3, but are USD and USDC actually fungible in all calculations? (They are approximately equal but not identical.)
- What about `roi`? Is it `total_pnl / total_invested * 100` across mixed currencies?

**Source filtering side effects:**
- When `filter_trades` filters by source (e.g., `source="polymarket"`), are all downstream calculations (metrics, tax, positions) automatically scoped to that source? Or do some functions re-read from `session.trades` (unfiltered) instead of `session.filtered_trades`?

**Cross-provider deduplication:**
- If the same market exists on multiple platforms (e.g., "Will X happen?" on both Polymarket and Kalshi), and the user loads both, are they treated as separate markets? They should be (different `market_slug`), but what if `market_slug` collision occurs?

**Provider-specific PnL semantics:**
- Limitless provides native PnL. Polymarket and Manifold use FIFO calculator. Kalshi uses position-based PnL. When all three are loaded, `calculate_global_pnl_summary()` sums all PnL values. But are the PnL semantics compatible? (Limitless PnL might include unrealized, while FIFO is realized-only. Kalshi position PnL is settlement-based.)
- Does the global summary double-count PnL for any provider?

**Tax calculations across providers:**
- `tax.py` uses FIFO/LIFO/average cost basis. Does it respect the `source` field? If a user has buys on Polymarket and sells on Kalshi for the same market slug, does the tax calculator match them? (It shouldn't — they're different platforms.)

---

### Pass 5 — Edge Case Audit (Targeted)

These are specific, concrete scenarios. For each, trace the exact code path and determine the outcome:

**Scenario 1: Empty portfolio after filtering.**
User loads 100 trades, applies filter that matches zero. Then calls `get_global_summary`.
- Trace: `filter_trades` → `session.filtered_trades = []` → `get_global_summary` tool → `calculate_global_pnl_summary([])`.
- What does `calculate_global_pnl_summary` return for an empty list? Division by zero in ROI? Empty dict? `None`?

**Scenario 2: Single trade portfolio.**
User loads exactly one Buy trade (no corresponding Sell). Then calls `get_advanced_metrics`.
- Sharpe ratio with 1 data point? `np.std([x], ddof=1)` is `NaN` (division by zero in Bessel's correction).
- Does this propagate as NaN through the response, or is it caught?

**Scenario 3: All trades are breakeven.**
Every trade has `pnl=0.0` and `pnl_is_set=True`.
- Win rate: `winning / (winning + losing)` = `0 / 0` = division by zero?
- Or does the code handle "all breakeven" as a special case?

**Scenario 4: Trades with identical timestamps.**
Two trades on the same market at the exact same millisecond, one Buy and one Sell.
- FIFO matching depends on sort order. Is the sort stable? If Buy and Sell have the same timestamp, which comes first? This affects whether the Sell has a matching Buy in the queue.
- `filter_by_date` with `start=end=that_timestamp` — does it include both, neither, or one?

**Scenario 5: Extremely large PnL values.**
A trade with `pnl=999999999.99` (exceeds `INF_CAP`).
- `sanitize_numeric()` caps at `INF_CAP`. But what about a legitimate trade with PnL > 999999.99? Is there a scenario where a real trade is silently capped?
- Does the FIFO calculator produce values that could exceed `INF_CAP` before sanitization?

**Scenario 6: Unicode market names in MCP export.**
Market name: `"將比特幣達到$100K嗎？"` (Chinese characters with dollar sign).
- Export tool uses filename sanitization. Does the sanitizer handle CJK characters?
- Does the MCP `export_trades` tool's path traversal guard reject legitimate Unicode paths?

**Scenario 7: Session restoration with schema migration.**
User has an old SQLite persistence file without the `fee` column. Server upgrades and restores session.
- Does `persistence.py` handle the missing column via migration?
- If restoration fails, is the session left empty (clean start) or does the error propagate and crash the MCP server?

**Scenario 8: Concurrent MCP tool calls under SSE.**
Two tool calls arrive simultaneously: `filter_trades` and `get_global_summary`.
- `contextvars.ContextVar` ensures per-connection state. But does the server process requests concurrently within a single connection? If so, `filter_trades` modifying `session.filtered_trades` while `get_global_summary` is reading it creates a race condition.

**Scenario 9: Wash sale detection across providers.**
User buys on Polymarket, sells at a loss, then buys again on Manifold within 30 days. Same market concept but different platform.
- Does `tax.py` wash sale detection match across `source` values? Should it? (Legally ambiguous for prediction markets, but the code should have a defined behavior.)

**Scenario 10: Trade with zero shares.**
A provider returns a trade with `shares=0.0`.
- FIFO calculator: pushing a zero-share buy onto the queue. When a sell matches against it, `matched_shares = min(sell_shares, 0.0)` = 0.0. The sell never fully matches. Does the loop terminate?
- `positions.py` open position calculation: zero shares position — is it filtered out or does it appear in concentration risk?

---

### Pass 6 — Regression Pattern Audit

The prior audits fixed specific bugs. Look for the SAME class of bug in places they didn't check:

**Pattern: `vars(t)` bypassing `to_dict()`** (CODEBASE_AUDIT #9)
- Fixed in `report_data.py`. Search for `vars(t)`, `t.__dict__`, or `dataclasses.asdict(t)` in ALL other files. Check: `gui.py`, `api/services/trade_service.py`, `prediction_mcp/persistence.py`, `prediction_mcp/serializers.py`.

**Pattern: Hardcoded `$` symbol** (CODEBASE_AUDIT #7)
- Fixed in report_text.py top-level. Search for `"$"` in ALL files that format monetary values. Check: `gui.py`, `prediction_mcp/tools/*_tools.py`, `api/` response formatting.

**Pattern: Silent `except Exception: pass`** (CODEBASE_AUDIT #12)
- Partially fixed in providers. Search for bare `except:`, `except Exception:` followed by `pass` or `continue` in ALL files. Include `gui.py` (which is 75K lines and may have many).

**Pattern: Inconsistent `ddof`** (CODEBASE_AUDIT #3)
- Sortino vs Sharpe. Are there OTHER statistical calculations (in `metrics.py`, `comparison.py`, `tax.py`) that use `np.std()` or variance? Check that `ddof` is consistent everywhere.

**Pattern: Missing `pnl_is_set` checks** (CODEBASE_AUDIT #2)
- Kalshi fix was confirmed. But does EVERY code path that modifies `trade.pnl` check `pnl_is_set` first? Search for `\.pnl\s*=` or `\.pnl\s*+=` across the entire codebase.

---

## Output Format

For each finding, provide ALL of the following:

### [PASS-N] Finding Title
One-sentence description of the cross-layer or state-transition bug.

### Category
One of: `Invariant Violation` | `State Transition Error` | `Cross-Layer Contract Breach` | `Multi-Provider Interaction Bug` | `Edge Case Failure` | `Regression Pattern`

### Components Involved
List the 2+ files/functions whose interaction causes the bug. Example:
- `prediction_mcp/persistence.py:restore()` ↔ `prediction_analyzer/trade_loader.py:Trade`

### Root Cause
Explain WHY this bug exists — which assumption in Component A is violated by Component B.

### Trigger Scenario
A specific, reproducible sequence of operations. Example:
1. Load Limitless trades from file (100 trades, some with `pnl=0.0, pnl_is_set=True`)
2. Stop and restart MCP server (triggers persistence restore)
3. Call `get_global_summary`
4. Observe: breakeven trades now show non-zero PnL (FIFO recalculated them)

### Observable Failure
What the user sees or what data is corrupted.

### Severity
- **Critical**: Data corruption or financial calculation error affecting normal use
- **High**: Affects a common multi-provider workflow or a specific state transition
- **Medium**: Edge case requiring unusual input or rare timing
- **Low**: Theoretical or very rare, but code path exists

### Confidence
- **High**: Code path verified, failure is deterministic
- **Medium**: Code path exists, failure depends on runtime conditions
- **Low**: Suspected from code reading, needs runtime verification

---

## Exclusion Rules (Hard)

Do NOT report:
- Anything already documented in CODEBASE_AUDIT.md, SECURITY_AUDIT.md, or QA_AUDIT_PROMPT.md
- Single-module bugs that don't involve a cross-component interaction (those were covered by prior audits)
- Performance issues, code style, missing type hints, missing docstrings
- "Could be more robust" without a concrete failure scenario
- Hypothetical API format changes or library deprecations
- GUI/tkinter rendering issues (covered by FRONTEND_QA_AUDIT_PROMPT.md)
- Suggestions for new features or architectural improvements

## Stop Conditions

**Stop immediately if:**
- You have completed all 6 passes and found fewer than 2 High-confidence findings on the last pass
- You are speculating about runtime behavior without evidence from the code
- You are re-discovering findings from prior audits
- Your trigger scenarios require modifying the source code to reproduce

**When you stop**, state:
> "Audit complete. [N] findings across [M] categories. Highest-severity unresolved: [severity]."

---

## Why This Prompt Exists

This codebase was built iteratively with LLM assistance. Prior audits focused on individual modules and found real bugs that were fixed. But LLM-generated code has a characteristic failure mode: **each module works correctly in isolation, but the contracts between modules are implicit and sometimes contradictory.** This audit specifically targets those seams.

The state machine diagrams exist precisely so you can verify that the code implements the documented transitions — and nothing else. Use them.
