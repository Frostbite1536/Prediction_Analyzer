# prediction_mcp/state.py
"""
In-memory session state for the MCP server.

Maintains loaded trades, active filters, and filtered results so that
the LLM can load trades once and run multiple analyses without re-loading.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from prediction_analyzer.trade_loader import Trade


@dataclass
class SessionState:
    """Per-session in-memory state for the MCP server."""

    trades: List[Trade] = field(default_factory=list)
    filtered_trades: List[Trade] = field(default_factory=list)
    active_filters: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)  # e.g. ["limitless", "polymarket"]

    # Legacy compat property
    @property
    def source(self) -> Optional[str]:
        """Return first source or None (backward compat)."""
        return self.sources[0] if self.sources else None

    @source.setter
    def source(self, value: Optional[str]):
        """Set source (backward compat — wraps single value in list)."""
        if value is None:
            self.sources.clear()
        elif value not in self.sources:
            self.sources.append(value)

    def clear(self):
        """Reset all session state."""
        self.trades.clear()
        self.filtered_trades.clear()
        self.active_filters.clear()
        self.sources.clear()

    @property
    def trade_count(self) -> int:
        """Number of loaded trades."""
        return len(self.trades)

    @property
    def has_trades(self) -> bool:
        """Whether any trades are loaded."""
        return len(self.trades) > 0


# Module-level singleton — one state per server process.
#
# WARNING: This is safe for stdio transport (single client per process) but
# NOT safe for SSE transport where multiple clients share the process.  The
# SSE transport should use per-connection state via contextvars or middleware.
# See server.py create_sse_app() for the per-connection override.
session = SessionState()


# Per-connection session support for SSE transport.
# When running under SSE, each connection gets its own SessionState via
# a contextvar.  Tools import `session` from this module which is the
# default, but SSE handler overrides it per-connection.
import contextvars

_session_var: contextvars.ContextVar[SessionState] = contextvars.ContextVar(
    "mcp_session", default=session
)


def get_session() -> SessionState:
    """Return the current session (per-connection under SSE, singleton under stdio)."""
    return _session_var.get()
