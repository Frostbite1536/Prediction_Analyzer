# prediction_analyzer/api/routers/analysis.py
"""
Analysis endpoints - PnL calculations, saved analyses
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_user
from ..models.user import User
from ..schemas.analysis import (
    FilterParams,
    GlobalSummaryResponse,
    MarketSummaryResponse,
    SavedAnalysisCreate,
    SavedAnalysisResponse,
    MarketBreakdownItem,
)
from ..services.analysis_service import analysis_service
from ..services.trade_service import trade_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/global", response_model=GlobalSummaryResponse)
async def get_global_analysis(
    filters: Optional[FilterParams] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate global PnL summary across all trades.

    Optionally filter by date range, trade type, side, or PnL thresholds.
    """
    # Check if user has any trades
    trades, total = trade_service.get_user_trades(db, current_user.id, limit=1, offset=0)
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trades found. Upload some trades first."
        )

    summary = analysis_service.get_global_summary(
        db,
        user_id=current_user.id,
        filters=filters
    )

    return GlobalSummaryResponse(**summary)


@router.post("/market/{market_slug}", response_model=MarketSummaryResponse)
async def get_market_analysis(
    market_slug: str,
    filters: Optional[FilterParams] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate PnL summary for a specific market.
    """
    # Check if market exists for user
    from ..models.trade import Trade
    exists = db.query(Trade).filter(
        Trade.user_id == current_user.id,
        Trade.market_slug == market_slug
    ).first()

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trades found for market: {market_slug}"
        )

    summary = analysis_service.get_market_summary(
        db,
        user_id=current_user.id,
        market_slug=market_slug,
        filters=filters
    )

    return MarketSummaryResponse(**summary)


@router.post("/breakdown", response_model=List[MarketBreakdownItem])
async def get_market_breakdown(
    filters: Optional[FilterParams] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get PnL breakdown by market.

    Returns a list of markets with their trade counts and PnL.
    """
    breakdown = analysis_service.get_market_breakdown(
        db,
        user_id=current_user.id,
        filters=filters
    )

    return [
        MarketBreakdownItem(
            market=data["market_name"],
            market_slug=slug,
            trade_count=data["trade_count"],
            pnl=data["total_pnl"]
        )
        for slug, data in breakdown.items()
    ]


@router.post("/timeseries")
async def get_pnl_timeseries(
    market_slug: Optional[str] = None,
    filters: Optional[FilterParams] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get time-series PnL data for charting.

    Returns trade-by-trade data with cumulative PnL and exposure.
    """
    data = analysis_service.get_pnl_timeseries(
        db,
        user_id=current_user.id,
        market_slug=market_slug,
        filters=filters
    )

    if not data:
        return {"data": [], "message": "No trades found matching criteria"}

    # Format for frontend consumption
    formatted = []
    for row in data:
        formatted.append({
            "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"]),
            "market": row.get("market"),
            "type": row.get("type"),
            "side": row.get("side"),
            "price": row.get("price"),
            "cost": row.get("cost"),
            "pnl": row.get("trade_pnl"),
            "cumulative_pnl": row.get("cumulative_pnl"),
            "exposure": row.get("exposure")
        })

    return {"data": formatted}


# Saved Analysis CRUD

@router.get("/saved", response_model=List[SavedAnalysisResponse])
async def list_saved_analyses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all saved analyses for the current user.
    """
    analyses = analysis_service.get_saved_analyses(db, current_user.id)

    return [
        SavedAnalysisResponse(**analysis_service.parse_saved_analysis(a))
        for a in analyses
    ]


@router.post("/saved", response_model=SavedAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def save_analysis(
    analysis_data: SavedAnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save an analysis result for later reference.
    """
    saved = analysis_service.save_analysis(
        db,
        user_id=current_user.id,
        analysis_data=analysis_data
    )

    return SavedAnalysisResponse(**analysis_service.parse_saved_analysis(saved))


@router.get("/saved/{analysis_id}", response_model=SavedAnalysisResponse)
async def get_saved_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific saved analysis.
    """
    analysis = analysis_service.get_saved_analysis(
        db,
        user_id=current_user.id,
        analysis_id=analysis_id
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved analysis not found"
        )

    return SavedAnalysisResponse(**analysis_service.parse_saved_analysis(analysis))


@router.delete("/saved/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a saved analysis.
    """
    analysis = analysis_service.get_saved_analysis(
        db,
        user_id=current_user.id,
        analysis_id=analysis_id
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved analysis not found"
        )

    analysis_service.delete_saved_analysis(db, analysis)
    return None
