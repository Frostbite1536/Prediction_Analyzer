# prediction_mcp/tools/__init__.py
"""
MCP tool modules.

Each module registers tools with the server via register_tools(server).
Tool modules are organized by feature area:
  - data_tools: load_trades, fetch_trades, list_markets
  - analysis_tools: global_summary, market_summary, advanced_metrics
  - filter_tools: filter_trades (composite filter)
  - chart_tools: generate_chart (all chart types)
  - portfolio_tools: open_positions, unrealized_pnl
  - export_tools: export data in various formats
  - tax_tools: capital_gains, cost_basis
"""
