# tests/static_patterns/__init__.py
"""
Static Pattern Tests

This package contains tests designed to verify code patterns and contracts
BEFORE implementing new features. These tests help ensure that:

1. All modules can be imported without errors
2. Public API signatures remain stable
3. Dataclasses maintain their structure
4. Configuration values are valid
5. Filter functions maintain their behavior contracts
6. PnL calculations produce expected outputs
7. Edge cases are handled gracefully
8. Data serialization round-trips correctly
9. Utility functions work as expected

Run these tests before making changes:
    pytest tests/static_patterns/ -v

Run with coverage:
    pytest tests/static_patterns/ --cov=prediction_analyzer
"""
