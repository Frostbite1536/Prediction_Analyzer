# prediction_analyzer/api/services/chart_service.py
"""
Chart service - generates chart data for frontend rendering
"""
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from ..models.trade import Trade as TradeModel
from ..schemas.analysis import FilterParams
from ..schemas.charts import PriceChartData, PnLChartData, ExposureChartData
from ...trade_loader import Trade as TradeDataclass
from ...pnl import calculate_pnl
from .trade_service import trade_service
from .analysis_service import analysis_service


class ChartService:
    """Service for generating chart data"""

    def get_trade_style(self, trade_type: str, side: str) -> tuple:
        """
        Get color and marker for a trade

        Returns:
            Tuple of (color, marker, label)
        """
        # Color based on trade type
        if trade_type in ["Buy", "Market Buy", "Limit Buy"]:
            color = "#00C853" if side == "YES" else "#FF1744"  # Green for YES, Red for NO
            marker = "triangle-up"
        else:  # Sell
            color = "#FFD600" if side == "YES" else "#AA00FF"  # Yellow for YES sell, Purple for NO sell
            marker = "triangle-down"

        label = f"{trade_type} {side}"
        return color, marker, label

    def get_price_chart_data(
        self,
        db: Session,
        user_id: int,
        market_slug: Optional[str] = None,
        filters: Optional[FilterParams] = None
    ) -> PriceChartData:
        """
        Generate price chart data

        Returns:
            PriceChartData with times, prices, colors, etc.
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
            trades = analysis_service.apply_filters(trades, filters)

        if not trades:
            return PriceChartData(
                times=[],
                prices=[],
                colors=[],
                markers=[],
                types=[],
                sides=[],
                costs=[]
            )

        # Sort by timestamp
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)

        times = []
        prices = []
        colors = []
        markers = []
        types = []
        sides = []
        costs = []

        for t in sorted_trades:
            times.append(t.timestamp.isoformat())
            prices.append(t.price)
            color, marker, _ = self.get_trade_style(t.type, t.side)
            colors.append(color)
            markers.append(marker)
            types.append(t.type)
            sides.append(t.side)
            costs.append(t.cost)

        return PriceChartData(
            times=times,
            prices=prices,
            colors=colors,
            markers=markers,
            types=types,
            sides=sides,
            costs=costs
        )

    def get_pnl_chart_data(
        self,
        db: Session,
        user_id: int,
        market_slug: Optional[str] = None,
        filters: Optional[FilterParams] = None
    ) -> PnLChartData:
        """
        Generate cumulative PnL chart data

        Returns:
            PnLChartData with times, cumulative_pnl, final_pnl
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
            trades = analysis_service.apply_filters(trades, filters)

        if not trades:
            return PnLChartData(times=[], cumulative_pnl=[], final_pnl=0.0)

        # Calculate cumulative PnL
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)

        times = []
        cumulative_pnl = []
        total = 0.0

        for t in sorted_trades:
            total += t.pnl
            times.append(t.timestamp.isoformat())
            cumulative_pnl.append(total)

        return PnLChartData(
            times=times,
            cumulative_pnl=cumulative_pnl,
            final_pnl=total
        )

    def get_exposure_chart_data(
        self,
        db: Session,
        user_id: int,
        market_slug: Optional[str] = None,
        filters: Optional[FilterParams] = None
    ) -> ExposureChartData:
        """
        Generate net exposure chart data

        Returns:
            ExposureChartData with times, exposure, max_exposure
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
            trades = analysis_service.apply_filters(trades, filters)

        if not trades:
            return ExposureChartData(times=[], exposure=[], max_exposure=0.0)

        # Use existing calculate_pnl to get exposure
        df = calculate_pnl(trades)

        times = df["timestamp"].apply(lambda x: x.isoformat()).tolist()
        exposure = df["exposure"].tolist()
        max_exposure = max(abs(e) for e in exposure) if exposure else 0.0

        return ExposureChartData(
            times=times,
            exposure=exposure,
            max_exposure=max_exposure
        )

    def get_dashboard_data(
        self,
        db: Session,
        user_id: int,
        filters: Optional[FilterParams] = None
    ) -> Dict[str, Any]:
        """
        Generate multi-market dashboard data

        Returns:
            Dictionary with per-market data and summary
        """
        db_trades = trade_service.get_all_user_trades(db, user_id)
        trades = trade_service.db_trades_to_dataclass(db_trades)

        if filters:
            trades = analysis_service.apply_filters(trades, filters)

        if not trades:
            return {"markets": {}, "summary": {}}

        # Group by market
        markets_data = {}
        for t in trades:
            if t.market_slug not in markets_data:
                markets_data[t.market_slug] = {
                    "title": t.market,
                    "trades": [],
                    "total_pnl": 0.0,
                    "trade_count": 0
                }
            markets_data[t.market_slug]["trades"].append(t)
            markets_data[t.market_slug]["total_pnl"] += t.pnl
            markets_data[t.market_slug]["trade_count"] += 1

        # Build chart data for each market
        result = {"markets": {}, "summary": {}}

        for slug, data in markets_data.items():
            sorted_trades = sorted(data["trades"], key=lambda x: x.timestamp)

            # Cumulative PnL for this market
            times = []
            cumulative = []
            total = 0.0
            for t in sorted_trades:
                total += t.pnl
                times.append(t.timestamp.isoformat())
                cumulative.append(total)

            result["markets"][slug] = {
                "title": data["title"],
                "times": times,
                "cumulative_pnl": cumulative,
                "total_pnl": data["total_pnl"],
                "trade_count": data["trade_count"]
            }

        # Overall summary
        total_pnl = sum(d["total_pnl"] for d in markets_data.values())
        total_trades = sum(d["trade_count"] for d in markets_data.values())

        result["summary"] = {
            "total_markets": len(markets_data),
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "best_market": max(markets_data.items(), key=lambda x: x[1]["total_pnl"])[0] if markets_data else None,
            "worst_market": min(markets_data.items(), key=lambda x: x[1]["total_pnl"])[0] if markets_data else None
        }

        return result


# Singleton instance
chart_service = ChartService()
