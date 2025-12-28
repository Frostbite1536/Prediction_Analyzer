# prediction_analyzer/charts/pro.py
"""
Professional/advanced chart generation with Plotly
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List
from ..trade_loader import Trade, _sanitize_filename

def generate_pro_chart(trades: List[Trade], market_name: str, resolved_outcome: str = None):
    """
    Generate an interactive professional chart using Plotly

    Args:
        trades: List of Trade objects for a specific market
        market_name: Name of the market
        resolved_outcome: "YES" or "NO" if market is resolved
    """
    if not trades:
        print("⚠️ No trades to chart.")
        return

    # Sort trades
    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    # Extract data
    times = [t.timestamp for t in sorted_trades]
    prices = [t.price for t in sorted_trades]
    pnls = [t.pnl for t in sorted_trades]
    types = [t.type for t in sorted_trades]
    sides = [t.side for t in sorted_trades]

    # Calculate cumulative PnL
    cumulative_pnl = []
    total = 0
    for pnl in pnls:
        total += pnl
        cumulative_pnl.append(total)

    # Calculate exposure
    net_exposure = []
    exposure = 0
    for t in sorted_trades:
        if t.type in ["Buy", "Market Buy", "Limit Buy"]:
            exposure += t.cost
        else:
            exposure -= t.cost
        net_exposure.append(exposure)

    # Color mapping
    colors = []
    for t_type, side in zip(types, sides):
        if "Buy" in t_type and side == "YES":
            colors.append("green")
        elif "Buy" in t_type and side == "NO":
            colors.append("purple")
        elif "Sell" in t_type and side == "YES":
            colors.append("lime")
        else:
            colors.append("red")

    # Create subplots
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Trade Prices", "Cumulative PnL", "Net Exposure"),
        row_heights=[0.4, 0.3, 0.3]
    )

    # Plot 1: Price line with trade markers
    fig.add_trace(
        go.Scatter(
            x=times,
            y=prices,
            mode="lines",
            line=dict(color="#1f77b4", width=2),
            name="Price",
            showlegend=False
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=times,
            y=prices,
            mode="markers",
            marker=dict(color=colors, size=10, line=dict(width=1, color="black")),
            name="Trades",
            text=[f"{t}<br>{s}<br>${c:.2f}" for t, s, c in zip(types, sides, [tr.cost for tr in sorted_trades])],
            hoverinfo="text+x+y"
        ),
        row=1, col=1
    )

    # Plot 2: Cumulative PnL
    fig.add_trace(
        go.Scatter(
            x=times,
            y=cumulative_pnl,
            mode="lines+markers",
            line=dict(color="green" if cumulative_pnl[-1] >= 0 else "red", width=3),
            marker=dict(size=6),
            name="Cumulative PnL",
            fill='tozeroy',
            fillcolor='rgba(0,255,0,0.1)' if cumulative_pnl[-1] >= 0 else 'rgba(255,0,0,0.1)'
        ),
        row=2, col=1
    )

    # Plot 3: Net Exposure
    fig.add_trace(
        go.Scatter(
            x=times,
            y=net_exposure,
            mode="lines",
            line=dict(color="orange", width=2),
            name="Net Exposure",
            fill='tozeroy',
            fillcolor='rgba(255,165,0,0.2)'
        ),
        row=3, col=1
    )

    # Update layout
    title_text = f"Professional Analysis: {market_name}"
    if resolved_outcome:
        title_text += f" (Resolved: {resolved_outcome})"

    fig.update_layout(
        height=900,
        title_text=title_text,
        showlegend=True,
        hovermode='x unified'
    )

    # Update axes
    fig.update_yaxes(title_text="Price (¢)", row=1, col=1)
    fig.update_yaxes(title_text="PnL ($)", row=2, col=1)
    fig.update_yaxes(title_text="Exposure ($)", row=3, col=1)
    fig.update_xaxes(title_text="Time", row=3, col=1)

    # Save as interactive HTML with sanitized filename
    safe_market_name = _sanitize_filename(market_name, max_length=30)
    filename = f"pro_chart_{safe_market_name}.html"
    fig.write_html(filename)
    print(f"✅ Interactive chart saved: {filename}")
    print("   Open this file in a web browser to interact with the chart.")

    # Also show in default browser
    fig.show()
