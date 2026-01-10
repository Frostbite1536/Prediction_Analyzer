# prediction_analyzer/api/schemas/charts.py
"""
Chart data Pydantic schemas
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class ChartDataResponse(BaseModel):
    """Generic chart data response"""
    times: List[str]  # ISO format timestamps
    values: List[float]
    labels: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PriceChartData(BaseModel):
    """Price history chart data"""
    times: List[str]
    prices: List[float]
    colors: List[str]
    markers: List[str]
    types: List[str]
    sides: List[str]
    costs: List[float]


class PnLChartData(BaseModel):
    """Cumulative PnL chart data"""
    times: List[str]
    cumulative_pnl: List[float]
    final_pnl: float


class ExposureChartData(BaseModel):
    """Net exposure chart data"""
    times: List[str]
    exposure: List[float]
    max_exposure: float


class DashboardDataResponse(BaseModel):
    """Multi-market dashboard data"""
    markets: Dict[str, Dict[str, Any]]
    summary: Dict[str, Any]
