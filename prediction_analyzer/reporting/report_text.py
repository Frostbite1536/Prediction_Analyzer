# prediction_analyzer/reporting/report_text.py
"""
Text-based report generation
"""
from typing import List
from datetime import datetime
from ..trade_loader import Trade
from ..pnl import calculate_market_pnl, calculate_global_pnl_summary

def print_global_summary(trades: List[Trade]):
    """
    Print a formatted global PnL summary to console
    """
    summary = calculate_global_pnl_summary(trades)
    market_stats = calculate_market_pnl(trades)

    print("\n" + "="*60)
    print("💰 GLOBAL PORTFOLIO SUMMARY")
    print("="*60)
    print(f"Total Trades:          {summary['total_trades']}")
    print(f"Total Volume:          ${summary['total_volume']:,.2f}")
    print(f"Total Realized PnL:    ${summary['total_pnl']:,.2f}")
    print(f"Win Rate:              {summary['win_rate']:.1f}%")
    print(f"Avg PnL per Trade:     ${summary['avg_pnl_per_trade']:.2f}")
    print("-" * 60)

    # Top markets by PnL
    sorted_markets = sorted(market_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True)

    print("\n📊 TOP MARKETS BY PNL:")
    print(f"{'Rank':<6} {'Market':<40} {'PnL':>12}")
    print("-" * 60)

    for i, (slug, stats) in enumerate(sorted_markets[:10], 1):
        market_name = stats['market_name'][:37] + "..." if len(stats['market_name']) > 40 else stats['market_name']
        print(f"{i:<6} {market_name:<40} ${stats['total_pnl']:>10,.2f}")

    print("="*60 + "\n")

def generate_text_report(trades: List[Trade], filename: str = None):
    """
    Generate a detailed text report file

    Args:
        trades: List of Trade objects
        filename: Output filename (auto-generated if None)
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trade_report_{timestamp}.txt"

    summary = calculate_global_pnl_summary(trades)
    market_stats = calculate_market_pnl(trades)

    lines = []
    lines.append("="*70)
    lines.append("PREDICTION MARKET TRADE ANALYSIS REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("="*70)
    lines.append("")

    # Global summary
    lines.append("GLOBAL SUMMARY")
    lines.append("-"*70)
    lines.append(f"Total Trades:           {summary['total_trades']}")
    lines.append(f"Winning Trades:         {summary['winning_trades']}")
    lines.append(f"Losing Trades:          {summary['losing_trades']}")
    lines.append(f"Win Rate:               {summary['win_rate']:.2f}%")
    lines.append(f"Total Volume:           ${summary['total_volume']:,.2f}")
    lines.append(f"Total Realized PnL:     ${summary['total_pnl']:,.2f}")
    lines.append(f"Average PnL per Trade:  ${summary['avg_pnl_per_trade']:.2f}")
    lines.append("")

    # Market breakdown
    lines.append("MARKET BREAKDOWN")
    lines.append("-"*70)
    lines.append(f"{'Market':<45} {'Trades':>8} {'Volume':>12} {'PnL':>12}")
    lines.append("-"*70)

    sorted_markets = sorted(market_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    for slug, stats in sorted_markets:
        market_name = stats['market_name'][:42]
        lines.append(
            f"{market_name:<45} {stats['trade_count']:>8} "
            f"${stats['total_volume']:>10,.2f} ${stats['total_pnl']:>10,.2f}"
        )

    lines.append("")
    lines.append("="*70)
    lines.append("END OF REPORT")
    lines.append("="*70)

    # Write to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"✅ Report saved: {filename}")
