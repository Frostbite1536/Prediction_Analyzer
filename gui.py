#!/usr/bin/env python3
"""
GUI Application for Prediction Analyzer
Provides an intuitive graphical interface for analyzing prediction market trades
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import sys
from typing import List, Optional
from datetime import datetime

# Add the package directory to Python path
package_dir = Path(__file__).parent
sys.path.insert(0, str(package_dir))

from prediction_analyzer.trade_loader import load_trades, Trade
from prediction_analyzer.trade_filter import filter_trades_by_market_slug, get_unique_markets, group_trades_by_market
from prediction_analyzer.filters import filter_by_date, filter_by_trade_type, filter_by_pnl
from prediction_analyzer.pnl import calculate_global_pnl_summary, calculate_market_pnl_summary
from prediction_analyzer.charts.simple import generate_simple_chart
from prediction_analyzer.charts.pro import generate_pro_chart
from prediction_analyzer.charts.enhanced import generate_enhanced_chart
from prediction_analyzer.charts.global_chart import generate_global_dashboard
from prediction_analyzer.reporting.report_data import export_to_csv, export_to_excel
from prediction_analyzer.utils.auth import get_signing_message, authenticate
from prediction_analyzer.utils.data import fetch_trade_history


class PredictionAnalyzerGUI:
    """Main GUI application for Prediction Analyzer"""

    def __init__(self, root):
        self.root = root
        self.root.title("Prediction Market Trade Analyzer")
        self.root.geometry("1200x800")

        # Data storage
        self.all_trades: List[Trade] = []
        self.filtered_trades: List[Trade] = []
        self.current_file_path: Optional[str] = None
        self.market_slugs: List[str] = []  # Initialize to prevent AttributeError

        # Configure style
        self.setup_style()

        # Create main layout
        self.create_menu_bar()
        self.create_main_interface()

    def setup_style(self):
        """Configure ttk styles for better appearance"""
        style = ttk.Style()
        style.theme_use('clam')

        # Use cross-platform font family (works on Windows, macOS, Linux)
        # 'TkDefaultFont' is always available, fallback chain for explicit fonts
        self.default_font = ('DejaVu Sans', 'Helvetica', 'Arial', 'TkDefaultFont')
        self.mono_font = ('DejaVu Sans Mono', 'Consolas', 'Courier', 'TkFixedFont')

        # Configure colors with cross-platform fonts
        style.configure('Title.TLabel', font=(self.default_font[0], 16, 'bold'))
        style.configure('Subtitle.TLabel', font=(self.default_font[0], 12, 'bold'))
        style.configure('Info.TLabel', font=(self.default_font[0], 10))
        style.configure('Success.TLabel', foreground='green', font=(self.default_font[0], 10, 'bold'))
        style.configure('Error.TLabel', foreground='red', font=(self.default_font[0], 10, 'bold'))

    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Trades from File...", command=self.load_file)
        file_menu.add_command(label="Load Trades from API...", command=self.load_from_api)
        file_menu.add_separator()
        file_menu.add_command(label="Export to CSV...", command=lambda: self.export_data('csv'))
        file_menu.add_command(label="Export to Excel...", command=lambda: self.export_data('excel'))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Analysis menu
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analysis", menu=analysis_menu)
        analysis_menu.add_command(label="Global PnL Summary", command=self.show_global_summary)
        analysis_menu.add_command(label="Generate Dashboard", command=self.generate_dashboard)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def create_main_interface(self):
        """Create the main interface layout"""
        # Main container with padding
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(2, weight=1)

        # Header section
        self.create_header(main_container)

        # Control panel
        self.create_control_panel(main_container)

        # Notebook for tabbed interface
        self.notebook = ttk.Notebook(main_container)
        self.notebook.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)

        # Create tabs
        self.create_summary_tab()
        self.create_markets_tab()
        self.create_filters_tab()
        self.create_charts_tab()

    def create_header(self, parent):
        """Create header section"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        title_label = ttk.Label(
            header_frame,
            text="Prediction Market Trade Analyzer",
            style='Title.TLabel'
        )
        title_label.grid(row=0, column=0, sticky=tk.W)

        self.status_label = ttk.Label(
            header_frame,
            text="No file loaded",
            style='Info.TLabel'
        )
        self.status_label.grid(row=1, column=0, sticky=tk.W)

    def create_control_panel(self, parent):
        """Create control panel with main action buttons"""
        control_frame = ttk.LabelFrame(parent, text="Quick Actions", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Private key input section
        ttk.Label(control_frame, text="Private Key:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.private_key_entry = ttk.Entry(control_frame, width=40, show="*")
        self.private_key_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)

        ttk.Button(
            control_frame,
            text="Load from API",
            command=self.load_from_api
        ).grid(row=0, column=3, padx=5, pady=2)

        # Action buttons row
        ttk.Button(
            control_frame,
            text="Load Trades File",
            command=self.load_file
        ).grid(row=1, column=0, padx=5, pady=2)

        ttk.Button(
            control_frame,
            text="Global Summary",
            command=self.show_global_summary
        ).grid(row=1, column=1, padx=5, pady=2)

        ttk.Button(
            control_frame,
            text="Generate Dashboard",
            command=self.generate_dashboard
        ).grid(row=1, column=2, padx=5, pady=2)

        ttk.Button(
            control_frame,
            text="Export CSV",
            command=lambda: self.export_data('csv')
        ).grid(row=1, column=3, padx=5, pady=2)

        ttk.Button(
            control_frame,
            text="Export Excel",
            command=lambda: self.export_data('excel')
        ).grid(row=1, column=4, padx=5, pady=2)

    def create_summary_tab(self):
        """Create global summary tab"""
        summary_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(summary_frame, text="Global Summary")

        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(1, weight=1)

        # Summary info
        info_frame = ttk.Frame(summary_frame)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(
            info_frame,
            text="Trade Statistics",
            style='Subtitle.TLabel'
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.summary_text = scrolledtext.ScrolledText(
            summary_frame,
            width=80,
            height=20,
            font=(self.mono_font[0], 10)
        )
        self.summary_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def create_markets_tab(self):
        """Create market analysis tab"""
        markets_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(markets_frame, text="Market Analysis")

        markets_frame.columnconfigure(1, weight=1)
        markets_frame.rowconfigure(1, weight=1)

        # Market selection
        ttk.Label(
            markets_frame,
            text="Select Market:",
            style='Subtitle.TLabel'
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # Market listbox with scrollbar
        listbox_frame = ttk.Frame(markets_frame)
        listbox_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.market_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            height=15,
            font=(self.default_font[0], 10)
        )
        self.market_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.market_listbox.yview)

        # Market action buttons
        button_frame = ttk.Frame(markets_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Button(
            button_frame,
            text="Show Market Summary",
            command=self.show_market_summary
        ).grid(row=0, column=0, padx=5)

        ttk.Button(
            button_frame,
            text="Simple Chart",
            command=lambda: self.generate_market_chart('simple')
        ).grid(row=0, column=1, padx=5)

        ttk.Button(
            button_frame,
            text="Pro Chart",
            command=lambda: self.generate_market_chart('pro')
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            button_frame,
            text="Enhanced Chart",
            command=lambda: self.generate_market_chart('enhanced')
        ).grid(row=0, column=3, padx=5)

        # Market summary display
        ttk.Label(
            markets_frame,
            text="Market Details:",
            style='Subtitle.TLabel'
        ).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))

        self.market_details_text = scrolledtext.ScrolledText(
            markets_frame,
            width=80,
            height=10,
            font=(self.mono_font[0], 10)
        )
        self.market_details_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

    def create_filters_tab(self):
        """Create filters tab"""
        filters_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(filters_frame, text="Filters")

        # Date filters
        date_frame = ttk.LabelFrame(filters_frame, text="Date Range", padding="10")
        date_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(date_frame, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W)
        self.start_date_entry = ttk.Entry(date_frame, width=20)
        self.start_date_entry.grid(row=0, column=1, padx=5, pady=2)
        # Bind Enter key to apply filters
        self.start_date_entry.bind('<Return>', lambda e: self.apply_filters())

        ttk.Label(date_frame, text="End Date (YYYY-MM-DD):").grid(row=1, column=0, sticky=tk.W)
        self.end_date_entry = ttk.Entry(date_frame, width=20)
        self.end_date_entry.grid(row=1, column=1, padx=5, pady=2)
        self.end_date_entry.bind('<Return>', lambda e: self.apply_filters())

        # Format hint label
        ttk.Label(date_frame, text="(e.g., 2024-01-15)", style='Info.TLabel').grid(row=0, column=2, sticky=tk.W, padx=5)

        # Trade type filters
        type_frame = ttk.LabelFrame(filters_frame, text="Trade Type", padding="10")
        type_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.buy_var = tk.BooleanVar(value=True)
        self.sell_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(type_frame, text="Buy", variable=self.buy_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(type_frame, text="Sell", variable=self.sell_var).grid(row=0, column=1, sticky=tk.W)

        # PnL filters
        pnl_frame = ttk.LabelFrame(filters_frame, text="PnL Range", padding="10")
        pnl_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(pnl_frame, text="Minimum PnL ($):").grid(row=0, column=0, sticky=tk.W)
        self.min_pnl_entry = ttk.Entry(pnl_frame, width=20)
        self.min_pnl_entry.grid(row=0, column=1, padx=5, pady=2)
        self.min_pnl_entry.bind('<Return>', lambda e: self.apply_filters())

        ttk.Label(pnl_frame, text="Maximum PnL ($):").grid(row=1, column=0, sticky=tk.W)
        self.max_pnl_entry = ttk.Entry(pnl_frame, width=20)
        self.max_pnl_entry.grid(row=1, column=1, padx=5, pady=2)
        self.max_pnl_entry.bind('<Return>', lambda e: self.apply_filters())

        # Format hint label
        ttk.Label(pnl_frame, text="(e.g., -100.50, 500)", style='Info.TLabel').grid(row=0, column=2, sticky=tk.W, padx=5)

        # Filter buttons
        button_frame = ttk.Frame(filters_frame)
        button_frame.grid(row=3, column=0, sticky=tk.W, pady=10)

        ttk.Button(
            button_frame,
            text="Apply Filters",
            command=self.apply_filters
        ).grid(row=0, column=0, padx=5)

        ttk.Button(
            button_frame,
            text="Clear Filters",
            command=self.clear_filters
        ).grid(row=0, column=1, padx=5)

        # Filter status
        self.filter_status_label = ttk.Label(
            filters_frame,
            text="No filters applied",
            style='Info.TLabel'
        )
        self.filter_status_label.grid(row=4, column=0, sticky=tk.W)

    def create_charts_tab(self):
        """Create charts tab"""
        charts_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(charts_frame, text="Charts")

        ttk.Label(
            charts_frame,
            text="Chart Generation",
            style='Subtitle.TLabel'
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        info_text = (
            "Generate various types of charts to visualize your trading data.\n\n"
            "- Simple Chart: Basic matplotlib chart for quick visualization\n"
            "- Pro Chart: Interactive Plotly chart with advanced features\n"
            "- Enhanced Chart: Battlefield-style visualization\n"
            "- Dashboard: Multi-market overview dashboard\n\n"
            "Note: For market-specific charts, go to the Market Analysis tab and select a market."
        )

        info_label = ttk.Label(charts_frame, text=info_text, justify=tk.LEFT)
        info_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 20))

        # Dashboard button
        dashboard_frame = ttk.LabelFrame(charts_frame, text="Global Charts", padding="10")
        dashboard_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))

        ttk.Button(
            dashboard_frame,
            text="Generate Multi-Market Dashboard",
            command=self.generate_dashboard
        ).grid(row=0, column=0, pady=5)

    def load_file(self):
        """Load trades from a file"""
        file_path = filedialog.askopenfilename(
            title="Select Trades File",
            filetypes=[
                ("All Supported", "*.json *.csv *.xlsx"),
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return

        try:
            self.all_trades = load_trades(file_path)
            self.filtered_trades = self.all_trades.copy()
            self.current_file_path = file_path

            # Update status
            filename = Path(file_path).name
            self.status_label.config(
                text=f"Loaded: {filename} ({len(self.all_trades)} trades)"
            )

            # Update displays
            self.update_markets_list()
            self.update_summary_display()

            messagebox.showinfo(
                "Success",
                f"Successfully loaded {len(self.all_trades)} trades from {filename}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")

    def load_from_api(self):
        """Load trades from API using private key"""
        private_key = self.private_key_entry.get().strip()

        if not private_key:
            messagebox.showwarning("Missing Private Key", "Please enter your private key.")
            return

        try:
            # Show progress
            self.status_label.config(text="Authenticating...")
            self.root.update()

            # Get signing message
            signing_message = get_signing_message()
            if not signing_message:
                messagebox.showerror("Error", "Failed to get signing message from API")
                self.status_label.config(text="Authentication failed")
                return

            # Authenticate
            session_cookie, address = authenticate(private_key, signing_message)
            if not session_cookie:
                messagebox.showerror("Error", "Authentication failed. Please check your private key.")
                self.status_label.config(text="Authentication failed")
                return

            # Update status
            self.status_label.config(text=f"Authenticated as {address[:10]}... Fetching trades...")
            self.root.update()

            # Fetch trade history
            raw_trades = fetch_trade_history(session_cookie)

            if not raw_trades:
                messagebox.showinfo("No Trades", "No trades found for this account.")
                self.status_label.config(text=f"Authenticated as {address[:10]}... (0 trades)")
                return

            # Convert raw trades to Trade objects
            from prediction_analyzer.trade_loader import load_trades
            import json
            import tempfile

            # Save raw trades to temporary file and load them using existing loader
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                json.dump(raw_trades, tmp)
                tmp_path = tmp.name

            try:
                self.all_trades = load_trades(tmp_path)
                self.filtered_trades = self.all_trades.copy()
                self.current_file_path = None  # Mark as API-loaded

                # Update status
                self.status_label.config(
                    text=f"Loaded from API: {address[:10]}... ({len(self.all_trades)} trades)"
                )

                # Update displays
                self.update_markets_list()
                self.update_summary_display()

                messagebox.showinfo(
                    "Success",
                    f"Successfully loaded {len(self.all_trades)} trades from API\nAddress: {address}"
                )
            finally:
                # Clean up temp file
                import os
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load trades from API:\n{str(e)}")
            self.status_label.config(text="Failed to load from API")

    def update_markets_list(self):
        """Update the markets listbox while preserving selection if possible"""
        # Remember current selection before clearing
        current_selection = self.market_listbox.curselection()
        selected_slug = None
        if current_selection and self.market_slugs:
            idx = current_selection[0]
            if idx < len(self.market_slugs):
                selected_slug = self.market_slugs[idx]

        self.market_listbox.delete(0, tk.END)

        if not self.filtered_trades:
            self.market_slugs = []
            return

        markets = get_unique_markets(self.filtered_trades)
        self.market_slugs = sorted(markets.keys())

        new_selection_idx = None
        for i, slug in enumerate(self.market_slugs):
            title = markets[slug]
            # Truncate with "..." indicator if title is too long
            if len(title) > 67:
                display_text = f"{title[:67]}..."
            else:
                display_text = title
            self.market_listbox.insert(tk.END, display_text)

            # Check if this was the previously selected market
            if slug == selected_slug:
                new_selection_idx = i

        # Restore selection if the market still exists in filtered list
        if new_selection_idx is not None:
            self.market_listbox.selection_set(new_selection_idx)
            self.market_listbox.see(new_selection_idx)

    def update_summary_display(self):
        """Update the global summary display"""
        self.summary_text.delete(1.0, tk.END)

        if not self.filtered_trades:
            self.summary_text.insert(tk.END, "No trades loaded.\n")
            return

        try:
            summary = calculate_global_pnl_summary(self.filtered_trades)

            output = []
            output.append("=" * 60)
            output.append("GLOBAL PnL SUMMARY")
            output.append("=" * 60)
            output.append(f"\nTotal Trades: {summary['total_trades']}")
            output.append(f"Total PnL: ${summary['total_pnl']:.2f}")
            output.append(f"Average PnL per Trade: ${summary['avg_pnl']:.2f}")
            output.append(f"\nWinning Trades: {summary['winning_trades']}")
            output.append(f"Losing Trades: {summary['losing_trades']}")
            output.append(f"Win Rate: {summary['win_rate']:.1f}%")
            output.append(f"\nTotal Invested: ${summary['total_invested']:.2f}")
            output.append(f"Total Returned: ${summary['total_returned']:.2f}")
            output.append(f"ROI: {summary['roi']:.2f}%")
            output.append("\n" + "=" * 60)

            self.summary_text.insert(tk.END, "\n".join(output))

        except Exception as e:
            self.summary_text.insert(tk.END, f"Error calculating summary:\n{str(e)}")

    def show_global_summary(self):
        """Show global summary and switch to summary tab"""
        if not self.all_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        self.update_summary_display()
        self.notebook.select(0)  # Switch to summary tab

    def show_market_summary(self):
        """Show summary for selected market"""
        selection = self.market_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a market first.")
            return

        idx = selection[0]
        if idx >= len(self.market_slugs):
            return

        market_slug = self.market_slugs[idx]
        market_trades = filter_trades_by_market_slug(self.filtered_trades, market_slug)

        if not market_trades:
            messagebox.showinfo("No Trades", f"No trades found for this market.")
            return

        try:
            summary = calculate_market_pnl_summary(market_trades)

            self.market_details_text.delete(1.0, tk.END)

            output = []
            output.append("=" * 60)
            output.append(f"MARKET: {summary['market_title']}")
            output.append("=" * 60)
            output.append(f"\nTotal Trades: {summary['total_trades']}")
            output.append(f"Total PnL: ${summary['total_pnl']:.2f}")
            output.append(f"Average PnL per Trade: ${summary['avg_pnl']:.2f}")
            output.append(f"\nWinning Trades: {summary['winning_trades']}")
            output.append(f"Losing Trades: {summary['losing_trades']}")
            output.append(f"Win Rate: {summary['win_rate']:.1f}%")
            output.append(f"\nTotal Invested: ${summary['total_invested']:.2f}")
            output.append(f"Total Returned: ${summary['total_returned']:.2f}")
            output.append(f"ROI: {summary['roi']:.2f}%")

            if summary.get('market_outcome'):
                output.append(f"\nMarket Outcome: {summary['market_outcome']}")

            output.append("\n" + "=" * 60)

            self.market_details_text.insert(tk.END, "\n".join(output))

        except Exception as e:
            self.market_details_text.delete(1.0, tk.END)
            self.market_details_text.insert(tk.END, f"Error:\n{str(e)}")

    def generate_market_chart(self, chart_type):
        """Generate chart for selected market"""
        selection = self.market_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a market first.")
            return

        idx = selection[0]
        if idx >= len(self.market_slugs):
            return

        market_slug = self.market_slugs[idx]
        markets = get_unique_markets(self.filtered_trades)
        market_title = markets.get(market_slug, market_slug)

        market_trades = filter_trades_by_market_slug(self.filtered_trades, market_slug)

        if not market_trades:
            messagebox.showinfo("No Trades", f"No trades found for this market.")
            return

        try:
            if chart_type == 'simple':
                generate_simple_chart(market_trades, market_title)
            elif chart_type == 'pro':
                generate_pro_chart(market_trades, market_title)
            elif chart_type == 'enhanced':
                generate_enhanced_chart(market_trades, market_title)

            messagebox.showinfo("Success", f"{chart_type.capitalize()} chart generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate chart:\n{str(e)}")

    def generate_dashboard(self):
        """Generate multi-market dashboard"""
        if not self.filtered_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        try:
            # Group trades by market for the dashboard
            trades_by_market = group_trades_by_market(self.filtered_trades)
            generate_global_dashboard(trades_by_market)
            messagebox.showinfo("Success", "Dashboard generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate dashboard:\n{str(e)}")

    def _validate_date_format(self, date_str: str) -> bool:
        """Validate date string is in YYYY-MM-DD format"""
        if not date_str:
            return True  # Empty is valid (no filter)
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _validate_numeric(self, value_str: str) -> bool:
        """Validate string can be converted to float"""
        if not value_str:
            return True  # Empty is valid (no filter)
        try:
            float(value_str)
            return True
        except ValueError:
            return False

    def apply_filters(self):
        """Apply filters to trades with input validation"""
        if not self.all_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        # Validate date formats
        start_date = self.start_date_entry.get().strip()
        end_date = self.end_date_entry.get().strip()

        if start_date and not self._validate_date_format(start_date):
            messagebox.showerror(
                "Invalid Date Format",
                f"Start date '{start_date}' is not valid.\n\n"
                "Please use YYYY-MM-DD format (e.g., 2024-01-15)."
            )
            self.start_date_entry.focus_set()
            return

        if end_date and not self._validate_date_format(end_date):
            messagebox.showerror(
                "Invalid Date Format",
                f"End date '{end_date}' is not valid.\n\n"
                "Please use YYYY-MM-DD format (e.g., 2024-01-15)."
            )
            self.end_date_entry.focus_set()
            return

        # Validate date range (start should be before or equal to end)
        if start_date and end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                messagebox.showerror(
                    "Invalid Date Range",
                    f"Start date ({start_date}) is after end date ({end_date}).\n\n"
                    "Please ensure start date is before or equal to end date."
                )
                self.start_date_entry.focus_set()
                return

        # Validate PnL values
        min_pnl_str = self.min_pnl_entry.get().strip()
        max_pnl_str = self.max_pnl_entry.get().strip()

        if min_pnl_str and not self._validate_numeric(min_pnl_str):
            messagebox.showerror(
                "Invalid PnL Value",
                f"Minimum PnL '{min_pnl_str}' is not a valid number.\n\n"
                "Please enter a numeric value (e.g., -100.50 or 500)."
            )
            self.min_pnl_entry.focus_set()
            return

        if max_pnl_str and not self._validate_numeric(max_pnl_str):
            messagebox.showerror(
                "Invalid PnL Value",
                f"Maximum PnL '{max_pnl_str}' is not a valid number.\n\n"
                "Please enter a numeric value (e.g., -100.50 or 500)."
            )
            self.max_pnl_entry.focus_set()
            return

        # Validate PnL range
        if min_pnl_str and max_pnl_str:
            min_pnl_val = float(min_pnl_str)
            max_pnl_val = float(max_pnl_str)
            if min_pnl_val > max_pnl_val:
                messagebox.showerror(
                    "Invalid PnL Range",
                    f"Minimum PnL (${min_pnl_val:.2f}) is greater than maximum PnL (${max_pnl_val:.2f}).\n\n"
                    "Please ensure minimum is less than or equal to maximum."
                )
                self.min_pnl_entry.focus_set()
                return

        try:
            filtered = self.all_trades.copy()
            filters_applied = []

            # Date filters
            if start_date or end_date:
                filtered = filter_by_date(
                    filtered,
                    start_date if start_date else None,
                    end_date if end_date else None
                )
                filters_applied.append("Date range")

            # Trade type filters
            trade_types = []
            if self.buy_var.get():
                trade_types.append("Buy")
            if self.sell_var.get():
                trade_types.append("Sell")

            # Handle case where neither checkbox is checked (show no trades)
            if not trade_types:
                filtered = []
                filters_applied.append("Type: None (no trades match)")
            elif len(trade_types) < 2:
                filtered = filter_by_trade_type(filtered, trade_types)
                filters_applied.append(f"Type: {', '.join(trade_types)}")

            # PnL filters
            min_pnl = float(min_pnl_str) if min_pnl_str else None
            max_pnl = float(max_pnl_str) if max_pnl_str else None

            if min_pnl is not None or max_pnl is not None:
                filtered = filter_by_pnl(filtered, min_pnl, max_pnl)
                filters_applied.append("PnL range")

            # Update filtered trades
            self.filtered_trades = filtered

            # Update displays
            self.update_markets_list()
            self.update_summary_display()

            # Update status
            if filters_applied:
                status_text = f"Filters applied: {', '.join(filters_applied)} ({len(filtered)} trades)"
            else:
                status_text = "No filters applied"

            self.filter_status_label.config(text=status_text)

            messagebox.showinfo(
                "Filters Applied",
                f"Filtered to {len(filtered)} trades from {len(self.all_trades)} total"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply filters:\n{str(e)}")

    def clear_filters(self):
        """Clear all filters"""
        # Clear entry fields
        self.start_date_entry.delete(0, tk.END)
        self.end_date_entry.delete(0, tk.END)
        self.min_pnl_entry.delete(0, tk.END)
        self.max_pnl_entry.delete(0, tk.END)

        # Reset checkboxes
        self.buy_var.set(True)
        self.sell_var.set(True)

        # Reset filtered trades only if we have data
        if self.all_trades:
            self.filtered_trades = self.all_trades.copy()

            # Update displays
            self.update_markets_list()
            self.update_summary_display()

            # Update status
            self.filter_status_label.config(text="Filters cleared")
            messagebox.showinfo("Filters Cleared", "All filters have been removed.")
        else:
            # No data loaded, just reset the filter status
            self.filter_status_label.config(text="No filters applied")
            messagebox.showinfo("Filters Cleared", "Filter fields have been reset.")

    def _generate_export_filename(self, extension: str) -> str:
        """Generate a default filename for export based on source and timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.current_file_path:
            # Base name from loaded file
            base_name = Path(self.current_file_path).stem
            return f"{base_name}_export_{timestamp}.{extension}"
        else:
            # API data or no source
            return f"trades_export_{timestamp}.{extension}"

    def export_data(self, format_type):
        """Export data to CSV or Excel"""
        if not self.filtered_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        if format_type == 'csv':
            default_filename = self._generate_export_filename("csv")
            file_path = filedialog.asksaveasfilename(
                title="Export to CSV",
                defaultextension=".csv",
                initialfile=default_filename,
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if file_path:
                try:
                    export_to_csv(self.filtered_trades, file_path)
                    messagebox.showinfo("Success", f"Exported {len(self.filtered_trades)} trades to:\n{file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Export failed:\n{str(e)}")

        elif format_type == 'excel':
            default_filename = self._generate_export_filename("xlsx")
            file_path = filedialog.asksaveasfilename(
                title="Export to Excel",
                defaultextension=".xlsx",
                initialfile=default_filename,
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            if file_path:
                try:
                    export_to_excel(self.filtered_trades, file_path)
                    messagebox.showinfo("Success", f"Exported {len(self.filtered_trades)} trades to:\n{file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Export failed:\n{str(e)}")

    def show_about(self):
        """Show about dialog"""
        about_text = (
            "Prediction Market Trade Analyzer\n\n"
            "A comprehensive tool for analyzing prediction market trades.\n\n"
            "Features:\n"
            "- Load trades from JSON, CSV, or Excel\n"
            "- Calculate global and market-specific PnL\n"
            "- Filter trades by date, type, and PnL\n"
            "- Generate multiple chart types\n"
            "- Export data in various formats\n\n"
            "Version: 1.0\n"
            "License: MIT"
        )
        messagebox.showinfo("About", about_text)


def main():
    """Main entry point for GUI application"""
    root = tk.Tk()
    app = PredictionAnalyzerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
