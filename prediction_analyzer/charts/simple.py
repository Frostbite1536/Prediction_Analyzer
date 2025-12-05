# prediction_analyzer/charts/simple.py
"""
Simple chart generation for novice users
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import List
from ..trade_loader import Trade
from ..config import STYLES

def generate_simple_chart(trades: List[Trade], market_name: str, resolved_outcome: str = None):
    """
    Generate a simple 2-panel chart showing price and exposure

    Args:
        trades: List of Trade objects for a specific market
        market_name: Name of the market
        resolved_outcome: "YES" or "NO" if market is resolved
    """
    if not trades:
        print("⚠️ No trades to chart.")
        return

    # Sort trades by timestamp
    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    # Extract data
    times = [t.timestamp for t in sorted_trades]
    prices = [t.price for t in sorted_trades]

    # Calculate exposure over time
    net_exposure = 0
    exposures = []

    for t in sorted_trades:
        if t.type in ["Buy", "Market Buy", "Limit Buy"]:
            net_exposure += t.cost
        else:
            net_exposure -= t.cost
        exposures.append(net_exposure)

    # Calculate final PnL if resolved
    final_pnl = 0
    if resolved_outcome:
        final_shares_yes = sum(t.shares if t.side == "YES" else -t.shares
                              for t in sorted_trades
                              if t.type in ["Buy", "Market Buy", "Limit Buy"])
        final_shares_no = sum(t.shares if t.side == "NO" else -t.shares
                             for t in sorted_trades
                             if t.type in ["Buy", "Market Buy", "Limit Buy"])

        final_value = final_shares_yes if resolved_outcome == "YES" else final_shares_no
        final_pnl = final_value - net_exposure

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Clean title (remove emojis)
    safe_title = market_name.encode('ascii', 'ignore').decode('ascii')
    title_text = f"{safe_title}"
    if resolved_outcome:
        title_text += f"\nResolved: {resolved_outcome} | PnL: ${final_pnl:+.2f}"
    fig.suptitle(title_text, fontsize=14, fontweight='bold')

    # Plot 1: Price with trade bubbles
    ax1.plot(times, prices, color='#1f77b4', alpha=0.5, linewidth=2, label='Price')

    # Add trade markers
    for t in sorted_trades:
        key = (t.type, t.side)
        color, marker, _ = STYLES.get(key, ('gray', 'o', ''))
        size = min(max(t.cost * 2, 20), 500)
        ax1.scatter(t.timestamp, t.price, s=size, c=color, marker=marker,
                   alpha=0.8, edgecolors='black', linewidths=0.5)

    ax1.set_ylabel("Price (¢)", fontsize=11)
    ax1.set_ylim(-5, 105)
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Plot 2: Net exposure
    ax2.fill_between(times, exposures, 0, color='orange', alpha=0.3)
    ax2.plot(times, exposures, color='orange', linewidth=2, label='Net Cash Invested')
    ax2.set_ylabel("Net Cash ($)", fontsize=11)
    ax2.set_xlabel("Time", fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    fig.autofmt_xdate()

    plt.tight_layout()

    # Save chart
    filename = f"chart_{market_name[:30].replace(' ', '_')}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"✅ Chart saved: {filename}")
    plt.show()
    plt.close()
