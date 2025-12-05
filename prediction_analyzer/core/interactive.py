# prediction_analyzer/core/interactive.py
"""
Interactive CLI menu for novice users
"""
from typing import List
from ..trade_loader import Trade
from ..trade_filter import filter_trades_by_market_slug, get_unique_markets
from ..filters import filter_by_date, filter_by_trade_type, filter_by_pnl
from ..reporting.report_text import print_global_summary, generate_text_report
from ..reporting.report_data import export_to_csv, export_to_excel
from ..charts.simple import generate_simple_chart
from ..charts.pro import generate_pro_chart

def interactive_menu(trades: List[Trade]):
    """
    Interactive menu for exploring and analyzing trades

    Args:
        trades: List of all Trade objects
    """
    print("\n" + "="*60)
    print("   PREDICTION MARKET TRADE ANALYZER")
    print("   Interactive Mode")
    print("="*60)

    while True:
        print("\n📊 MAIN MENU")
        print("-" * 40)
        print("1. Global PnL Summary")
        print("2. Analyze Specific Market")
        print("3. Export All Trades")
        print("4. Generate Full Report")
        print("Q. Quit")
        print("-" * 40)

        choice = input("\nSelect option: ").strip().upper()

        if choice == 'Q':
            print("\n👋 Goodbye!")
            break

        elif choice == '1':
            # Global summary
            print_global_summary(trades)
            input("\nPress Enter to continue...")

        elif choice == '2':
            # Market-specific analysis
            analyze_market_menu(trades)

        elif choice == '3':
            # Export trades
            export_menu(trades)

        elif choice == '4':
            # Full report
            generate_text_report(trades)
            input("\nPress Enter to continue...")

        else:
            print("❌ Invalid option. Please try again.")

def analyze_market_menu(trades: List[Trade]):
    """Submenu for analyzing a specific market"""
    markets = get_unique_markets(trades)

    if not markets:
        print("❌ No markets found in trade data.")
        return

    # Display markets
    slugs = sorted(markets.keys())
    print("\n📈 SELECT MARKET")
    print("-" * 60)
    for i, slug in enumerate(slugs, 1):
        title = markets[slug]
        print(f"{i}. {title[:55]}")
    print("B. Back to main menu")
    print("-" * 60)

    choice = input("\nSelect market number: ").strip().upper()

    if choice == 'B':
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(slugs):
            print("❌ Invalid selection.")
            return

        selected_slug = slugs[idx]
        selected_name = markets[selected_slug]

        # Filter trades for this market
        market_trades = filter_trades_by_market_slug(trades, selected_slug)

        if not market_trades:
            print(f"❌ No trades found for {selected_name}")
            return

        # Apply additional filters
        filtered_trades = apply_filters_menu(market_trades)

        if not filtered_trades:
            print("❌ No trades match the filters.")
            return

        # Chart selection
        print("\n📊 SELECT CHART TYPE")
        print("1. Simple Chart (Quick View)")
        print("2. Professional Chart (Interactive)")

        chart_choice = input("\nSelect chart type (1 or 2): ").strip()

        if chart_choice == '1':
            generate_simple_chart(filtered_trades, selected_name)
        elif chart_choice == '2':
            generate_pro_chart(filtered_trades, selected_name)
        else:
            print("❌ Invalid choice.")

    except ValueError:
        print("❌ Invalid input.")

def apply_filters_menu(trades: List[Trade]) -> List[Trade]:
    """
    Interactive filter application menu

    Returns:
        Filtered list of trades
    """
    filtered = trades

    while True:
        print("\n🔍 FILTERS")
        print("-" * 40)
        print("1. Filter by Date Range")
        print("2. Filter by Trade Type (Buy/Sell)")
        print("3. Filter by PnL Range")
        print("4. Clear Filters")
        print("5. Done (Apply Filters)")
        print("-" * 40)

        choice = input("Select option: ").strip()

        if choice == '1':
            start = input("Start date (YYYY-MM-DD) or Enter to skip: ").strip()
            end = input("End date (YYYY-MM-DD) or Enter to skip: ").strip()
            start = start if start else None
            end = end if end else None
            filtered = filter_by_date(filtered, start, end)
            print(f"✅ {len(filtered)} trades after date filter")

        elif choice == '2':
            print("Select types (comma-separated): Buy, Sell")
            types_str = input("> ").strip()
            if types_str:
                types = [t.strip() for t in types_str.split(',')]
                filtered = filter_by_trade_type(filtered, types)
                print(f"✅ {len(filtered)} trades after type filter")

        elif choice == '3':
            min_pnl = input("Minimum PnL (or Enter to skip): ").strip()
            max_pnl = input("Maximum PnL (or Enter to skip): ").strip()
            min_pnl = float(min_pnl) if min_pnl else None
            max_pnl = float(max_pnl) if max_pnl else None
            filtered = filter_by_pnl(filtered, min_pnl, max_pnl)
            print(f"✅ {len(filtered)} trades after PnL filter")

        elif choice == '4':
            filtered = trades
            print("✅ Filters cleared")

        elif choice == '5':
            break

        else:
            print("❌ Invalid option")

    return filtered

def export_menu(trades: List[Trade]):
    """Export menu for various formats"""
    print("\n💾 EXPORT OPTIONS")
    print("-" * 40)
    print("1. Export to CSV")
    print("2. Export to Excel")
    print("3. Back")
    print("-" * 40)

    choice = input("Select option: ").strip()

    if choice == '1':
        filename = input("Filename (or Enter for default): ").strip()
        filename = filename if filename else "trades_export.csv"
        export_to_csv(trades, filename)

    elif choice == '2':
        filename = input("Filename (or Enter for default): ").strip()
        filename = filename if filename else "trades_export.xlsx"
        export_to_excel(trades, filename)

    input("\nPress Enter to continue...")
