# prediction_analyzer/charts/enhanced.py
"""
Enhanced chart generation with battlefield visualization
"""

import logging
from decimal import Decimal
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from typing import List, Optional
from ..trade_loader import Trade
from ..utils.export import sanitize_filename as _sanitize_filename
from ..exceptions import NoTradesError

logger = logging.getLogger(__name__)

# Default output directory: charts_output/ under project root
_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "charts_output"


def generate_enhanced_chart(
    trades: List[Trade],
    market_name: str,
    resolved_outcome: str = None,
    output_dir: Optional[str] = None,
    show: bool = True,
):
    """
    Generate an enhanced battlefield chart using Plotly

    Top Panel (The Battlefield):
        - Blue Line: Implied Probability of YES (market price)
        - Green Triangles: "Long YES" moves (Buying YES or Selling NO)
        - Red Triangles: "Short YES" moves (Buying NO or Selling YES)
        - Bubble Size: Bigger bubble = Bigger bet ($)

    Middle Panel (The Scoreboard):
        - Running P&L (Mark-to-Market)
        - Green Area: Currently in profit
        - Red Area: Currently in loss

    Bottom Panel (The Risk):
        - Net share count
        - Positive: Holding YES shares (net)
        - Negative: Holding NO shares (net)

    Args:
        trades: List of Trade objects for a specific market
        market_name: Name of the market
        resolved_outcome: "YES" or "NO" if market is resolved
    """
    if not trades:
        raise NoTradesError("No trades to chart.")

    # Sort trades by timestamp
    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    # Extract data
    times = [t.timestamp for t in sorted_trades]
    prices = [t.price for t in sorted_trades]

    # Calculate running metrics
    net_shares = []  # Net YES shares (positive) or NO shares (negative)
    total_cost_basis = []
    running_pnl = []

    current_shares = Decimal("0")  # Net YES shares
    current_cost = Decimal("0")

    for i, t in enumerate(sorted_trades):
        shares_d = Decimal(str(t.shares))
        cost_d = Decimal(str(t.cost))

        # Update share count and cost basis
        if t.type in ["Buy", "Market Buy", "Limit Buy"]:
            if t.side == "YES":
                # Buying YES increases YES shares
                current_shares += shares_d
                current_cost += cost_d
            else:  # NO
                # Buying NO decreases YES shares (equivalent to shorting YES)
                current_shares -= shares_d
                current_cost += cost_d
        else:  # Sell
            if t.side == "YES":
                # Selling YES decreases YES shares
                current_shares -= shares_d
                current_cost -= cost_d
            else:  # NO
                # Selling NO increases YES shares
                current_shares += shares_d
                current_cost -= cost_d

        net_shares.append(float(current_shares))
        total_cost_basis.append(float(current_cost))

        # Calculate mark-to-market P&L
        # Current market value of shares minus cost basis
        current_price = Decimal(str(t.price)) / Decimal("100")  # Convert cents to dollars per share
        mark_to_market_value = current_shares * current_price
        mtm_pnl = mark_to_market_value - current_cost
        running_pnl.append(float(mtm_pnl))

    # Classify trades for visualization
    trade_colors = []
    trade_symbols = []
    trade_sizes = []
    hover_texts = []

    for t in sorted_trades:
        # Determine if trade is "Long YES" or "Short YES"
        is_long_yes = False

        if t.type in ["Buy", "Market Buy", "Limit Buy"]:
            # Buying YES = Long YES
            # Buying NO = Short YES
            is_long_yes = t.side == "YES"
        else:  # Sell
            # Selling YES = Short YES
            # Selling NO = Long YES
            is_long_yes = t.side == "NO"

        # Color and symbol
        if is_long_yes:
            trade_colors.append("green")
            trade_symbols.append("triangle-up")
        else:
            trade_colors.append("red")
            trade_symbols.append("triangle-down")

        # Size based on bet amount (cost)
        # Scale: $10 = size 10, $100 = size 20, $1000 = size 30
        size = min(max(10 + (t.cost / 50), 8), 40)
        trade_sizes.append(size)

        # Hover text
        action = "Long YES" if is_long_yes else "Short YES"
        hover_texts.append(
            f"{action}<br>"
            f"{t.type} {t.side}<br>"
            f"${t.cost:.2f}<br>"
            f"{t.shares:.1f} shares @ {t.price:.1f}¢"
        )

    # Create subplots
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            "The Battlefield: Implied Probability of YES",
            "The Scoreboard: Running P&L (Mark-to-Market)",
            "The Risk: Net Share Position",
        ),
        row_heights=[0.4, 0.3, 0.3],
    )

    # ==========================================
    # Panel 1: The Battlefield (Price + Trades)
    # ==========================================

    # Blue line for market price
    fig.add_trace(
        go.Scatter(
            x=times,
            y=prices,
            mode="lines",
            line=dict(color="#1f77b4", width=3),
            name="Market Price",
            showlegend=True,
            hovertemplate="Price: %{y:.1f}¢<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Trade markers (triangles)
    fig.add_trace(
        go.Scatter(
            x=times,
            y=prices,
            mode="markers",
            marker=dict(
                color=trade_colors,
                size=trade_sizes,
                symbol=trade_symbols,
                line=dict(width=1, color="white"),
            ),
            name="Trades",
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
            showlegend=True,
        ),
        row=1,
        col=1,
    )

    # ==========================================
    # Panel 2: The Scoreboard (Running P&L)
    # ==========================================

    # P&L line with fill
    fig.add_trace(
        go.Scatter(
            x=times,
            y=running_pnl,
            mode="lines",
            line=dict(color="black", width=2),
            name="Running P&L",
            fill="tozeroy",
            fillcolor="rgba(0,255,0,0.2)",  # Will be conditional
            showlegend=True,
            hovertemplate="P&L: $%{y:.2f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Add positive/negative fill regions
    positive_pnl = [pnl if pnl >= 0 else 0 for pnl in running_pnl]
    negative_pnl = [pnl if pnl < 0 else 0 for pnl in running_pnl]

    fig.add_trace(
        go.Scatter(
            x=times,
            y=positive_pnl,
            mode="none",
            fill="tozeroy",
            fillcolor="rgba(0,255,0,0.3)",
            name="Profit",
            showlegend=False,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=times,
            y=negative_pnl,
            mode="none",
            fill="tozeroy",
            fillcolor="rgba(255,0,0,0.3)",
            name="Loss",
            showlegend=False,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )

    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)

    # ==========================================
    # Panel 3: The Risk (Net Shares)
    # ==========================================

    # Determine fill color based on position
    fill_color = "rgba(0,150,255,0.2)" if net_shares[-1] >= 0 else "rgba(255,100,0,0.2)"

    fig.add_trace(
        go.Scatter(
            x=times,
            y=net_shares,
            mode="lines",
            line=dict(color="purple", width=2),
            name="Net Shares",
            fill="tozeroy",
            fillcolor=fill_color,
            showlegend=True,
            hovertemplate="Shares: %{y:.1f}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=3, col=1)

    # ==========================================
    # Layout Configuration
    # ==========================================

    title_text = f"Enhanced Analysis: {market_name}"
    if resolved_outcome:
        title_text += f" (Resolved: {resolved_outcome})"
        final_pnl = running_pnl[-1] if running_pnl else 0
        title_text += f" | Final P&L: ${final_pnl:+.2f}"

    fig.update_layout(
        height=1000,
        title_text=title_text,
        title_font_size=16,
        showlegend=True,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # Update axes
    fig.update_yaxes(title_text="Price (¢)", row=1, col=1, range=[-5, 105])
    fig.update_yaxes(title_text="P&L ($)", row=2, col=1)
    fig.update_yaxes(title_text="Net Shares", row=3, col=1)
    fig.update_xaxes(title_text="Time", row=3, col=1)

    # Add gridlines
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.2)")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.2)")

    # Save as interactive HTML with sanitized filename to output directory
    out = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    safe_market_name = _sanitize_filename(market_name, max_length=30)
    filepath = out / f"enhanced_chart_{safe_market_name}.html"
    fig.write_html(str(filepath))
    logger.info("Enhanced battlefield chart saved: %s", filepath)

    if show:
        fig.show()
    return str(filepath)
