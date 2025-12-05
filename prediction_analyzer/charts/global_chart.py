# prediction_analyzer/charts/global_chart.py
"""
Global multi-market dashboard
"""
import plotly.graph_objects as go
from typing import Dict, List
from ..trade_loader import Trade

def generate_global_dashboard(trades_by_market: Dict[str, List[Trade]]):
    """
    Generate a global PnL dashboard across multiple markets

    Args:
        trades_by_market: Dictionary mapping market_name -> list of trades
    """
    if not trades_by_market:
        print("⚠️ No trades available for dashboard.")
        return

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
        cum = 0
        for pnl in pnls:
            cum += pnl
            cumulative.append(cum)

        # Add to plot
        fig.add_trace(go.Scatter(
            x=times,
            y=cumulative,
            mode='lines',
            name=market_name,
            line=dict(width=2),
            hovertemplate=f'{market_name}<br>Time: %{{x}}<br>PnL: $%{{y:.2f}}<extra></extra>'
        ))

        # Collect all trades for total portfolio calculation
        all_trades.extend(sorted_trades)

    # Add total cumulative PnL line
    if all_trades:
        # Sort all trades by timestamp across all markets
        all_trades_sorted = sorted(all_trades, key=lambda t: t.timestamp)

        # Calculate true cumulative PnL across all markets
        total_times = []
        total_cumulative = []
        cum = 0

        for trade in all_trades_sorted:
            cum += trade.pnl
            total_times.append(trade.timestamp)
            total_cumulative.append(cum)

        fig.add_trace(go.Scatter(
            x=total_times,
            y=total_cumulative,
            mode='lines',
            name='Total Portfolio',
            line=dict(color='black', width=4, dash='dash'),
            hovertemplate='Total<br>Time: %{x}<br>PnL: $%{y:.2f}<extra></extra>'
        ))

    # Update layout
    fig.update_layout(
        title="Global Multi-Market PnL Dashboard",
        xaxis_title="Time",
        yaxis_title="Cumulative PnL ($)",
        hovermode='x unified',
        height=700,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )

    # Save and display
    filename = "global_dashboard.html"
    fig.write_html(filename)
    print(f"✅ Global dashboard saved: {filename}")
    fig.show()
