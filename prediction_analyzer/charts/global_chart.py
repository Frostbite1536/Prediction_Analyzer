# prediction_analyzer/charts/global_chart.py
"""
Global multi-market dashboard
"""

import logging
from decimal import Decimal
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, List, Optional
from ..trade_loader import Trade
from ..exceptions import NoTradesError

logger = logging.getLogger(__name__)

# Default output directory: charts_output/ under project root
_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "charts_output"


def generate_global_dashboard(
    trades_by_market: Dict[str, List[Trade]], output_dir: Optional[str] = None, show: bool = True
):
    """
    Generate a global PnL dashboard across multiple markets

    Args:
        trades_by_market: Dictionary mapping market_name -> list of trades
    """
    if not trades_by_market:
        raise NoTradesError("No trades available for dashboard.")

    fig = go.Figure()

    # Collect all trades from all markets for accurate total calculation
    all_trades = []

    for market_name, trades in trades_by_market.items():
        if not trades:
            continue

        # Sort trades
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)

        # Calculate cumulative PnL for this market
        times = [t.timestamp for t in sorted_trades]
        pnls = [t.pnl for t in sorted_trades]

        cumulative = []
        cum = Decimal("0")
        for pnl in pnls:
            cum += Decimal(str(pnl))
            cumulative.append(float(cum))

        # Add to plot
        fig.add_trace(
            go.Scatter(
                x=times,
                y=cumulative,
                mode="lines",
                name=market_name,
                line=dict(width=2),
                hovertemplate=f"{market_name}<br>Time: %{{x}}<br>PnL: $%{{y:.2f}}<extra></extra>",
            )
        )

        # Collect all trades for total portfolio calculation
        all_trades.extend(sorted_trades)

    # Add total cumulative PnL line
    if all_trades:
        # Sort all trades by timestamp across all markets
        all_trades_sorted = sorted(all_trades, key=lambda t: t.timestamp)

        # Calculate true cumulative PnL across all markets
        total_times = []
        total_cumulative = []
        cum = Decimal("0")

        for trade in all_trades_sorted:
            cum += Decimal(str(trade.pnl))
            total_times.append(trade.timestamp)
            total_cumulative.append(float(cum))

        fig.add_trace(
            go.Scatter(
                x=total_times,
                y=total_cumulative,
                mode="lines",
                name="Total Portfolio",
                line=dict(color="black", width=4, dash="dash"),
                hovertemplate="Total<br>Time: %{x}<br>PnL: $%{y:.2f}<extra></extra>",
            )
        )

    # Update layout
    fig.update_layout(
        title="Global Multi-Market PnL Dashboard",
        xaxis_title="Time",
        yaxis_title="Cumulative PnL ($)",
        hovermode="x unified",
        height=700,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    )

    # Save and display to output directory
    out = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    filepath = out / "global_dashboard.html"
    fig.write_html(str(filepath))
    logger.info("Global dashboard saved: %s", filepath)
    if show:
        fig.show()
    return str(filepath)
