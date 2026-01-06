# prediction_analyzer/api/services/analysis_service.py
"""
Analysis service - wraps existing pnl.py and filters.py functions
"""
import json
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from ..models.trade import Trade as TradeModel
from ..models.analysis import SavedAnalysis
from ..schemas.analysis import FilterParams, SavedAnalysisCreate
from ...trade_loader import Trade as TradeDataclass
from ...pnl import (
    calculate_global_pnl_summary,
    calculate_market_pnl_summary,
    calculate_market_pnl,
    calculate_pnl
)
from ...filters import (
    filter_by_date,
    filter_by_trade_type,
    filter_by_side,
    filter_by_pnl
)
from .trade_service import trade_service


class AnalysisService:
    """Service for running analyses on trade data"""

    def apply_filters(
        self,
        trades: List[TradeDataclass],
        filters: FilterParams
    ) -> List[TradeDataclass]:
        """
        Apply filter parameters to a list of trades

        Args:
            trades: List of Trade dataclass objects
            filters: Filter parameters

        Returns:
            Filtered list of trades
        """
        if filters.start_date or filters.end_date:
            trades = filter_by_date(trades, filters.start_date, filters.end_date)

        if filters.types:
            trades = filter_by_trade_type(trades, filters.types)

        if filters.sides:
            trades = filter_by_side(trades, filters.sides)

        if filters.min_pnl is not None or filters.max_pnl is not None:
            trades = filter_by_pnl(trades, filters.min_pnl, filters.max_pnl)

        if filters.market_slug:
            trades = [t for t in trades if t.market_slug == filters.market_slug]

        return trades

    def get_global_summary(
        self,
        db: Session,
        user_id: int,
        filters: Optional[FilterParams] = None
    ) -> Dict[str, Any]:
        """
        Calculate global PnL summary for a user

        Args:
            db: Database session
            user_id: User ID
            filters: Optional filter parameters

        Returns:
            Dictionary with global summary statistics
        """
        # Get all user trades
        db_trades = trade_service.get_all_user_trades(db, user_id)
        trades = trade_service.db_trades_to_dataclass(db_trades)

        # Apply filters if provided
        if filters:
            trades = self.apply_filters(trades, filters)

        # Use existing pnl.py function
        return calculate_global_pnl_summary(trades)

    def get_market_summary(
        self,
        db: Session,
        user_id: int,
        market_slug: str,
        filters: Optional[FilterParams] = None
    ) -> Dict[str, Any]:
        """
        Calculate PnL summary for a specific market

        Args:
            db: Database session
            user_id: User ID
            market_slug: Market identifier
            filters: Optional filter parameters

        Returns:
            Dictionary with market summary statistics
        """
        # Get trades for specific market
        db_trades = db.query(TradeModel).filter(
            TradeModel.user_id == user_id,
            TradeModel.market_slug == market_slug
        ).order_by(TradeModel.timestamp.asc()).all()

        trades = trade_service.db_trades_to_dataclass(db_trades)

        # Apply filters if provided
        if filters:
            trades = self.apply_filters(trades, filters)

        # Use existing pnl.py function
        summary = calculate_market_pnl_summary(trades)
        summary["market_slug"] = market_slug
        return summary

    def get_market_breakdown(
        self,
        db: Session,
        user_id: int,
        filters: Optional[FilterParams] = None
    ) -> Dict[str, Dict]:
        """
        Get PnL breakdown by market

        Returns:
            Dictionary mapping market_slug to statistics
        """
        db_trades = trade_service.get_all_user_trades(db, user_id)
        trades = trade_service.db_trades_to_dataclass(db_trades)

        if filters:
            trades = self.apply_filters(trades, filters)

        return calculate_market_pnl(trades)

    def get_pnl_timeseries(
        self,
        db: Session,
        user_id: int,
        market_slug: Optional[str] = None,
        filters: Optional[FilterParams] = None
    ) -> List[Dict]:
        """
        Get time-series PnL data for charting

        Returns:
            List of dictionaries with timestamp, cumulative_pnl, exposure
        """
        if market_slug:
            db_trades = db.query(TradeModel).filter(
                TradeModel.user_id == user_id,
                TradeModel.market_slug == market_slug
            ).order_by(TradeModel.timestamp.asc()).all()
        else:
            db_trades = trade_service.get_all_user_trades(db, user_id)

        trades = trade_service.db_trades_to_dataclass(db_trades)

        if filters:
            trades = self.apply_filters(trades, filters)

        if not trades:
            return []

        # Use existing calculate_pnl function
        df = calculate_pnl(trades)

        return df.to_dict(orient="records")

    # Saved Analysis CRUD

    def save_analysis(
        self,
        db: Session,
        user_id: int,
        analysis_data: SavedAnalysisCreate
    ) -> SavedAnalysis:
        """Save an analysis result"""
        saved = SavedAnalysis(
            user_id=user_id,
            name=analysis_data.name,
            description=analysis_data.description,
            filter_params=json.dumps(
                analysis_data.filter_params.model_dump() if analysis_data.filter_params else None
            ),
            market_slug=analysis_data.market_slug,
            results=json.dumps(analysis_data.results)
        )
        db.add(saved)
        db.commit()
        db.refresh(saved)
        return saved

    def get_saved_analyses(self, db: Session, user_id: int) -> List[SavedAnalysis]:
        """Get all saved analyses for a user"""
        return db.query(SavedAnalysis).filter(
            SavedAnalysis.user_id == user_id
        ).order_by(SavedAnalysis.created_at.desc()).all()

    def get_saved_analysis(
        self,
        db: Session,
        user_id: int,
        analysis_id: int
    ) -> Optional[SavedAnalysis]:
        """Get a specific saved analysis"""
        return db.query(SavedAnalysis).filter(
            SavedAnalysis.id == analysis_id,
            SavedAnalysis.user_id == user_id
        ).first()

    def delete_saved_analysis(self, db: Session, analysis: SavedAnalysis) -> None:
        """Delete a saved analysis"""
        db.delete(analysis)
        db.commit()

    def parse_saved_analysis(self, analysis: SavedAnalysis) -> Dict[str, Any]:
        """Parse a saved analysis into response format"""
        return {
            "id": analysis.id,
            "name": analysis.name,
            "description": analysis.description,
            "filter_params": json.loads(analysis.filter_params) if analysis.filter_params else None,
            "market_slug": analysis.market_slug,
            "results": json.loads(analysis.results),
            "created_at": analysis.created_at,
            "updated_at": analysis.updated_at
        }


# Singleton instance
analysis_service = AnalysisService()
