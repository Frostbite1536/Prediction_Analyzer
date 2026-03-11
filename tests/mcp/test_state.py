# tests/mcp/test_state.py
"""Tests for MCP session state."""

from prediction_mcp.state import SessionState, session
from .conftest import make_trades


class TestSessionState:
    def test_initial_state(self):
        s = SessionState()
        assert s.trades == []
        assert s.filtered_trades == []
        assert s.active_filters == {}
        assert s.source is None

    def test_has_trades_false_when_empty(self):
        s = SessionState()
        assert s.has_trades is False

    def test_has_trades_true(self):
        s = SessionState()
        s.trades = make_trades(1)
        assert s.has_trades is True

    def test_trade_count(self):
        s = SessionState()
        assert s.trade_count == 0
        s.trades = make_trades(5)
        assert s.trade_count == 5

    def test_clear(self):
        s = SessionState()
        s.trades = make_trades(3)
        s.filtered_trades = list(s.trades)
        s.active_filters = {"sides": ["YES"]}
        s.source = "test"
        s.clear()
        assert s.trades == []
        assert s.filtered_trades == []
        assert s.active_filters == {}
        assert s.source is None

    def test_module_singleton(self):
        """The module-level session should be a SessionState instance."""
        assert isinstance(session, SessionState)
