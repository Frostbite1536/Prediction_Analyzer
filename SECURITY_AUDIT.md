# Security & Code Quality Audit Report

**Date:** 2026-03-10
**Scope:** Full repository audit addressing authentication, data parsing, math precision, API security, and dependency management.

---

## Executive Summary

The codebase is well-structured with good separation of concerns, comprehensive test coverage (36 test files), and several security best practices already in place. This audit identifies **5 high-severity**, **8 medium-severity**, and **6 low-severity** findings across 6 audit categories.

---

## 1. Authentication & Key Management

### 1.1 Findings

| ID | Severity | File | Finding |
|----|----------|------|---------|
| AUTH-1 | **HIGH** | `api/config.py:17` | Default `SECRET_KEY` is a readable string. While there is a runtime guard that blocks production use, the development default is predictable and could be exploited if someone deploys without setting `ENVIRONMENT=production`. |
| AUTH-2 | **LOW** | `providers/polymarket.py:44` | Wallet address prefix (first 10 chars) is logged: `logger.info("Downloading Polymarket trade history for %s...", api_key[:10])`. Wallet addresses are public on-chain so this is low risk, but establishes a pattern that could be copied for private keys. |
| AUTH-3 | **GOOD** | `.gitignore:69` | `.env` is properly gitignored. |
| AUTH-4 | **GOOD** | `.gitignore:66` | `*.pem` files (Kalshi RSA keys) are properly gitignored. |
| AUTH-5 | **GOOD** | `utils/auth.py` | API keys are never logged, printed, or written to files. Error messages in `__main__.py` only show env var *names*, not values. |
| AUTH-6 | **GOOD** | `api/services/auth_service.py:19` | Uses Argon2 for password hashing (modern, memory-hard algorithm). |

### 1.2 JWT Implementation Review

| ID | Severity | File | Finding |
|----|----------|------|---------|
| JWT-1 | **GOOD** | `api/services/auth_service.py:55-59` | Tokens include `exp`, `iat`, `iss`, and `aud` claims. |
| JWT-2 | **GOOD** | `api/services/auth_service.py:79-84` | Token decoding validates `issuer` and `audience`. |
| JWT-3 | **GOOD** | `api/services/auth_service.py:90` | All JWT exceptions are caught (`InvalidTokenError`, `DecodeError`, `ExpiredSignatureError`). |
| JWT-4 | **MEDIUM** | `api/services/auth_service.py:19` | Algorithm is `HS256` (symmetric). This is fine for a single-server deployment but doesn't support key rotation or asymmetric verification. Consider documenting this trade-off. |
| JWT-5 | **GOOD** | `api/dependencies.py:41-59` | `get_current_user` validates token, checks user exists, and verifies `is_active` status. |

### 1.3 Kalshi RSA Key Handling

| ID | Severity | File | Finding |
|----|----------|------|---------|
| KALSHI-1 | **GOOD** | `providers/kalshi.py:59-62` | Private key loaded from file, never logged or serialized. |
| KALSHI-2 | **GOOD** | `providers/kalshi.py:79-88` | RSA-PSS signing uses `DIGEST_LENGTH` salt per Kalshi docs. |
| KALSHI-3 | **LOW** | `providers/kalshi.py:36` | Private key stored as instance attribute `self._private_key`. If the provider object is serialized or introspected in a debug session, the key could leak. Consider using a `__slots__` or marking as non-serializable. |

---

## 2. FastAPI & Web Security

### 2.1 CORS Configuration

| ID | Severity | File | Finding |
|----|----------|------|---------|
| CORS-1 | **GOOD** | `api/main.py:70-85` | CORS properly handles wildcard vs. explicit origins. When `ALLOWED_ORIGINS="*"`, credentials are disabled (per CORS spec). |
| CORS-2 | **LOW** | `api/main.py:83-84` | `allow_methods=["*"]` and `allow_headers=["*"]` are overly permissive. Consider restricting to the methods/headers actually used. |

### 2.2 Rate Limiting

| ID | Severity | File | Finding |
|----|----------|------|---------|
| RATE-1 | **GOOD** | `api/main.py:38-39` | Auth endpoints limited to 5 req/min, general to 60 req/min. |
| RATE-2 | **MEDIUM** | `api/main.py:37` | In-memory rate store (`defaultdict(list)`) is not shared across workers/processes. If running with multiple Uvicorn workers, rate limits are per-worker. |
| RATE-3 | **MEDIUM** | `api/main.py:37` | Rate store grows unbounded over time. While timestamps are pruned per-key on each request, keys for clients that stop sending requests are never evicted. In a long-running server with many unique IPs, this is a slow memory leak. |

### 2.3 Endpoint Security

