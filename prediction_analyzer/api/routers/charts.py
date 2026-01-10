# prediction_analyzer/api/routers/charts.py
"""
Chart data endpoints - returns JSON data for frontend rendering
"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_user
from ..models.user import User
from ..schemas.analysis import FilterParams
from ..schemas.charts import PriceChartData, PnLChartData, ExposureChartData, DashboardDataResponse
from ..services.chart_service import chart_service

router = APIRouter(prefix="/charts", tags=["charts"])


@router.post("/price", response_model=PriceChartData)
async def get_price_chart_data(
    market_slug: Optional[str] = None,
    filters: Optional[FilterParams] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get price history chart data.

    Returns trade prices over time with styling information.
    """
    return chart_service.get_price_chart_data(
        db,
        user_id=current_user.id,
        market_slug=market_slug,
        filters=filters
    )


@router.post("/pnl", response_model=PnLChartData)
async def get_pnl_chart_data(
    market_slug: Optional[str] = None,
    filters: Optional[FilterParams] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get cumulative PnL chart data.

    Returns cumulative PnL over time.
    """
    return chart_service.get_pnl_chart_data(
        db,
        user_id=current_user.id,
        market_slug=market_slug,
        filters=filters
    )


@router.post("/exposure", response_model=ExposureChartData)
async def get_exposure_chart_data(
    market_slug: Optional[str] = None,
    filters: Optional[FilterParams] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get net exposure chart data.

    Returns net share exposure over time.
    """
    return chart_service.get_exposure_chart_data(
        db,
        user_id=current_user.id,
        market_slug=market_slug,
        filters=filters
    )


@router.post("/dashboard", response_model=DashboardDataResponse)
async def get_dashboard_data(
    filters: Optional[FilterParams] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get multi-market dashboard data.

    Returns per-market PnL data and overall summary.
    """
    return chart_service.get_dashboard_data(
        db,
        user_id=current_user.id,
        filters=filters
    )
