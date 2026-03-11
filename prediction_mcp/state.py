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


# Module-level singleton — one state per server process
session = SessionState()
