# tests/mcp/test_persistence.py
"""Tests for SQLite session persistence."""

import os
import tempfile


from prediction_mcp.persistence import SessionStore
from prediction_mcp.state import SessionState
from .conftest import make_trades


class TestSessionStore:
    def _make_store(self):
        """Create a temporary SessionStore."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        return SessionStore(path), path

    def test_create_store(self):
        store, path = self._make_store()
        try:
            assert os.path.exists(path)
        finally:
            store.close()
            os.unlink(path)

    def test_save_and_restore_trades(self):
        store, path = self._make_store()
        try:
            # Save
            session = SessionState()
            session.trades = make_trades(5)
            session.filtered_trades = list(session.trades)
            session.source = "test:fixture"
            store.save(session)

            # Restore into new session
            new_session = SessionState()
            restored = store.restore(new_session)
            assert restored is True
            assert len(new_session.trades) == 5
            assert new_session.source == "test:fixture"
            assert len(new_session.filtered_trades) == 5
        finally:
            store.close()
            os.unlink(path)

    def test_restore_empty_db(self):
        store, path = self._make_store()
        try:
            session = SessionState()
            restored = store.restore(session)
            assert restored is False
            assert session.trades == []
        finally:
            store.close()
            os.unlink(path)

    def test_save_overwrites_previous(self):
        store, path = self._make_store()
        try:
            session = SessionState()
            session.trades = make_trades(3)
            session.filtered_trades = list(session.trades)
            store.save(session)

            session.trades = make_trades(7)
            session.filtered_trades = list(session.trades)
            store.save(session)

            new_session = SessionState()
            store.restore(new_session)
            assert len(new_session.trades) == 7
        finally:
            store.close()
            os.unlink(path)

    def test_preserves_trade_fields(self):
        store, path = self._make_store()
        try:
            session = SessionState()
            session.trades = make_trades(1)
            session.filtered_trades = list(session.trades)
            store.save(session)

            new_session = SessionState()
            store.restore(new_session)
            original = session.trades[0]
            restored = new_session.trades[0]
            assert restored.market == original.market
            assert restored.market_slug == original.market_slug
            assert restored.price == original.price
            assert restored.shares == original.shares
            assert restored.cost == original.cost
            assert restored.type == original.type
            assert restored.side == original.side
            assert restored.pnl == original.pnl
            assert restored.tx_hash == original.tx_hash
        finally:
            store.close()
            os.unlink(path)

    def test_saves_active_filters(self):
        store, path = self._make_store()
        try:
            session = SessionState()
            session.trades = make_trades(2)
            session.filtered_trades = list(session.trades)
            session.active_filters = {"sides": ["YES"], "min_pnl": 0.5}
            store.save(session)

            new_session = SessionState()
            store.restore(new_session)
            assert new_session.active_filters == {"sides": ["YES"], "min_pnl": 0.5}
        finally:
            store.close()
            os.unlink(path)

    def test_context_manager(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            with SessionStore(path) as store:
                session = SessionState()
                session.trades = make_trades(3)
                session.filtered_trades = list(session.trades)
                store.save(session)

            # Re-open and verify
            with SessionStore(path) as store:
                new_session = SessionState()
                assert store.restore(new_session) is True
                assert len(new_session.trades) == 3
        finally:
            os.unlink(path)

    def test_clear_then_save(self):
        store, path = self._make_store()
        try:
            session = SessionState()
            session.trades = make_trades(5)
            session.filtered_trades = list(session.trades)
            session.source = "test"
            store.save(session)

            session.clear()
            store.save(session)

            new_session = SessionState()
            restored = store.restore(new_session)
            assert restored is False
        finally:
            store.close()
            os.unlink(path)
