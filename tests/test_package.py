# tests/test_package.py
"""
Basic tests for the prediction analyzer package
"""
import pytest
from datetime import datetime
from prediction_analyzer.trade_loader import Trade
from prediction_analyzer.pnl import calculate_global_pnl_summary
from prediction_analyzer.filters import filter_by_date, filter_by_trade_type

def create_sample_trade(**kwargs):
    """Helper to create sample trades"""
    defaults = {
        'market': 'Test Market',
        'market_slug': 'test-market',
        'timestamp': datetime.now(),
        'price': 50.0,
        'shares': 10.0,
        'cost': 5.0,
        'type': 'Buy',
        'side': 'YES',
        'pnl': 0.0
    }
    defaults.update(kwargs)
    return Trade(**defaults)

def test_trade_creation():
    """Test Trade dataclass creation"""
    trade = create_sample_trade()
    assert trade.market == 'Test Market'
    assert trade.price == 50.0
    assert trade.type == 'Buy'

def test_global_pnl_calculation():
    """Test global PnL summary calculation"""
    trades = [
        create_sample_trade(pnl=10.0),
        create_sample_trade(pnl=-5.0),
        create_sample_trade(pnl=15.0)
    ]

    summary = calculate_global_pnl_summary(trades)

    assert summary['total_trades'] == 3
    assert summary['total_pnl'] == 20.0
    assert summary['winning_trades'] == 2
    assert summary['losing_trades'] == 1

def test_filter_by_date():
    """Test date filtering"""
    trades = [
        create_sample_trade(timestamp=datetime(2024, 1, 1)),
        create_sample_trade(timestamp=datetime(2024, 6, 1)),
        create_sample_trade(timestamp=datetime(2024, 12, 1))
    ]

    filtered = filter_by_date(trades, start='2024-05-01', end='2024-12-31')

    assert len(filtered) == 2

def test_filter_by_type():
    """Test trade type filtering"""
    trades = [
        create_sample_trade(type='Buy'),
        create_sample_trade(type='Sell'),
        create_sample_trade(type='Buy')
    ]

    filtered = filter_by_trade_type(trades, types=['Buy'])

    assert len(filtered) == 2
    assert all(t.type == 'Buy' for t in filtered)

if __name__ == '__main__':
    pytest.main([__file__])
