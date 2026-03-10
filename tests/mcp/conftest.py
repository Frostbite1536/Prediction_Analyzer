# tests/mcp/conftest.py
"""
Shared fixtures for MCP tool tests.
"""
import os
import json
import pytest
import asyncio
from datetime import datetime

from prediction_analyzer.trade_loader import Trade
from prediction_mcp.state import session


EXAMPLE_TRADES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "example_trades.json",
)


def make_trades(count=10):
    """Create a list of sample Trade objects for testing."""
    trades = []
    for i in range(count):
        is_buy = i % 2 == 0
        trades.append(Trade(
            market=f"Market {i // 3}",
            market_slug=f"market-{i // 3}",
            timestamp=datetime(2024, 1, 1 + i),
            price=0.5 + (i * 0.01),
            shares=10.0,
            cost=5.0 + i,
            type="Buy" if is_buy else "Sell",
            side="YES" if i % 4 < 2 else "NO",
            pnl=1.0 if is_buy else -0.5,
        ))
    return trades


@pytest.fixture(autouse=True)
def reset_session():
    """Reset session state before each test."""
    session.clear()
    yield
    session.clear()


@pytest.fixture
def sample_trades():
    """Return a list of sample trades."""
    return make_trades(10)


@pytest.fixture
def loaded_session(sample_trades):
    """Set up a session with loaded trades."""
    session.trades = sample_trades
    session.filtered_trades = list(sample_trades)
    session.source = "test:fixture"
    return session
