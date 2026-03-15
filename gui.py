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
import threading

# Add the package directory to Python path
package_dir = Path(__file__).parent
sys.path.insert(0, str(package_dir))

from prediction_analyzer.trade_loader import load_trades, Trade
from prediction_analyzer.trade_filter import (
    filter_trades_by_market_slug,
    get_unique_markets,
    group_trades_by_market,
)
from prediction_analyzer.filters import (
    filter_by_date,
    filter_by_trade_type,
    filter_by_pnl,
    filter_by_side,
)
from prediction_analyzer.pnl import calculate_global_pnl_summary, calculate_market_pnl_summary
from prediction_analyzer.charts.simple import generate_simple_chart
from prediction_analyzer.charts.pro import generate_pro_chart
from prediction_analyzer.charts.enhanced import generate_enhanced_chart
from prediction_analyzer.charts.global_chart import generate_global_dashboard
from prediction_analyzer.reporting.report_data import export_to_csv, export_to_excel, export_to_json
from prediction_analyzer.utils.auth import get_api_key
from prediction_analyzer.utils.data import fetch_trade_history
from prediction_analyzer.metrics import calculate_advanced_metrics
from prediction_analyzer.positions import calculate_open_positions, calculate_concentration_risk
from prediction_analyzer.drawdown import analyze_drawdowns
from prediction_analyzer.tax import calculate_capital_gains
from prediction_analyzer.comparison import compare_periods


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
        self._fetch_lock = threading.Lock()
        self._fetch_in_progress = False

        # Configure style
        self.setup_style()

        # Create main layout
        self.create_menu_bar()
        self.create_main_interface()

    def setup_style(self):
        """Configure ttk styles for better appearance"""
        style = ttk.Style()
        style.theme_use("clam")

        # Use cross-platform font family (works on Windows, macOS, Linux)
        # 'TkDefaultFont' is always available, fallback chain for explicit fonts
        self.default_font = ("DejaVu Sans", "Helvetica", "Arial", "TkDefaultFont")
        self.mono_font = ("DejaVu Sans Mono", "Consolas", "Courier", "TkFixedFont")

        # Configure colors with cross-platform fonts
        style.configure("Title.TLabel", font=(self.default_font[0], 16, "bold"))
        style.configure("Subtitle.TLabel", font=(self.default_font[0], 12, "bold"))
        style.configure("Info.TLabel", font=(self.default_font[0], 10))
        style.configure(
            "Success.TLabel", foreground="green", font=(self.default_font[0], 10, "bold")
        )
        style.configure("Error.TLabel", foreground="red", font=(self.default_font[0], 10, "bold"))

    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Load Trades from File...", command=self.load_file, accelerator="Ctrl+O"
        )
        file_menu.add_command(label="Load Trades from API...", command=self.load_from_api)
        file_menu.add_separator()
        file_menu.add_command(
            label="Export to CSV...", command=lambda: self.export_data("csv"), accelerator="Ctrl+E"
        )
        file_menu.add_command(label="Export to Excel...", command=lambda: self.export_data("excel"))
        file_menu.add_command(label="Export to JSON...", command=lambda: self.export_data("json"))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")

        # Analysis menu
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analysis", menu=analysis_menu)
        analysis_menu.add_command(
            label="Global PnL Summary", command=self.show_global_summary, accelerator="Ctrl+G"
        )
        analysis_menu.add_command(
            label="Generate Dashboard", command=self.generate_dashboard, accelerator="Ctrl+D"
        )
        analysis_menu.add_separator()
        analysis_menu.add_command(
            label="Compare Periods...", command=self.show_compare_periods_dialog
        )

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
        self.create_trades_tab()
        self.create_filters_tab()
        self.create_portfolio_tab()
        self.create_tax_tab()
        self.create_charts_tab()

        # Keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self.load_file())
        self.root.bind("<Control-e>", lambda e: self.export_data("csv"))
        self.root.bind("<Control-d>", lambda e: self.generate_dashboard())
        self.root.bind("<Control-g>", lambda e: self.show_global_summary())
        self.root.bind("<Control-q>", lambda e: self.root.quit())

    def create_header(self, parent):
        """Create header section"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        title_label = ttk.Label(
            header_frame, text="Prediction Market Trade Analyzer", style="Title.TLabel"
        )
        title_label.grid(row=0, column=0, sticky=tk.W)

        self.status_label = ttk.Label(header_frame, text="No file loaded", style="Info.TLabel")
        self.status_label.grid(row=1, column=0, sticky=tk.W)

    def create_control_panel(self, parent):
        """Create control panel with main action buttons"""
        control_frame = ttk.LabelFrame(parent, text="Quick Actions", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Provider selector
        ttk.Label(control_frame, text="Provider:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=2
        )
        self.provider_var = tk.StringVar(value="auto")
        provider_combo = ttk.Combobox(
            control_frame,
            textvariable=self.provider_var,
            values=["auto", "limitless", "polymarket", "kalshi", "manifold"],
            state="readonly",
            width=12,
        )
        provider_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        # API key input section
        ttk.Label(control_frame, text="API Key / Wallet:").grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=2
        )
        self.api_key_entry = ttk.Entry(control_frame, width=35, show="*")
        self.api_key_entry.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=5, pady=2)

        ttk.Button(control_frame, text="Load from API", command=self.load_from_api).grid(
            row=0, column=4, padx=5, pady=2
        )

        # Action buttons row
        ttk.Button(control_frame, text="Load Trades File", command=self.load_file).grid(
            row=1, column=0, padx=5, pady=2
        )

        ttk.Button(control_frame, text="Global Summary", command=self.show_global_summary).grid(
            row=1, column=1, padx=5, pady=2
        )

        ttk.Button(control_frame, text="Generate Dashboard", command=self.generate_dashboard).grid(
            row=1, column=2, padx=5, pady=2
        )

        ttk.Button(control_frame, text="Export CSV", command=lambda: self.export_data("csv")).grid(
            row=1, column=3, padx=5, pady=2
        )

        ttk.Button(
            control_frame, text="Export Excel", command=lambda: self.export_data("excel")
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

        ttk.Label(info_frame, text="Trade Statistics", style="Subtitle.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5)
        )

        self.summary_text = scrolledtext.ScrolledText(
            summary_frame, width=80, height=20, font=(self.mono_font[0], 10)
        )
        self.summary_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def create_markets_tab(self):
        """Create market analysis tab"""
        markets_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(markets_frame, text="Market Analysis")

        markets_frame.columnconfigure(1, weight=1)
        markets_frame.rowconfigure(1, weight=1)

        # Market selection header and search
        header_frame = ttk.Frame(markets_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(header_frame, text="Select Market:", style="Subtitle.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )

        ttk.Label(header_frame, text="Search:").grid(row=0, column=1, sticky=tk.W, padx=(20, 5))
        self.market_search_var = tk.StringVar()
        self.market_search_var.trace_add("write", lambda *args: self._filter_market_listbox())
        market_search_entry = ttk.Entry(header_frame, textvariable=self.market_search_var, width=25)
        market_search_entry.grid(row=0, column=2, sticky=tk.W, padx=5)

        # Market listbox with scrollbar
        listbox_frame = ttk.Frame(markets_frame)
        listbox_frame.grid(
            row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10)
        )

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.market_listbox = tk.Listbox(
            listbox_frame, yscrollcommand=scrollbar.set, height=15, font=(self.default_font[0], 10)
        )
        self.market_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.market_listbox.yview)

        # Market action buttons
        button_frame = ttk.Frame(markets_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Button(button_frame, text="Show Market Summary", command=self.show_market_summary).grid(
            row=0, column=0, padx=5
        )

        ttk.Button(
            button_frame, text="Simple Chart", command=lambda: self.generate_market_chart("simple")
        ).grid(row=0, column=1, padx=5)

        ttk.Button(
            button_frame, text="Pro Chart", command=lambda: self.generate_market_chart("pro")
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            button_frame,
            text="Enhanced Chart",
            command=lambda: self.generate_market_chart("enhanced"),
        ).grid(row=0, column=3, padx=5)

        # Market summary display
        ttk.Label(markets_frame, text="Market Details:", style="Subtitle.TLabel").grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 5)
        )

        self.market_details_text = scrolledtext.ScrolledText(
            markets_frame, width=80, height=10, font=(self.mono_font[0], 10)
        )
        self.market_details_text.grid(
            row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S)
        )

    def create_trades_tab(self):
        """Create trade browser tab for viewing individual trades"""
        trades_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(trades_frame, text="Trade Browser")

        trades_frame.columnconfigure(0, weight=1)
        trades_frame.rowconfigure(1, weight=1)

        # Controls row
        controls_frame = ttk.Frame(trades_frame)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(controls_frame, text="Trade Browser", style="Subtitle.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )

        self.trades_count_label = ttk.Label(controls_frame, text="", style="Info.TLabel")
        self.trades_count_label.grid(row=0, column=1, sticky=tk.W, padx=20)

        # Sort controls
        ttk.Label(controls_frame, text="Sort by:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        self.sort_var = tk.StringVar(value="timestamp")
        sort_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.sort_var,
            values=["timestamp", "pnl", "cost", "market"],
            state="readonly",
            width=12,
        )
        sort_combo.grid(row=0, column=3, padx=5)

        self.sort_desc_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls_frame, text="Descending", variable=self.sort_desc_var).grid(
            row=0, column=4, padx=5
        )

        ttk.Button(controls_frame, text="Refresh", command=self.refresh_trades_browser).grid(
            row=0, column=5, padx=5
        )

        # Treeview for trade data
        tree_frame = ttk.Frame(trades_frame)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = (
            "timestamp",
            "market",
            "type",
            "side",
            "price",
            "shares",
            "cost",
            "pnl",
            "source",
            "currency",
        )
        self.trades_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)

        # Column headings and widths
        col_config = {
            "timestamp": ("Timestamp", 140),
            "market": ("Market", 200),
            "type": ("Type", 80),
            "side": ("Side", 50),
            "price": ("Price", 70),
            "shares": ("Shares", 70),
            "cost": ("Cost", 80),
            "pnl": ("PnL", 80),
            "source": ("Source", 80),
            "currency": ("Currency", 60),
        }
        for col, (heading, width) in col_config.items():
            self.trades_tree.heading(col, text=heading)
            self.trades_tree.column(col, width=width, minwidth=40)

        # Scrollbars
        tree_yscroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.trades_tree.yview)
        tree_xscroll = ttk.Scrollbar(
            tree_frame, orient=tk.HORIZONTAL, command=self.trades_tree.xview
        )
        self.trades_tree.configure(yscrollcommand=tree_yscroll.set, xscrollcommand=tree_xscroll.set)

        self.trades_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_yscroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_xscroll.grid(row=1, column=0, sticky=(tk.W, tk.E))

    def create_filters_tab(self):
        """Create filters tab"""
        filters_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(filters_frame, text="Filters")

        # Use a canvas with scrollbar for the filters content
        filters_canvas = tk.Canvas(filters_frame)
        filters_scrollbar = ttk.Scrollbar(
            filters_frame, orient=tk.VERTICAL, command=filters_canvas.yview
        )
        filters_content = ttk.Frame(filters_canvas)

        filters_content.bind(
            "<Configure>",
            lambda e: filters_canvas.configure(scrollregion=filters_canvas.bbox("all")),
        )
        filters_canvas.create_window((0, 0), window=filters_content, anchor="nw")
        filters_canvas.configure(yscrollcommand=filters_scrollbar.set)

        filters_frame.columnconfigure(0, weight=1)
        filters_frame.rowconfigure(0, weight=1)
        filters_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        filters_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Date filters
        date_frame = ttk.LabelFrame(filters_content, text="Date Range", padding="10")
        date_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(date_frame, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W)
        self.start_date_entry = ttk.Entry(date_frame, width=20)
        self.start_date_entry.grid(row=0, column=1, padx=5, pady=2)
        # Bind Enter key to apply filters
        self.start_date_entry.bind("<Return>", lambda e: self.apply_filters())

        ttk.Label(date_frame, text="End Date (YYYY-MM-DD):").grid(row=1, column=0, sticky=tk.W)
        self.end_date_entry = ttk.Entry(date_frame, width=20)
        self.end_date_entry.grid(row=1, column=1, padx=5, pady=2)
        self.end_date_entry.bind("<Return>", lambda e: self.apply_filters())

        # Format hint label
        ttk.Label(date_frame, text="(e.g., 2024-01-15)", style="Info.TLabel").grid(
            row=0, column=2, sticky=tk.W, padx=5
        )

        # Trade type filters
        type_frame = ttk.LabelFrame(filters_content, text="Trade Type", padding="10")
        type_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.buy_var = tk.BooleanVar(value=True)
        self.sell_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(type_frame, text="Buy", variable=self.buy_var).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 15)
        )
        ttk.Checkbutton(type_frame, text="Sell", variable=self.sell_var).grid(
            row=0, column=1, sticky=tk.W
        )

        # Side filters
        side_frame = ttk.LabelFrame(filters_content, text="Side", padding="10")
        side_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.yes_var = tk.BooleanVar(value=True)
        self.no_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(side_frame, text="YES", variable=self.yes_var).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 15)
        )
        ttk.Checkbutton(side_frame, text="NO", variable=self.no_var).grid(
            row=0, column=1, sticky=tk.W
        )

        # PnL filters
        pnl_frame = ttk.LabelFrame(filters_content, text="PnL Range", padding="10")
        pnl_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(pnl_frame, text="Minimum PnL:").grid(row=0, column=0, sticky=tk.W)
        self.min_pnl_entry = ttk.Entry(pnl_frame, width=20)
        self.min_pnl_entry.grid(row=0, column=1, padx=5, pady=2)
        self.min_pnl_entry.bind("<Return>", lambda e: self.apply_filters())

        ttk.Label(pnl_frame, text="Maximum PnL:").grid(row=1, column=0, sticky=tk.W)
        self.max_pnl_entry = ttk.Entry(pnl_frame, width=20)
        self.max_pnl_entry.grid(row=1, column=1, padx=5, pady=2)
        self.max_pnl_entry.bind("<Return>", lambda e: self.apply_filters())

        # Format hint label
        ttk.Label(pnl_frame, text="(e.g., -100.50, 500)", style="Info.TLabel").grid(
            row=0, column=2, sticky=tk.W, padx=5
        )

        # Filter buttons
        button_frame = ttk.Frame(filters_content)
        button_frame.grid(row=4, column=0, sticky=tk.W, pady=10)

        ttk.Button(button_frame, text="Apply Filters", command=self.apply_filters).grid(
            row=0, column=0, padx=5
        )

        ttk.Button(button_frame, text="Clear Filters", command=self.clear_filters).grid(
            row=0, column=1, padx=5
        )

        # Filter status
        self.filter_status_label = ttk.Label(
            filters_content, text="No filters applied", style="Info.TLabel"
        )
        self.filter_status_label.grid(row=5, column=0, sticky=tk.W)

    def create_portfolio_tab(self):
        """Create portfolio analysis tab with positions, concentration, and drawdown"""
        portfolio_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(portfolio_frame, text="Portfolio")

        portfolio_frame.columnconfigure(0, weight=1)
        portfolio_frame.rowconfigure(1, weight=1)

        # Buttons row
        buttons_frame = ttk.Frame(portfolio_frame)
        buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(buttons_frame, text="Open Positions", command=self.show_open_positions).grid(
            row=0, column=0, padx=5
        )

        ttk.Button(
            buttons_frame, text="Concentration Risk", command=self.show_concentration_risk
        ).grid(row=0, column=1, padx=5)

        ttk.Button(
            buttons_frame, text="Drawdown Analysis", command=self.show_drawdown_analysis
        ).grid(row=0, column=2, padx=5)

        # Display area
        self.portfolio_text = scrolledtext.ScrolledText(
            portfolio_frame, width=80, height=25, font=(self.mono_font[0], 10)
        )
        self.portfolio_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def create_tax_tab(self):
        """Create tax reporting tab"""
        tax_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tax_frame, text="Tax Report")

        tax_frame.columnconfigure(0, weight=1)
        tax_frame.rowconfigure(2, weight=1)

        # Controls
        controls_frame = ttk.LabelFrame(tax_frame, text="Tax Report Settings", padding="10")
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(controls_frame, text="Tax Year:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.tax_year_var = tk.StringVar(value=str(datetime.now().year - 1))
        tax_year_entry = ttk.Entry(controls_frame, textvariable=self.tax_year_var, width=8)
        tax_year_entry.grid(row=0, column=1, padx=5)

        ttk.Label(controls_frame, text="Cost Basis Method:").grid(
            row=0, column=2, sticky=tk.W, padx=(20, 5)
        )
        self.cost_basis_var = tk.StringVar(value="fifo")
        cost_basis_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.cost_basis_var,
            values=["fifo", "lifo", "average"],
            state="readonly",
            width=10,
        )
        cost_basis_combo.grid(row=0, column=3, padx=5)

        ttk.Button(
            controls_frame, text="Generate Tax Report", command=self.generate_tax_report
        ).grid(row=0, column=4, padx=15)

        # Method descriptions
        method_text = (
            "FIFO: First-In, First-Out (most common)  |  "
            "LIFO: Last-In, First-Out  |  "
            "Average: Average cost basis"
        )
        ttk.Label(controls_frame, text=method_text, style="Info.TLabel").grid(
            row=1, column=0, columnspan=5, sticky=tk.W, pady=(5, 0)
        )

        # Results display
        self.tax_text = scrolledtext.ScrolledText(
            tax_frame, width=80, height=25, font=(self.mono_font[0], 10)
        )
        self.tax_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def create_charts_tab(self):
        """Create charts tab"""
        charts_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(charts_frame, text="Charts")

        charts_frame.columnconfigure(0, weight=1)
        charts_frame.columnconfigure(1, weight=1)

        ttk.Label(charts_frame, text="Chart Generation", style="Subtitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10)
        )

        # Global charts section
        global_frame = ttk.LabelFrame(charts_frame, text="Global Charts", padding="10")
        global_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 5), pady=(0, 10))

        ttk.Label(
            global_frame,
            text="Multi-market overview dashboard\nshowing cumulative PnL across\nall loaded markets.",
            justify=tk.LEFT,
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        ttk.Button(global_frame, text="Generate Dashboard", command=self.generate_dashboard).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )

        # Per-market charts section
        market_frame = ttk.LabelFrame(charts_frame, text="Market-Specific Charts", padding="10")
        market_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N), padx=(5, 0), pady=(0, 10))

        chart_descriptions = (
            "Simple Chart\n"
            "  Basic matplotlib PNG with price history\n"
            "  and net cash invested over time.\n\n"
            "Pro Chart\n"
            "  Interactive Plotly HTML dashboard\n"
            "  with advanced multi-metric display.\n\n"
            "Enhanced Chart\n"
            "  Battlefield-style Plotly visualization\n"
            "  with P&L tracking and risk panels."
        )
        ttk.Label(market_frame, text=chart_descriptions, justify=tk.LEFT).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 10)
        )

        ttk.Label(
            market_frame,
            text="Select a market in the Market Analysis\ntab, then use the chart buttons there.",
            style="Info.TLabel",
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky=tk.W, pady=5)

    def load_file(self):
        """Load trades from a file"""
        file_path = filedialog.askopenfilename(
            title="Select Trades File",
            filetypes=[
                ("All Supported", "*.json *.csv *.xlsx"),
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        try:
            self.all_trades = load_trades(file_path)
            self.filtered_trades = self.all_trades.copy()
            self.current_file_path = file_path

            # Update status
            filename = Path(file_path).name
            self.status_label.config(text=f"Loaded: {filename} ({len(self.all_trades)} trades)")

            # Update displays
            self.update_markets_list()
            self.update_summary_display()
            self.refresh_trades_browser()

            messagebox.showinfo(
                "Success", f"Successfully loaded {len(self.all_trades)} trades from {filename}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")

    def load_from_api(self):
        """Load trades from API using API key (runs in background thread)"""
        # Atomic check-and-set to prevent concurrent fetches
        with self._fetch_lock:
            if self._fetch_in_progress:
                messagebox.showinfo("Busy", "A fetch is already in progress. Please wait.")
                return
            self._fetch_in_progress = True

        try:
            self._start_api_fetch()
        except Exception as e:
            self._fetch_in_progress = False
            self._set_api_controls_enabled(True)
            messagebox.showerror("Error", f"Failed to start API fetch:\n{str(e)}")

    def _start_api_fetch(self):
        """Prepare and launch the background API fetch thread."""
        from prediction_analyzer.utils.auth import detect_provider_from_key

        api_key_raw = self.api_key_entry.get().strip()
        provider_name = self.provider_var.get()

        api_key = get_api_key(
            api_key_raw, provider=provider_name if provider_name != "auto" else "limitless"
        )

        if not api_key:
            self._fetch_in_progress = False
            messagebox.showwarning(
                "Missing API Key",
                "Please enter your API key or wallet address.\n\n"
                "Supported formats:\n"
                "  Limitless: lmts_...\n"
                "  Polymarket: 0x... (wallet address)\n"
                "  Kalshi: kalshi_<KEY_ID>:<PEM_PATH>\n"
                "  Manifold: manifold_...\n\n"
                "Or set the appropriate environment variable.",
            )
            return

        # Auto-detect provider if needed
        if provider_name == "auto":
            provider_name = detect_provider_from_key(api_key)

        # Disable buttons while fetching (flag already set inside _fetch_lock above)
        self.status_label.config(text=f"Fetching trades from {provider_name}...")
        self._set_api_controls_enabled(False)

        def _fetch_worker():
            """Background thread for API fetch"""
            try:
                if provider_name == "limitless":
                    # Legacy path
                    raw_trades = fetch_trade_history(api_key)
                    self.root.after(0, lambda: self._on_api_fetch_complete(raw_trades))
                else:
                    # Provider system
                    from prediction_analyzer.providers import ProviderRegistry
                    from prediction_analyzer.providers.pnl_calculator import compute_realized_pnl

                    provider = ProviderRegistry.get(provider_name)
                    trades = provider.fetch_trades(api_key)
                    if provider_name in ("kalshi", "manifold", "polymarket"):
                        trades = compute_realized_pnl(trades)
                    self.root.after(
                        0, lambda: self._on_provider_fetch_complete(trades, provider_name)
                    )
            except Exception as exc:
                self.root.after(0, lambda err=str(exc): self._on_api_fetch_error(err))

        thread = threading.Thread(target=_fetch_worker, daemon=True)
        thread.start()

    def _set_api_controls_enabled(self, enabled: bool):
        """Enable or disable API-related controls during fetch"""
        state = "normal" if enabled else "disabled"
        self.api_key_entry.config(state=state)

    def _on_api_fetch_complete(self, raw_trades):
        """Handle successful API fetch (called on main thread)"""
        self._fetch_in_progress = False
        self._set_api_controls_enabled(True)

        if not raw_trades:
            messagebox.showinfo("No Trades", "No trades found for this account.")
            self.status_label.config(text="No trades found")
            return

        try:
            from prediction_analyzer.trade_loader import load_trades
            import json
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
                json.dump(raw_trades, tmp)
                tmp_path = tmp.name

            try:
                self.all_trades = load_trades(tmp_path)
                self.filtered_trades = self.all_trades.copy()
                self.current_file_path = None

                self.status_label.config(text=f"Loaded from API ({len(self.all_trades)} trades)")

                self.update_markets_list()
                self.update_summary_display()
                self.refresh_trades_browser()

                messagebox.showinfo(
                    "Success", f"Successfully loaded {len(self.all_trades)} trades from API"
                )
            finally:
                import os

                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process trades:\n{str(e)}")
            self.status_label.config(text="Failed to process API data")

    def _on_provider_fetch_complete(self, trades, provider_name: str):
        """Handle successful provider fetch (called on main thread)"""
        self._fetch_in_progress = False
        self._set_api_controls_enabled(True)

        if not trades:
            messagebox.showinfo("No Trades", f"No trades found from {provider_name}.")
            self.status_label.config(text="No trades found")
            return

        self.all_trades = trades
        self.filtered_trades = self.all_trades.copy()
        self.current_file_path = None

        self.status_label.config(
            text=f"Loaded from {provider_name} ({len(self.all_trades)} trades)"
        )

        self.update_markets_list()
        self.update_summary_display()
        self.refresh_trades_browser()

        messagebox.showinfo(
            "Success", f"Successfully loaded {len(self.all_trades)} trades from {provider_name}"
        )

    def _on_api_fetch_error(self, error_msg: str):
        """Handle API fetch error (called on main thread)"""
        self._fetch_in_progress = False
        self._set_api_controls_enabled(True)
        messagebox.showerror("Error", f"Failed to load trades from API:\n{error_msg}")
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
        # Count trades per market for display
        trades_by_market = group_trades_by_market(self.filtered_trades)
        self.market_slugs = sorted(markets.keys())

        new_selection_idx = None
        for i, slug in enumerate(self.market_slugs):
            title = markets[slug]
            trade_count = len(trades_by_market.get(slug, []))
            # Show trade count next to market name
            count_suffix = f" ({trade_count} trades)"
            max_title_len = 60 - len(count_suffix)
            if len(title) > max_title_len:
                display_text = f"{title[:max_title_len]}...{count_suffix}"
            else:
                display_text = f"{title}{count_suffix}"
            self.market_listbox.insert(tk.END, display_text)

            # Check if this was the previously selected market
            if slug == selected_slug:
                new_selection_idx = i

        # Restore selection if the market still exists in filtered list
        if new_selection_idx is not None:
            self.market_listbox.selection_set(new_selection_idx)
            self.market_listbox.see(new_selection_idx)

    def _filter_market_listbox(self):
        """Filter market listbox based on search text"""
        search_text = self.market_search_var.get().strip().lower()
        if not self.filtered_trades:
            return

        self.market_listbox.delete(0, tk.END)
        self.market_listbox.selection_clear(0, tk.END)

        markets = get_unique_markets(self.filtered_trades)
        trades_by_market = group_trades_by_market(self.filtered_trades)

        # Filter and rebuild the visible slugs list
        self.market_slugs = []
        for slug in sorted(markets.keys()):
            title = markets[slug]
            if search_text and search_text not in title.lower() and search_text not in slug.lower():
                continue

            self.market_slugs.append(slug)
            trade_count = len(trades_by_market.get(slug, []))
            count_suffix = f" ({trade_count} trades)"
            max_title_len = 60 - len(count_suffix)
            if len(title) > max_title_len:
                display_text = f"{title[:max_title_len]}...{count_suffix}"
            else:
                display_text = f"{title}{count_suffix}"
            self.market_listbox.insert(tk.END, display_text)

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
            currency = summary.get("currency", "USD")
            cur_sym = "$" if currency in ("USD", "USDC") else f"{currency} "
            output.append(f"\nTotal Trades: {summary['total_trades']}")
            output.append(f"Total PnL: {cur_sym}{summary['total_pnl']:.2f}")
            output.append(f"Average PnL per Trade: {cur_sym}{summary['avg_pnl']:.2f}")
            output.append(f"\nWinning Trades: {summary['winning_trades']}")
            output.append(f"Losing Trades: {summary['losing_trades']}")
            output.append(f"Breakeven Trades: {summary.get('breakeven_trades', 0)}")
            output.append(f"Win Rate: {summary['win_rate']:.1f}%")
            output.append(f"\nTotal Invested: {cur_sym}{summary['total_invested']:.2f}")
            output.append(f"Total Returned: {cur_sym}{summary['total_returned']:.2f}")
            output.append(f"ROI: {summary['roi']:.2f}%")

            # Currency breakdown if multiple currencies present
            if summary.get("by_currency"):
                output.append("\n" + "-" * 60)
                output.append("CURRENCY BREAKDOWN")
                output.append("-" * 60)
                for currency, data in summary["by_currency"].items():
                    output.append(f"\n  {currency}:")
                    output.append(f"    Trades: {data.get('total_trades', 'N/A')}")
                    if isinstance(data.get("total_pnl"), (int, float)):
                        output.append(f"    PnL: {data['total_pnl']:.2f} {currency}")
                    if isinstance(data.get("win_rate"), (int, float)):
                        output.append(f"    Win Rate: {data['win_rate']:.1f}%")

            # Provider/source breakdown (use pre-computed by_source from summary)
            if summary.get("by_source"):
                output.append("\n" + "-" * 60)
                output.append("PROVIDER BREAKDOWN")
                output.append("-" * 60)
                for source, data in sorted(summary["by_source"].items()):
                    output.append(f"\n  {source.capitalize()}:")
                    output.append(f"    Trades: {data.get('total_trades', 0)}")
                    pnl_val = data.get("total_pnl", 0)
                    cur = data.get("currency", "USD")
                    output.append(f"    PnL: {pnl_val:.2f} {cur}")

            # Advanced metrics
            metrics = calculate_advanced_metrics(self.filtered_trades)
            output.append("\n" + "=" * 60)
            output.append("ADVANCED METRICS")
            output.append("=" * 60)
            output.append(f"\nSharpe Ratio: {metrics['sharpe_ratio']:.4f}")
            output.append(f"Sortino Ratio: {metrics['sortino_ratio']:.4f}")
            output.append(f"Profit Factor: {metrics['profit_factor']:.2f}")
            output.append(f"Expectancy: {cur_sym}{metrics['expectancy']:.4f}")
            output.append(
                f"\nMax Drawdown: {cur_sym}{metrics['max_drawdown']:.2f} ({metrics['max_drawdown_pct']:.1f}%)"
            )
            output.append(f"Max DD Duration: {metrics['max_drawdown_duration_trades']} trades")
            output.append(
                f"\nAvg Win: {cur_sym}{metrics['avg_win']:.2f}  |  Avg Loss: {cur_sym}{metrics['avg_loss']:.2f}"
            )
            output.append(
                f"Largest Win: {cur_sym}{metrics['largest_win']:.2f}  |  Largest Loss: {cur_sym}{metrics['largest_loss']:.2f}"
            )
            output.append(
                f"Max Win Streak: {metrics['max_win_streak']}  |  Max Loss Streak: {metrics['max_loss_streak']}"
            )

            output.append("\n" + "=" * 60)

            self.summary_text.insert(tk.END, "\n".join(output))

        except Exception as e:
            self.summary_text.insert(tk.END, f"Error calculating summary:\n{str(e)}")

    def refresh_trades_browser(self):
        """Populate the trade browser treeview with current filtered trades"""
        # Clear existing items
        for item in self.trades_tree.get_children():
            self.trades_tree.delete(item)

        if not self.filtered_trades:
            self.trades_count_label.config(text="No trades loaded")
            return

        # Sort trades
        sort_key = self.sort_var.get()
        reverse = self.sort_desc_var.get()

        sorted_trades = list(self.filtered_trades)
        if sort_key == "timestamp":
            sorted_trades.sort(key=lambda t: t.timestamp, reverse=reverse)
        elif sort_key == "pnl":
            sorted_trades.sort(key=lambda t: t.pnl, reverse=reverse)
        elif sort_key == "cost":
            sorted_trades.sort(key=lambda t: t.cost, reverse=reverse)
        elif sort_key == "market":
            sorted_trades.sort(key=lambda t: t.market, reverse=reverse)

        for trade in sorted_trades:
            self.trades_tree.insert(
                "",
                tk.END,
                values=(
                    trade.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    trade.market[:40] + "..." if len(trade.market) > 40 else trade.market,
                    trade.type,
                    trade.side,
                    f"{trade.price:.2f}",
                    f"{trade.shares:.4f}",
                    f"{trade.cost:.2f}",
                    f"{trade.pnl:.2f}",
                    trade.source,
                    trade.currency,
                ),
            )

        self.trades_count_label.config(text=f"{len(sorted_trades)} trades")

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
            messagebox.showinfo("No Trades", "No trades found for this market.")
            return

        try:
            summary = calculate_market_pnl_summary(market_trades)

            self.market_details_text.delete(1.0, tk.END)

            output = []
            # Determine currency from trades
            currencies = set(t.currency for t in market_trades)
            sources = set(t.source for t in market_trades)
            market_cur = next(iter(currencies)) if len(currencies) == 1 else "USD"
            mcur_sym = "$" if market_cur in ("USD", "USDC") else f"{market_cur} "

            output.append("=" * 60)
            output.append(f"MARKET: {summary['market_title']}")
            output.append("=" * 60)
            output.append(f"\nTotal Trades: {summary['total_trades']}")
            output.append(f"Total PnL: {mcur_sym}{summary['total_pnl']:.2f}")
            output.append(f"Average PnL per Trade: {mcur_sym}{summary['avg_pnl']:.2f}")
            output.append(f"\nWinning Trades: {summary['winning_trades']}")
            output.append(f"Losing Trades: {summary['losing_trades']}")
            output.append(f"Breakeven Trades: {summary.get('breakeven_trades', 0)}")
            output.append(f"Win Rate: {summary['win_rate']:.1f}%")
            output.append(f"\nTotal Invested: {mcur_sym}{summary['total_invested']:.2f}")
            output.append(f"Total Returned: {mcur_sym}{summary['total_returned']:.2f}")
            output.append(f"ROI: {summary['roi']:.2f}%")

            if summary.get("market_outcome"):
                output.append(f"\nMarket Outcome: {summary['market_outcome']}")

            output.append(f"\nCurrency: {', '.join(currencies)}")
            output.append(f"Source: {', '.join(s.capitalize() for s in sources)}")

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
            messagebox.showinfo("No Trades", "No trades found for this market.")
            return

        try:
            if chart_type == "simple":
                generate_simple_chart(market_trades, market_title)
            elif chart_type == "pro":
                generate_pro_chart(market_trades, market_title)
            elif chart_type == "enhanced":
                generate_enhanced_chart(market_trades, market_title)

            messagebox.showinfo(
                "Success", f"{chart_type.capitalize()} chart generated successfully!"
            )

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

    def _get_currency_symbol(self, trades=None) -> str:
        """Derive currency symbol from trades. Uses '$' for USD/USDC, else the currency code."""
        trades = trades or self.filtered_trades
        if not trades:
            return "$"
        currencies = set(t.currency for t in trades)
        if len(currencies) == 1:
            cur = next(iter(currencies))
            return "$" if cur in ("USD", "USDC") else f"{cur} "
        return "$"

    def show_open_positions(self):
        """Show open positions in the portfolio tab"""
        if not self.filtered_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        self.portfolio_text.delete(1.0, tk.END)

        try:
            positions = calculate_open_positions(self.filtered_trades)
            cs = self._get_currency_symbol()

            output = []
            output.append("=" * 60)
            output.append("OPEN POSITIONS")
            output.append("=" * 60)

            if not positions:
                output.append("\nNo open positions found.")
            else:
                for pos in positions:
                    output.append(f"\n  Market: {pos.get('market', 'N/A')}")
                    output.append(f"  Side: {pos.get('side', 'N/A')}")
                    output.append(f"  Net Shares: {pos.get('net_shares', 0):.4f}")
                    output.append(f"  Avg Entry Price: {pos.get('avg_entry_price', 0):.2f}")
                    if pos.get("current_price") is not None:
                        output.append(f"  Current Price: {pos['current_price']:.2f}")
                    if pos.get("unrealized_pnl") is not None:
                        output.append(f"  Unrealized PnL: {cs}{pos['unrealized_pnl']:.2f}")
                    output.append(f"  Cost Basis: {cs}{pos.get('cost_basis', 0):.2f}")
                    output.append("  " + "-" * 40)

            output.append("\n" + "=" * 60)
            self.portfolio_text.insert(tk.END, "\n".join(output))

        except Exception as e:
            self.portfolio_text.insert(tk.END, f"Error calculating positions:\n{str(e)}")

    def show_concentration_risk(self):
        """Show concentration risk analysis"""
        if not self.filtered_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        self.portfolio_text.delete(1.0, tk.END)

        try:
            risk = calculate_concentration_risk(self.filtered_trades)
            cs = self._get_currency_symbol()

            output = []
            output.append("=" * 60)
            output.append("CONCENTRATION RISK ANALYSIS")
            output.append("=" * 60)
            output.append(f"\nTotal Markets: {risk.get('total_markets', 0)}")
            output.append(f"Total Exposure: {cs}{risk.get('total_exposure', 0):.2f}")
            output.append(f"Herfindahl Index (HHI): {risk.get('herfindahl_index', 0):.4f}")
            output.append(f"Top 3 Concentration: {risk.get('top_3_concentration_pct', 0):.1f}%")

            # Diversification assessment (HHI is on 0-10000 scale)
            hhi = risk.get("herfindahl_index", 0)
            if hhi < 1500:
                assessment = "Well diversified"
            elif hhi < 2500:
                assessment = "Moderately concentrated"
            else:
                assessment = "Highly concentrated"
            output.append(f"Assessment: {assessment}")

            markets = risk.get("markets", [])
            if markets:
                output.append("\n" + "-" * 60)
                output.append("PER-MARKET EXPOSURE")
                output.append("-" * 60)
                for m in markets[:20]:  # Show top 20
                    name = m.get("market", "N/A")
                    if len(name) > 35:
                        name = name[:35] + "..."
                    exposure = m.get("exposure", 0)
                    pct = m.get("pct_of_total", 0)
                    trades_count = m.get("trade_count", 0)
                    output.append(
                        f"  {name:<38} {cs}{exposure:>8.2f} ({pct:>5.1f}%) [{trades_count} trades]"
                    )

            output.append("\n" + "=" * 60)
            self.portfolio_text.insert(tk.END, "\n".join(output))

        except Exception as e:
            self.portfolio_text.insert(tk.END, f"Error calculating concentration:\n{str(e)}")

    def show_drawdown_analysis(self):
        """Show detailed drawdown analysis"""
        if not self.filtered_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        self.portfolio_text.delete(1.0, tk.END)

        try:
            dd = analyze_drawdowns(self.filtered_trades)
            cs = self._get_currency_symbol()

            output = []
            output.append("=" * 60)
            output.append("DRAWDOWN ANALYSIS")
            output.append("=" * 60)
            output.append(
                f"\nMax Drawdown: {cs}{dd.get('max_drawdown_amount', 0):.2f} ({dd.get('max_drawdown_pct', 0):.1f}%)"
            )
            output.append(f"Peak Value: {cs}{dd.get('peak_value', 0):.2f}")
            output.append(f"Trough Value: {cs}{dd.get('trough_value', 0):.2f}")

            if dd.get("drawdown_start_date"):
                output.append(f"\nDrawdown Start: {dd['drawdown_start_date']}")
            if dd.get("drawdown_end_date"):
                output.append(f"Drawdown End: {dd['drawdown_end_date']}")
            if dd.get("recovery_date"):
                output.append(f"Recovery Date: {dd['recovery_date']}")
            if dd.get("drawdown_duration_days") is not None:
                output.append(f"Drawdown Duration: {dd['drawdown_duration_days']} days")
            if dd.get("recovery_duration_days") is not None:
                output.append(f"Recovery Duration: {dd['recovery_duration_days']} days")

            output.append(f"\nCurrently In Drawdown: {'Yes' if dd.get('is_in_drawdown') else 'No'}")
            if dd.get("is_in_drawdown") and dd.get("current_drawdown") is not None:
                output.append(f"Current Drawdown: {cs}{dd['current_drawdown']:.2f}")

            periods = dd.get("drawdown_periods", [])
            if periods:
                output.append("\n" + "-" * 60)
                output.append(f"DRAWDOWN PERIODS ({len(periods)} total)")
                output.append("-" * 60)
                for i, period in enumerate(periods[:10], 1):  # Show top 10
                    output.append(f"\n  Period {i}:")
                    output.append(
                        f"    Amount: {cs}{period.get('amount', 0):.2f} ({period.get('pct', 0):.1f}%)"
                    )
                    if period.get("start"):
                        output.append(f"    Start: {period['start']}")
                    if period.get("end"):
                        output.append(f"    End: {period['end']}")
                    if period.get("duration_days") is not None:
                        output.append(f"    Duration: {period['duration_days']} days")

            output.append("\n" + "=" * 60)
            self.portfolio_text.insert(tk.END, "\n".join(output))

        except Exception as e:
            self.portfolio_text.insert(tk.END, f"Error analyzing drawdowns:\n{str(e)}")

    def generate_tax_report(self):
        """Generate capital gains tax report"""
        if not self.all_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        # Validate tax year
        tax_year_str = self.tax_year_var.get().strip()
        try:
            tax_year = int(tax_year_str)
            if tax_year < 2000 or tax_year > 2100:
                raise ValueError("Year out of range")
        except ValueError:
            messagebox.showerror(
                "Invalid Year",
                f"'{tax_year_str}' is not a valid tax year.\nPlease enter a 4-digit year (e.g., 2025).",
            )
            return

        cost_basis = self.cost_basis_var.get()

        self.tax_text.delete(1.0, tk.END)

        try:
            report = calculate_capital_gains(self.all_trades, tax_year, cost_basis)
            cs = self._get_currency_symbol(self.all_trades)

            output = []
            output.append("=" * 60)
            output.append(f"TAX REPORT - {tax_year}")
            output.append(f"Cost Basis Method: {cost_basis.upper()}")
            output.append("=" * 60)

            output.append(f"\nNote: Tax report uses all trades regardless of active filters.")
            output.append(f"Total trades in scope: {report.get('total_trades_in_scope', 0)}")
            output.append(f"\nShort-Term Gains: {cs}{report.get('short_term_gains', 0):.2f}")
            output.append(f"Short-Term Losses: {cs}{report.get('short_term_losses', 0):.2f}")
            output.append(f"Long-Term Gains: {cs}{report.get('long_term_gains', 0):.2f}")
            output.append(f"Long-Term Losses: {cs}{report.get('long_term_losses', 0):.2f}")
            output.append(f"\nNet Gain/Loss: {cs}{report.get('net_gain_loss', 0):.2f}")
            output.append(f"Total Fees: {cs}{report.get('total_fees', 0):.2f}")
            output.append(f"Transaction Count: {report.get('transaction_count', 0)}")

            if report.get("wash_sales"):
                output.append(f"\nPotential Wash Sales: {len(report['wash_sales'])}")
                if report.get("wash_sale_disallowed_loss") is not None:
                    output.append(
                        f"Total Disallowed Loss: {cs}{report['wash_sale_disallowed_loss']:.2f}"
                    )
                for ws in report["wash_sales"][:10]:
                    market = ws.get("market", "N/A")
                    if len(market) > 30:
                        market = market[:30] + "..."
                    output.append(
                        f"  {market}: sold {ws.get('date_sold', '?')}, "
                        f"repurchased {ws.get('date_repurchased', '?')}, "
                        f"disallowed {cs}{ws.get('disallowed_loss', 0):.2f}"
                    )

            transactions = report.get("transactions", [])
            if transactions:
                output.append("\n" + "-" * 60)
                output.append("TRANSACTIONS")
                output.append("-" * 60)
                for txn in transactions[:50]:  # Show first 50
                    term = "ST" if txn.get("holding_period") == "short_term" else "LT"
                    market = txn.get("market", "N/A")
                    if len(market) > 30:
                        market = market[:30] + "..."
                    gain = txn.get("gain_loss", 0)
                    output.append(f"  [{term}] {market:<33} {cs}{gain:>10.2f}")

            output.append("\n" + "=" * 60)
            output.append("DISCLAIMER: This is an estimate only. Consult a tax")
            output.append("professional for actual tax filing requirements.")
            output.append("=" * 60)

            self.tax_text.insert(tk.END, "\n".join(output))

        except Exception as e:
            self.tax_text.insert(tk.END, f"Error generating tax report:\n{str(e)}")

    def show_compare_periods_dialog(self):
        """Show dialog for comparing two time periods"""
        if not self.all_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Compare Periods")
        dialog.geometry("450x350")
        dialog.transient(self.root)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Compare Trading Performance", style="Subtitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15)
        )

        # Period 1
        p1_frame = ttk.LabelFrame(main_frame, text="Period 1", padding="10")
        p1_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(p1_frame, text="Start:").grid(row=0, column=0, sticky=tk.W)
        p1_start = ttk.Entry(p1_frame, width=15)
        p1_start.grid(row=0, column=1, padx=5)
        ttk.Label(p1_frame, text="End:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        p1_end = ttk.Entry(p1_frame, width=15)
        p1_end.grid(row=0, column=3, padx=5)

        # Period 2
        p2_frame = ttk.LabelFrame(main_frame, text="Period 2", padding="10")
        p2_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(p2_frame, text="Start:").grid(row=0, column=0, sticky=tk.W)
        p2_start = ttk.Entry(p2_frame, width=15)
        p2_start.grid(row=0, column=1, padx=5)
        ttk.Label(p2_frame, text="End:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        p2_end = ttk.Entry(p2_frame, width=15)
        p2_end.grid(row=0, column=3, padx=5)

        ttk.Label(main_frame, text="Date format: YYYY-MM-DD", style="Info.TLabel").grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(0, 10)
        )

        def do_compare():
            dates = [
                p1_start.get().strip(),
                p1_end.get().strip(),
                p2_start.get().strip(),
                p2_end.get().strip(),
            ]
            for d in dates:
                if not d:
                    messagebox.showerror(
                        "Missing Date", "All four date fields are required.", parent=dialog
                    )
                    return
                if not self._validate_date_format(d):
                    messagebox.showerror(
                        "Invalid Date",
                        f"'{d}' is not a valid date.\nUse YYYY-MM-DD format.",
                        parent=dialog,
                    )
                    return

            try:
                result = compare_periods(self.all_trades, dates[0], dates[1], dates[2], dates[3])
                dialog.destroy()
                self._show_comparison_result(result)
            except Exception as e:
                messagebox.showerror("Error", f"Comparison failed:\n{str(e)}", parent=dialog)

        ttk.Button(main_frame, text="Compare", command=do_compare).grid(
            row=4, column=0, columnspan=2, pady=10
        )

    def _show_comparison_result(self, result):
        """Display period comparison results in the summary tab"""
        self.summary_text.delete(1.0, tk.END)
        cs = self._get_currency_symbol()

        output = []
        output.append("=" * 60)
        output.append("PERIOD COMPARISON")
        output.append("=" * 60)

        for label, key in [("PERIOD 1", "period_1"), ("PERIOD 2", "period_2")]:
            period = result.get(key, {})
            output.append(
                f"\n{label}: {period.get('start_date', '?')} to {period.get('end_date', '?')}"
            )
            output.append(f"  Trades: {period.get('trades', 0)}")
            output.append(f"  PnL: {cs}{period.get('pnl', 0):.2f}")
            output.append(f"  Win Rate: {period.get('win_rate', 0):.1f}%")
            output.append(f"  Avg PnL: {cs}{period.get('avg_pnl', 0):.2f}")
            if period.get("sharpe") is not None:
                output.append(f"  Sharpe Ratio: {period['sharpe']:.4f}")

        changes = result.get("changes", {})
        if changes:
            output.append("\n" + "-" * 60)
            output.append("CHANGES (Period 1 -> Period 2)")
            output.append("-" * 60)
            if changes.get("pnl_change_pct") is not None:
                output.append(f"  PnL Change: {changes['pnl_change_pct']:+.1f}%")
            if changes.get("win_rate_change") is not None:
                output.append(f"  Win Rate Change: {changes['win_rate_change']:+.1f} pp")
            if changes.get("sharpe_change") is not None:
                output.append(f"  Sharpe Change: {changes['sharpe_change']:+.4f}")
            if changes.get("avg_pnl_change_pct") is not None:
                output.append(f"  Avg PnL Change: {changes['avg_pnl_change_pct']:+.1f}%")

        output.append("\n" + "=" * 60)
        self.summary_text.insert(tk.END, "\n".join(output))
        self.notebook.select(0)

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
                "Please use YYYY-MM-DD format (e.g., 2024-01-15).",
            )
            self.start_date_entry.focus_set()
            return

        if end_date and not self._validate_date_format(end_date):
            messagebox.showerror(
                "Invalid Date Format",
                f"End date '{end_date}' is not valid.\n\n"
                "Please use YYYY-MM-DD format (e.g., 2024-01-15).",
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
                    "Please ensure start date is before or equal to end date.",
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
                "Please enter a numeric value (e.g., -100.50 or 500).",
            )
            self.min_pnl_entry.focus_set()
            return

        if max_pnl_str and not self._validate_numeric(max_pnl_str):
            messagebox.showerror(
                "Invalid PnL Value",
                f"Maximum PnL '{max_pnl_str}' is not a valid number.\n\n"
                "Please enter a numeric value (e.g., -100.50 or 500).",
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
                    "Please ensure minimum is less than or equal to maximum.",
                )
                self.min_pnl_entry.focus_set()
                return

        try:
            filtered = self.all_trades.copy()
            filters_applied = []

            # Date filters
            if start_date or end_date:
                filtered = filter_by_date(
                    filtered, start_date if start_date else None, end_date if end_date else None
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

            # Side filters
            sides = []
            if self.yes_var.get():
                sides.append("YES")
            if self.no_var.get():
                sides.append("NO")

            if not sides:
                filtered = []
                filters_applied.append("Side: None (no trades match)")
            elif len(sides) < 2:
                filtered = filter_by_side(filtered, sides)
                filters_applied.append(f"Side: {', '.join(sides)}")

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
            self.refresh_trades_browser()

            # Update status
            if filters_applied:
                status_text = (
                    f"Filters applied: {', '.join(filters_applied)} ({len(filtered)} trades)"
                )
            else:
                status_text = "No filters applied"

            self.filter_status_label.config(text=status_text)

            messagebox.showinfo(
                "Filters Applied",
                f"Filtered to {len(filtered)} trades from {len(self.all_trades)} total",
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
        self.yes_var.set(True)
        self.no_var.set(True)

        # Reset filtered trades only if we have data
        if self.all_trades:
            self.filtered_trades = self.all_trades.copy()

            # Update displays
            self.update_markets_list()
            self.update_summary_display()
            self.refresh_trades_browser()

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
        """Export data to CSV, Excel, or JSON"""
        if not self.filtered_trades:
            messagebox.showwarning("No Data", "Please load a trades file first.")
            return

        format_config = {
            "csv": ("Export to CSV", ".csv", "csv", [("CSV files", "*.csv"), ("All files", "*.*")]),
            "excel": (
                "Export to Excel",
                ".xlsx",
                "xlsx",
                [("Excel files", "*.xlsx"), ("All files", "*.*")],
            ),
            "json": (
                "Export to JSON",
                ".json",
                "json",
                [("JSON files", "*.json"), ("All files", "*.*")],
            ),
        }

        if format_type not in format_config:
            return

        title, ext, file_ext, filetypes = format_config[format_type]
        default_filename = self._generate_export_filename(file_ext)

        file_path = filedialog.asksaveasfilename(
            title=title, defaultextension=ext, initialfile=default_filename, filetypes=filetypes
        )

        if not file_path:
            return

        try:
            if format_type == "csv":
                export_to_csv(self.filtered_trades, file_path)
            elif format_type == "excel":
                export_to_excel(self.filtered_trades, file_path)
            elif format_type == "json":
                export_to_json(self.filtered_trades, file_path)

            messagebox.showinfo(
                "Success", f"Exported {len(self.filtered_trades)} trades to:\n{file_path}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")

    def show_about(self):
        """Show about dialog"""
        about_text = (
            "Prediction Market Trade Analyzer\n\n"
            "A comprehensive tool for analyzing prediction market trades\n"
            "across multiple providers and currencies.\n\n"
            "Supported Providers:\n"
            "- Limitless Exchange (USDC)\n"
            "- Polymarket (USDC)\n"
            "- Kalshi (USD)\n"
            "- Manifold Markets (MANA)\n\n"
            "Features:\n"
            "- Load trades from JSON, CSV, Excel, or API\n"
            "- Global and per-market PnL analysis\n"
            "- Advanced metrics (Sharpe, Sortino, drawdown)\n"
            "- Portfolio analysis and concentration risk\n"
            "- Tax reporting (FIFO/LIFO/Average)\n"
            "- Period comparison\n"
            "- Filter by date, type, side, and PnL\n"
            "- Multiple chart types (Simple, Pro, Enhanced)\n"
            "- Export to CSV, Excel, and JSON\n\n"
            "License: AGPL-3.0"
        )
        messagebox.showinfo("About", about_text)


def main():
    """Main entry point for GUI application"""
    root = tk.Tk()
    PredictionAnalyzerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
