# prediction_analyzer/api/services/trade_service.py
"""
Trade service - file upload, CRUD operations
"""
import tempfile
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import UploadFile

from ..models.trade import Trade as TradeModel, TradeUpload
from ..schemas.trade import MarketInfo
from ...trade_loader import load_trades, Trade as TradeDataclass


class TradeService:
    """Service for trade operations"""

    def db_trade_to_dataclass(self, db_trade: TradeModel) -> TradeDataclass:
        """Convert a SQLAlchemy Trade model to a Trade dataclass"""
        return TradeDataclass(
            market=db_trade.market,
            market_slug=db_trade.market_slug,
            timestamp=db_trade.timestamp,
            price=db_trade.price,
            shares=db_trade.shares,
            cost=db_trade.cost,
            type=db_trade.type,
            side=db_trade.side,
            pnl=db_trade.pnl,
            tx_hash=db_trade.tx_hash
        )

    def db_trades_to_dataclass(self, db_trades: List[TradeModel]) -> List[TradeDataclass]:
        """Convert a list of SQLAlchemy Trade models to Trade dataclasses"""
        return [self.db_trade_to_dataclass(t) for t in db_trades]

    async def process_upload(
        self,
        db: Session,
        user_id: int,
        file: UploadFile
    ) -> Tuple[int, int]:
        """
        Process an uploaded trade file

        Args:
            db: Database session
            user_id: ID of the user uploading
            file: Uploaded file

        Returns:
            Tuple of (upload_id, trade_count)
        """
        # Determine file extension
        filename = file.filename or "trades.json"
        suffix = Path(filename).suffix.lower()

        if suffix not in [".json", ".csv", ".xlsx"]:
            raise ValueError(f"Unsupported file type: {suffix}")

        # Read file content
        content = await file.read()

        # Calculate file hash for deduplication
        file_hash = hashlib.sha256(content).hexdigest()

        # Check for duplicate upload
        existing = db.query(TradeUpload).filter(
            TradeUpload.user_id == user_id,
            TradeUpload.file_hash == file_hash
        ).first()

        if existing:
            raise ValueError(f"This file was already uploaded (ID: {existing.id})")

        # Save to temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Use existing trade_loader to parse the file
            trades = load_trades(tmp_path)

            if not trades:
                raise ValueError("No valid trades found in the file")

            # Create upload record
            upload = TradeUpload(
                user_id=user_id,
                filename=filename,
                file_type=suffix[1:],  # Remove the dot
                trade_count=len(trades),
                file_hash=file_hash
            )
            db.add(upload)
            db.flush()  # Get the upload ID

            # Convert and save trades to database
            for trade in trades:
                db_trade = TradeModel(
                    user_id=user_id,
                    upload_id=upload.id,
                    market=trade.market,
                    market_slug=trade.market_slug,
                    timestamp=trade.timestamp,
                    price=trade.price,
                    shares=trade.shares,
                    cost=trade.cost,
                    type=trade.type,
                    side=trade.side,
                    pnl=trade.pnl,
                    tx_hash=trade.tx_hash
                )
                db.add(db_trade)

            db.commit()
            return upload.id, len(trades)

        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    def get_user_trades(
        self,
        db: Session,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        market_slug: Optional[str] = None
    ) -> Tuple[List[TradeModel], int]:
        """
        Get trades for a user with pagination

        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of trades to return
            offset: Number of trades to skip
            market_slug: Optional filter by market

        Returns:
            Tuple of (trades list, total count)
        """
        query = db.query(TradeModel).filter(TradeModel.user_id == user_id)

        if market_slug:
            query = query.filter(TradeModel.market_slug == market_slug)

        total = query.count()
        trades = query.order_by(TradeModel.timestamp.desc()).offset(offset).limit(limit).all()

        return trades, total

    def get_all_user_trades(self, db: Session, user_id: int) -> List[TradeModel]:
        """Get all trades for a user (no pagination)"""
        return db.query(TradeModel).filter(
            TradeModel.user_id == user_id
        ).order_by(TradeModel.timestamp.asc()).all()

    def get_user_markets(self, db: Session, user_id: int) -> List[MarketInfo]:
        """
        Get unique markets for a user with trade counts and PnL

        Returns:
            List of MarketInfo objects
        """
        results = db.query(
            TradeModel.market_slug,
            TradeModel.market,
            func.count(TradeModel.id).label("trade_count"),
            func.sum(TradeModel.pnl).label("total_pnl")
        ).filter(
            TradeModel.user_id == user_id
        ).group_by(
            TradeModel.market_slug,
            TradeModel.market
        ).all()

        return [
            MarketInfo(
                slug=r.market_slug,
                title=r.market,
                trade_count=r.trade_count,
                total_pnl=r.total_pnl or 0.0
            )
            for r in results
        ]

    def get_trade_by_id(
        self,
        db: Session,
        user_id: int,
        trade_id: int
    ) -> Optional[TradeModel]:
        """Get a specific trade by ID (must belong to user)"""
        return db.query(TradeModel).filter(
            TradeModel.id == trade_id,
            TradeModel.user_id == user_id
        ).first()

    def delete_trade(self, db: Session, trade: TradeModel) -> None:
        """Delete a trade"""
        db.delete(trade)
        db.commit()

    def delete_all_user_trades(self, db: Session, user_id: int) -> int:
        """Delete all trades for a user, returns count deleted"""
        # Also delete uploads
        db.query(TradeUpload).filter(TradeUpload.user_id == user_id).delete()
        count = db.query(TradeModel).filter(TradeModel.user_id == user_id).delete()
        db.commit()
        return count

    def get_user_uploads(self, db: Session, user_id: int) -> List[TradeUpload]:
        """Get all uploads for a user"""
        return db.query(TradeUpload).filter(
            TradeUpload.user_id == user_id
        ).order_by(TradeUpload.uploaded_at.desc()).all()


# Singleton instance
trade_service = TradeService()