| ID | Severity | File | Finding |
|----|----------|------|---------|
| API-1 | **GOOD** | `api/routers/trades.py` | All trade endpoints require `get_current_user` authentication. |
| API-2 | **GOOD** | `api/services/trade_service.py:217-220` | Trade access is scoped by `user_id` — users can only access their own trades. |
| API-3 | **GOOD** | `api/routers/trades.py:174-181` | Filename sanitization uses regex to prevent path traversal in export filenames. |
| API-4 | **GOOD** | All DB queries use SQLAlchemy ORM parameterized queries — no raw SQL injection risk. |
| API-5 | **HIGH** | `api/routers/trades.py:76` | No file upload size limit. The `process_upload` reads entire file into memory (`content = await file.read()` at `trade_service.py:76`). A malicious user could upload a multi-GB file to cause OOM. |
| API-6 | **MEDIUM** | `api/routers/trades.py:100-111` | `/trades/providers` endpoint has no authentication — anyone can list available providers. Low risk but inconsistent with the rest of the API. |

### 2.4 Input Validation

| ID | Severity | File | Finding |
|----|----------|------|---------|
| VAL-1 | **GOOD** | `api/schemas/user.py:13-14` | Username: 3-50 chars; password: 6-100 chars; email validated via `EmailStr`. |
| VAL-2 | **MEDIUM** | `api/schemas/user.py:14` | Minimum password length of 6 is weak by modern standards. NIST recommends minimum 8 characters. No complexity requirements enforced. |

---

## 3. Data Parsing & Type Safety

### 3.1 NaN/Infinity Handling

| ID | Severity | File | Finding |
|----|----------|------|---------|
| NAN-1 | **GOOD** | `trade_loader.py:18-33` | `sanitize_numeric()` properly converts NaN → 0.0, Inf → ±999999.99. |
| NAN-2 | **GOOD** | `prediction_mcp/serializers.py:20-42` | Recursive JSON sanitization handles nested structures. |
| NAN-3 | **GOOD** | `prediction_mcp/validators.py:107-115` | Filter parameters are validated for NaN/Infinity. |
| NAN-4 | **LOW** | `trade_loader.py:33` vs `metrics.py:78` | Infinity is capped to 999999.99 in one place and 999.99 in another. Inconsistent sentinel values could cause confusion. |

### 3.2 External API Response Parsing

| ID | Severity | File | Finding |
|----|----------|------|---------|
| PARSE-1 | **GOOD** | All providers | Use `.get()` with defaults for optional fields — graceful degradation. |
| PARSE-2 | **MEDIUM** | `providers/manifold.py:34` | `return resp.json()["id"]` — `KeyError` would propagate uncaught if Manifold API changes response format. |
| PARSE-3 | **LOW** | `providers/limitless.py:81-90` | Hardcoded divisor of 1,000,000 for USDC micro-units without validation that incoming values are actually in micro-units. |
| PARSE-4 | **MEDIUM** | `providers/kalshi.py:248-268` | Multiple `except (ValueError, TypeError): continue` blocks silently skip malformed data without logging which fields failed. |
| PARSE-5 | **GOOD** | `trade_loader.py:74-142` | Timestamp parsing has multi-format fallback chain with logging on failure. |

### 3.3 Pydantic & Database Models

| ID | Severity | File | Finding |
|----|----------|------|---------|
| MODEL-1 | **HIGH** | `api/models/trade.py:44-46` | SQLAlchemy `Float` columns used for monetary values (price, shares, cost, pnl). IEEE 754 doubles accumulate rounding errors in financial calculations. Should use `Numeric(precision=18, scale=8)` or similar. |
| MODEL-2 | **MEDIUM** | `api/schemas/trade.py:15-20` | No validation constraints on numeric fields. Price should be `Field(ge=0, le=1)`, shares `Field(ge=0)`, cost `Field(ge=0)`. |

---

## 4. Math & PnL Calculations

### 4.1 Floating-Point Precision

| ID | Severity | File | Finding |
|----|----------|------|---------|
| MATH-1 | **HIGH** | `pnl.py:32` | `df["cumulative_pnl"] = df["trade_pnl"].cumsum()` — cumulative sum on floats accumulates rounding errors. For 1000+ trades, errors could exceed $1. |
| MATH-2 | **HIGH** | Entire codebase | No use of `decimal.Decimal` anywhere. All financial calculations use Python `float` (IEEE 754 double). This is a known limitation for financial software. |
| MATH-3 | **LOW** | `metrics.py:86-91` | Inconsistent rounding: `round(value, 2)` for profit_factor but `round(value, 4)` for others. No documented rounding strategy. |
| MATH-4 | **MEDIUM** | `providers/pnl_calculator.py:58` | FIFO share matching uses `<= 1e-10` as "zero" threshold — magic number without documentation or named constant. |

### 4.2 Specific Calculation Issues

