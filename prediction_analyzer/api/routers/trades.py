# prediction_analyzer/api/routers/trades.py
"""
Trade management endpoints - CRUD, upload, export
"""
from typing import Optional
import io
import json

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd

from ..dependencies import get_db, get_current_user
from ..models.user import User
from ..schemas.trade import (
    TradeResponse,
    TradeListResponse,
    TradeUploadResponse,
    MarketInfo,
)
from ..services.trade_service import trade_service

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=TradeListResponse)
async def list_trades(
    limit: int = Query(100, le=1000, ge=1),
    offset: int = Query(0, ge=0),
    market_slug: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List trades for the current user with pagination.

    - **limit**: Maximum number of trades to return (max 1000)
    - **offset**: Number of trades to skip
    - **market_slug**: Optional filter by market
    """
    trades, total = trade_service.get_user_trades(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        market_slug=market_slug
    )

    return TradeListResponse(
        trades=[TradeResponse.model_validate(t) for t in trades],
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("/upload", response_model=TradeUploadResponse)
async def upload_trades(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a trade file (JSON, CSV, or XLSX).

    The file will be parsed and trades will be saved to your account.
    """
    filename = file.filename or "trades.json"

    if not filename.lower().endswith(('.json', '.csv', '.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Use JSON, CSV, or XLSX."
        )

    try:
        upload_id, trade_count = await trade_service.process_upload(
            db, current_user.id, file
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return TradeUploadResponse(
        upload_id=upload_id,
        filename=filename,
        trade_count=trade_count,
        message=f"Successfully imported {trade_count} trades"
    )


@router.get("/markets", response_model=list[MarketInfo])
async def list_markets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all unique markets for the current user.

    Returns market slugs, titles, trade counts, and total PnL.
    """
    return trade_service.get_user_markets(db, current_user.id)


@router.get("/export/csv")
async def export_trades_csv(
    market_slug: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export trades as CSV file.
    """
    trades, _ = trade_service.get_user_trades(
        db,
        user_id=current_user.id,
        limit=100000,  # Get all trades
        offset=0,
        market_slug=market_slug
    )

    if not trades:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trades found to export"
        )

    # Convert to DataFrame
    df = pd.DataFrame([
        {
            "market": t.market,
            "market_slug": t.market_slug,
            "timestamp": t.timestamp.isoformat(),
            "price": t.price,
            "shares": t.shares,
            "cost": t.cost,
            "type": t.type,
            "side": t.side,
            "pnl": t.pnl,
            "tx_hash": t.tx_hash
        }
        for t in trades
    ])

    # Write to buffer
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    filename = f"trades_{current_user.username}"
    if market_slug:
        filename += f"_{market_slug}"
    filename += ".csv"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/json")
async def export_trades_json(
    market_slug: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export trades as JSON file.
    """
    trades, _ = trade_service.get_user_trades(
        db,
        user_id=current_user.id,
        limit=100000,
        offset=0,
        market_slug=market_slug
    )

    if not trades:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trades found to export"
        )

    # Convert to list of dicts
    trades_data = [
        {
            "market": t.market,
            "market_slug": t.market_slug,
            "timestamp": t.timestamp.isoformat(),
            "price": t.price,
            "shares": t.shares,
            "cost": t.cost,
            "type": t.type,
            "side": t.side,
            "pnl": t.pnl,
            "tx_hash": t.tx_hash
        }
        for t in trades
    ]

    filename = f"trades_{current_user.username}"
    if market_slug:
        filename += f"_{market_slug}"
    filename += ".json"

    return StreamingResponse(
        iter([json.dumps(trades_data, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific trade by ID.
    """
    trade = trade_service.get_trade_by_id(db, current_user.id, trade_id)

    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found"
        )

    return TradeResponse.model_validate(trade)


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific trade.
    """
    trade = trade_service.get_trade_by_id(db, current_user.id, trade_id)

    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found"
        )

    trade_service.delete_trade(db, trade)
    return None


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_all_trades(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete all trades for the current user.

    This action cannot be undone!
    """
    count = trade_service.delete_all_user_trades(db, current_user.id)

    return {
        "message": f"Deleted {count} trades",
        "deleted_count": count
    }
