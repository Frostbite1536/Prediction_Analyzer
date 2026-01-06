# prediction_analyzer/api/schemas/analysis.py
"""
Analysis-related Pydantic schemas
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class FilterParams(BaseModel):
    """Parameters for filtering trades"""
    start_date: Optional[str] = None  # YYYY-MM-DD format
    end_date: Optional[str] = None
    types: Optional[List[str]] = None  # ["Buy", "Sell"]
    sides: Optional[List[str]] = None  # ["YES", "NO"]
    min_pnl: Optional[float] = None
    max_pnl: Optional[float] = None
    market_slug: Optional[str] = None


class GlobalSummaryResponse(BaseModel):
    """Global portfolio summary"""
    total_trades: int
    total_volume: float
    total_pnl: float
    win_rate: float
    avg_pnl_per_trade: float
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    total_invested: float
    total_returned: float
    roi: float


class MarketSummaryResponse(BaseModel):
    """Per-market analysis summary"""
    market_title: str
    market_slug: str
    total_trades: int
    total_pnl: float
    avg_pnl: float
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_invested: float
    total_returned: float
    roi: float


class MarketBreakdownItem(BaseModel):
    """Single market in breakdown"""
    market: str
    market_slug: str
    trade_count: int
    pnl: float


class SavedAnalysisCreate(BaseModel):
    """Schema for saving an analysis"""
    name: str
    description: Optional[str] = None
    filter_params: Optional[FilterParams] = None
    market_slug: Optional[str] = None
    results: Dict[str, Any]


class SavedAnalysisResponse(BaseModel):
    """Schema for saved analysis response"""
    id: int
    name: str
    description: Optional[str]
    filter_params: Optional[Dict[str, Any]]
    market_slug: Optional[str]
    results: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