| ID | Severity | File | Finding |
|----|----------|------|---------|
| CALC-1 | **GOOD** | `utils/math_utils.py:38-50` | `safe_divide()` properly handles zero denominator. |
| CALC-2 | **GOOD** | `metrics.py:105-113` | Drawdown handles edge cases (zero peak, never-positive equity). |
| CALC-3 | **LOW** | `metrics.py:78` | Profit factor capped at 999.99 — arbitrary magic number, undocumented. |

---

## 5. Dependency Management

### 5.1 Sync Between Files

| ID | Severity | File | Finding |
|----|----------|------|---------|
| DEP-1 | **MEDIUM** | `pyproject.toml` vs `requirements.txt` | Both files exist. `requirements.txt` includes `argon2-cffi>=23.1.0` and `email-validator>=2.1.0` which are not listed in `pyproject.toml`'s `[project.optional-dependencies.api]`. Someone installing via `pip install .[api]` would be missing these packages. |
| DEP-2 | **GOOD** | Both files | Version lower bounds are consistent where packages overlap (e.g., `pandas>=1.5.0`, `fastapi>=0.109.0`). |
| DEP-3 | **LOW** | `requirements.txt` | No upper version bounds. While this avoids dependency hell, a major version bump in a dependency could break the project silently. |

---

## 6. Logging & Information Disclosure

| ID | Severity | File | Finding |
|----|----------|------|---------|
| LOG-1 | **GOOD** | `logging_config.py` | Logging goes to stderr, keeping stdout clean for MCP stdio transport. |
| LOG-2 | **GOOD** | `api/routers/auth.py:77-81` | Login failure returns generic "Incorrect email or password" — no information leakage about which field was wrong. |
| LOG-3 | **GOOD** | `api/dependencies.py:41-49` | Token validation failure returns generic "Could not validate credentials". |
| LOG-4 | **GOOD** | `utils/auth.py` | API keys never logged. Only environment variable *names* mentioned in error messages. |

---

## Summary of Recommendations

### High Priority (fix before production deployment)

1. **API-5**: Add file upload size limit (e.g., 50MB max) to prevent OOM attacks:
   ```python
   content = await file.read()
   if len(content) > 50 * 1024 * 1024:
       raise ValueError("File too large (max 50MB)")
   ```

2. **MODEL-1**: Change SQLAlchemy `Float` → `Numeric(18, 8)` for monetary columns in `api/models/trade.py`.

3. **MATH-2**: Document the float precision limitation prominently. Consider using `decimal.Decimal` for PnL summation or at minimum round final outputs consistently.

4. **AUTH-1**: Consider generating a random SECRET_KEY at first startup and persisting it, rather than using a predictable default string.

5. **MATH-1**: For cumulative PnL, consider rounding after each addition or using a Kahan summation algorithm to reduce float drift.

### Medium Priority (address in next release)

1. **RATE-2/3**: Add key eviction to rate limiter; document single-worker limitation.
2. **DEP-1**: Sync `argon2-cffi` and `email-validator` into `pyproject.toml` optional dependencies.
3. **MODEL-2**: Add Pydantic field constraints for price, shares, cost.
4. **PARSE-2**: Add `KeyError` handling in Manifold provider's `resolve_market_id()`.
5. **PARSE-4**: Log which Kalshi fields failed to parse instead of silently continuing.
6. **VAL-2**: Increase minimum password length to 8 characters.
7. **API-6**: Add authentication to `/trades/providers` endpoint for consistency.
8. **MATH-4**: Extract `1e-10` to a named constant `SHARE_EPSILON`.

### Low Priority (nice to have)

1. **NAN-4**: Harmonize infinity cap values (999.99 vs 999999.99).
2. **CORS-2**: Restrict CORS methods/headers to those actually used.
3. **PARSE-3**: Validate micro-unit conversion assumptions.
4. **KALSHI-3**: Consider `__slots__` to prevent accidental serialization of private key.
5. **DEP-3**: Consider adding upper version bounds for critical dependencies.
6. **CALC-3/MATH-3**: Document rounding strategy and standardize magic numbers.

---

## What's Already Done Well

- **Password hashing**: Argon2 (best-in-class)
- **JWT**: Full claim validation with issuer/audience
- **SQL injection**: Zero risk — all queries use SQLAlchemy ORM
- **Path traversal**: Export filenames are sanitized
- **Secret management**: `.env` and `.pem` files gitignored, keys never logged
- **Error messages**: No information leakage on auth failures
- **NaN/Infinity**: Comprehensive sanitization in serializers and loaders
- **Rate limiting**: Auth endpoints have stricter limits
- **Test coverage**: 36 test files with regression tests for known bugs
- **Active user checks**: JWT validation includes `is_active` status check
- **CORS**: Correctly disables credentials with wildcard origins
