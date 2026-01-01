# tests/conftest.py
"""
Shared fixtures and configuration for static pattern tests.

These tests are designed to run BEFORE implementing new features to ensure
existing patterns and contracts are maintained.
"""
import pytest
from datetime import datetime, timedelta
from typing import List

from prediction_analyzer.trade_loader import Trade


@pytest.fixture
def sample_trade() -> Trade:
    """Create a single sample trade with default values."""
    return Trade(
        market="Test Market",
        market_slug="test-market",
        timestamp=datetime(2024, 6, 15, 12, 0, 0),
        price=50.0,
        shares=10.0,
        cost=5.0,
        type="Buy",
        side="YES",
        pnl=0.0,
        tx_hash="0x123abc"
    )


@pytest.fixture
def sample_trade_factory():
    """Factory function to create trades with custom attributes."""
    def _create_trade(**kwargs) -> Trade:
        defaults = {
            "market": "Test Market",
            "market_slug": "test-market",
            "timestamp": datetime(2024, 6, 15, 12, 0, 0),
            "price": 50.0,
            "shares": 10.0,
            "cost": 5.0,
            "type": "Buy",
            "side": "YES",
            "pnl": 0.0,
            "tx_hash": None
        }
        defaults.update(kwargs)
        return Trade(**defaults)
    return _create_trade


@pytest.fixture
def sample_trades_list(sample_trade_factory) -> List[Trade]:
    """Create a diverse list of sample trades."""
    return [
        sample_trade_factory(
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            type="Buy",
            side="YES",
            price=45.0,
            cost=4.5,
            pnl=10.0
        ),
        sample_trade_factory(
            timestamp=datetime(2024, 3, 15, 14, 30, 0),
            type="Sell",
            side="YES",
            price=55.0,
            cost=5.5,
            pnl=-5.0
        ),
        sample_trade_factory(
            timestamp=datetime(2024, 6, 1, 9, 0, 0),
            type="Market Buy",
            side="NO",
            price=30.0,
            cost=3.0,
            pnl=15.0
        ),
        sample_trade_factory(
            timestamp=datetime(2024, 9, 1, 16, 45, 0),
            type="Limit Sell",
            side="NO",
            price=70.0,
            cost=7.0,
            pnl=0.0
        ),
        sample_trade_factory(
            timestamp=datetime(2024, 12, 1, 11, 15, 0),
            type="Buy",
            side="YES",
            price=50.0,
            cost=5.0,
            pnl=-8.0
        ),
    ]


@pytest.fixture
def empty_trades_list() -> List[Trade]:
    """Return an empty list of trades."""
    return []


@pytest.fixture
def single_trade_list(sample_trade) -> List[Trade]:
    """Return a list with a single trade."""
    return [sample_trade]


@pytest.fixture
def winning_trades(sample_trade_factory) -> List[Trade]:
    """Create a list of only winning trades (positive PnL)."""
    return [
        sample_trade_factory(pnl=10.0),
        sample_trade_factory(pnl=25.0),
        sample_trade_factory(pnl=5.0),
    ]


@pytest.fixture
def losing_trades(sample_trade_factory) -> List[Trade]:
    """Create a list of only losing trades (negative PnL)."""
    return [
        sample_trade_factory(pnl=-10.0),
        sample_trade_factory(pnl=-25.0),
        sample_trade_factory(pnl=-5.0),
    ]


@pytest.fixture
def breakeven_trades(sample_trade_factory) -> List[Trade]:
    """Create a list of only breakeven trades (zero PnL)."""
    return [
        sample_trade_factory(pnl=0.0),
        sample_trade_factory(pnl=0.0),
        sample_trade_factory(pnl=0.0),
    ]


@pytest.fixture
def multi_market_trades(sample_trade_factory) -> List[Trade]:
    """Create trades across multiple markets."""
    return [
        sample_trade_factory(market="Market A", market_slug="market-a", pnl=10.0),
        sample_trade_factory(market="Market A", market_slug="market-a", pnl=5.0),
        sample_trade_factory(market="Market B", market_slug="market-b", pnl=-3.0),
        sample_trade_factory(market="Market C", market_slug="market-c", pnl=20.0),
        sample_trade_factory(market="Market C", market_slug="market-c", pnl=-15.0),
    ]


@pytest.fixture
def all_trade_types(sample_trade_factory) -> List[Trade]:
    """Create trades with all possible trade types."""
    trade_types = [
        "Buy", "Sell",
        "Market Buy", "Market Sell",
        "Limit Buy", "Limit Sell"
    ]
    return [sample_trade_factory(type=t) for t in trade_types]


@pytest.fixture
def both_sides_trades(sample_trade_factory) -> List[Trade]:
    """Create trades with both YES and NO sides."""
    return [
        sample_trade_factory(side="YES"),
        sample_trade_factory(side="NO"),
    ]


# Timestamp fixtures for date filtering tests
@pytest.fixture
def trades_spanning_year(sample_trade_factory) -> List[Trade]:
    """Create trades spanning an entire year for date filtering tests."""
    return [
        sample_trade_factory(timestamp=datetime(2024, 1, 15)),
        sample_trade_factory(timestamp=datetime(2024, 4, 15)),
        sample_trade_factory(timestamp=datetime(2024, 7, 15)),
        sample_trade_factory(timestamp=datetime(2024, 10, 15)),
    ]


# Edge case fixtures
@pytest.fixture
def extreme_values_trades(sample_trade_factory) -> List[Trade]:
    """Create trades with extreme values for boundary testing."""
    return [
        sample_trade_factory(price=0.0, cost=0.0, shares=0.0, pnl=0.0),
        sample_trade_factory(price=100.0, cost=1000000.0, shares=1000000.0, pnl=1000000.0),
        sample_trade_factory(price=50.0, cost=0.0001, shares=0.0001, pnl=-1000000.0),
    ]
