# prediction_analyzer/__main__.py
"""
Main CLI entry point for the prediction analyzer
"""
import argparse
import sys
from pathlib import Path

from .trade_loader import load_trades, save_trades
from .utils.auth import get_signing_message, authenticate
from .utils.data import fetch_trade_history
from .core.interactive import interactive_menu
from .reporting.report_text import print_global_summary, generate_text_report
from .charts.simple import generate_simple_chart
from .charts.pro import generate_pro_chart
from .charts.enhanced import generate_enhanced_chart
from .charts.global_chart import generate_global_dashboard
from .trade_filter import filter_trades_by_market_slug, get_unique_markets
from .filters import filter_by_date, filter_by_trade_type, filter_by_pnl
from .reporting.report_data import export_to_csv, export_to_excel
from .config import DEFAULT_TRADE_FILE

def main():
    parser = argparse.ArgumentParser(
        description="Prediction Market Trade Analyzer - Analyze and visualize your trades",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (novice-friendly)
  python -m prediction_analyzer --file trades.json

  # Quick global summary
  python -m prediction_analyzer --file trades.json --global

  # Analyze specific market
  python -m prediction_analyzer --file trades.json --market "ETH-USD" --chart pro
  python -m prediction_analyzer --file trades.json --market "ETH-USD" --chart enhanced

  # Fetch trades from API
  python -m prediction_analyzer --fetch --key "0xYOURPRIVATEKEY"

  # Filter and export
  python -m prediction_analyzer --file trades.json --start-date 2024-01-01 --export trades.csv
        """
    )

    # Data source options
    data_group = parser.add_argument_group('Data Source')
    data_group.add_argument('--file', '-f', type=str, help='Path to trades JSON/CSV/XLSX file')
    data_group.add_argument('--fetch', action='store_true', help='Fetch live trades from API')
    data_group.add_argument('--key', '-k', type=str, help='Private key for API authentication')

    # Analysis options
    analysis_group = parser.add_argument_group('Analysis')
    analysis_group.add_argument('--market', '-m', type=str, help='Analyze specific market (slug or name)')
    analysis_group.add_argument('--global', dest='global_view', action='store_true', help='Show global PnL summary')
    analysis_group.add_argument('--chart', '-c', choices=['simple', 'pro', 'enhanced'], default='simple',
                                help='Chart type: simple, pro, or enhanced (default: simple)')
    analysis_group.add_argument('--dashboard', action='store_true', help='Generate multi-market dashboard')

    # Filter options
    filter_group = parser.add_argument_group('Filters')
    filter_group.add_argument('--start-date', type=str, help='Filter from date (YYYY-MM-DD)')
    filter_group.add_argument('--end-date', type=str, help='Filter to date (YYYY-MM-DD)')
    filter_group.add_argument('--type', nargs='+', choices=['Buy', 'Sell'], help='Filter by trade type')
    filter_group.add_argument('--min-pnl', type=float, help='Minimum PnL threshold')
    filter_group.add_argument('--max-pnl', type=float, help='Maximum PnL threshold')

    # Export options
    export_group = parser.add_argument_group('Export')
    export_group.add_argument('--export', type=str, help='Export filtered trades (CSV or XLSX)')
    export_group.add_argument('--report', action='store_true', help='Generate text report')

    # Other options
    parser.add_argument('--no-interactive', action='store_true', help='Disable interactive mode')

    args = parser.parse_args()

    # Load or fetch trades
    trades = []

    if args.fetch:
        # Fetch from API
        if not args.key:
            print("❌ --key required for fetching trades from API")
            sys.exit(1)

        print("🔐 Authenticating...")
        signing_message = get_signing_message()
        if not signing_message:
            print("❌ Failed to get signing message")
            sys.exit(1)

        cookie, address = authenticate(args.key, signing_message)
        if not cookie:
            print("❌ Authentication failed")
            sys.exit(1)

        print(f"✅ Authenticated as {address}")

        raw_trades = fetch_trade_history(cookie)
        save_trades(raw_trades, DEFAULT_TRADE_FILE)

        # Convert to Trade objects
        trades = load_trades(DEFAULT_TRADE_FILE)

    elif args.file:
        # Load from file
        trades = load_trades(args.file)
        if not trades:
            print(f"❌ Failed to load trades from {args.file}")
            sys.exit(1)

    elif Path(DEFAULT_TRADE_FILE).exists():
        # Try default file
        print(f"📂 Loading from default file: {DEFAULT_TRADE_FILE}")
        trades = load_trades(DEFAULT_TRADE_FILE)

    else:
        print("❌ No trade data available.")
        print("   Use --file to load from a file, or --fetch with --key to download from API")
        parser.print_help()
        sys.exit(1)

    if not trades:
        print("❌ No trades to analyze")
        sys.exit(1)

    print(f"✅ Loaded {len(trades)} trades\n")

    # Apply filters
    original_count = len(trades)

    if args.start_date or args.end_date:
        trades = filter_by_date(trades, args.start_date, args.end_date)
        print(f"🔍 Date filter: {len(trades)}/{original_count} trades")

    if args.type:
        trades = filter_by_trade_type(trades, args.type)
        print(f"🔍 Type filter: {len(trades)}/{original_count} trades")

    if args.min_pnl is not None or args.max_pnl is not None:
        trades = filter_by_pnl(trades, args.min_pnl, args.max_pnl)
        print(f"🔍 PnL filter: {len(trades)}/{original_count} trades")

    if len(trades) != original_count:
        print()

    # Execute commands
    if args.global_view:
        print_global_summary(trades)

    if args.report:
        generate_text_report(trades)

    if args.export:
        if args.export.endswith('.csv'):
            export_to_csv(trades, args.export)
        elif args.export.endswith('.xlsx'):
            export_to_excel(trades, args.export)
        else:
            print("❌ Export file must be .csv or .xlsx")

    if args.dashboard:
        markets = get_unique_markets(trades)
        trades_by_market = {}
        for slug, name in markets.items():
            market_trades = filter_trades_by_market_slug(trades, slug)
            if market_trades:
                trades_by_market[name] = market_trades
        generate_global_dashboard(trades_by_market)

    if args.market:
        # Analyze specific market
        market_trades = filter_trades_by_market_slug(trades, args.market)

        if not market_trades:
            print(f"❌ No trades found for market: {args.market}")
            sys.exit(1)

        market_name = market_trades[0].market

        if args.chart == 'simple':
            generate_simple_chart(market_trades, market_name)
        elif args.chart == 'pro':
            generate_pro_chart(market_trades, market_name)
        elif args.chart == 'enhanced':
            generate_enhanced_chart(market_trades, market_name)
        else:
            generate_simple_chart(market_trades, market_name)

    # Interactive mode (if no other actions specified)
    if not any([args.global_view, args.report, args.export, args.dashboard, args.market]) and not args.no_interactive:
        interactive_menu(trades)

if __name__ == "__main__":
    main()
