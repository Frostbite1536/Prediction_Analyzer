# prediction_analyzer/api/routers/users.py
"""
User profile endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_user
from ..models.user import User
from ..schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get the current authenticated user's profile.
    """
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's profile.

    Only provided fields will be updated.
    """
    from ..services.auth_service import auth_service

    # Check if new email is already taken
    if user_update.email and user_update.email != current_user.email:
        existing = auth_service.get_user_by_email(db, user_update.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_update.email

    # Check if new username is already taken
    if user_update.username and user_update.username != current_user.username:
        existing = auth_service.get_user_by_username(db, user_update.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_update.username

    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete the current user's account.

    This will also delete all associated trades and saved analyses.
    """
    db.delete(current_user)
    db.commit()
    return None


@router.get("/me/stats")
async def get_current_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for the current user.
    """
    from ..models.trade import Trade, TradeUpload
    from ..models.analysis import SavedAnalysis
    from sqlalchemy import func

    trade_count = db.query(func.count(Trade.id)).filter(
        Trade.user_id == current_user.id
    ).scalar()

    upload_count = db.query(func.count(TradeUpload.id)).filter(
        TradeUpload.user_id == current_user.id
    ).scalar()

    analysis_count = db.query(func.count(SavedAnalysis.id)).filter(
        SavedAnalysis.user_id == current_user.id
    ).scalar()

    market_count = db.query(func.count(func.distinct(Trade.market_slug))).filter(
        Trade.user_id == current_user.id
    ).scalar()

    total_pnl = db.query(func.sum(Trade.pnl)).filter(
        Trade.user_id == current_user.id
    ).scalar() or 0.0

    return {
        "trade_count": trade_count,
        "upload_count": upload_count,
        "saved_analysis_count": analysis_count,
        "market_count": market_count,
        "total_pnl": total_pnl,
        "member_since": current_user.created_at.isoformat()
    }
