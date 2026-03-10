# prediction_analyzer/reporting/report_data.py
"""
Data export functionality (CSV, Excel, JSON)
"""
import logging
import pandas as pd
from typing import List
from ..trade_loader import Trade
from ..exceptions import NoTradesError, ExportError

logger = logging.getLogger(__name__)

def export_to_csv(trades: List[Trade], filename: str = "trades_export.csv"):
    """
    Export trades to CSV file

    Args:
        trades: List of Trade objects
        filename: Output CSV filename
    """
    if not trades:
        raise NoTradesError("No trades to export.")

    try:
        df = pd.DataFrame([vars(t) for t in trades])
        df.to_csv(filename, index=False)
        logger.info("Trades exported to: %s", filename)
        return True
    except Exception as e:
        logger.error("Error exporting to CSV: %s", e)
        raise ExportError(f"Error exporting to CSV {filename}: {e}") from e

def export_to_excel(trades: List[Trade], filename: str = "trades_export.xlsx"):
    """
    Export trades to Excel file with multiple sheets

    Args:
        trades: List of Trade objects
        filename: Output Excel filename
    """
    if not trades:
        raise NoTradesError("No trades to export.")

    try:
        df = pd.DataFrame([vars(t) for t in trades])

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Main trades sheet
            df.to_excel(writer, sheet_name='All Trades', index=False)

            # Summary by market
            summary = df.groupby('market').agg({
                'cost': 'sum',
                'pnl': 'sum',
                'market_slug': 'count'
            }).rename(columns={'market_slug': 'trade_count'})
            summary.to_excel(writer, sheet_name='Market Summary')

        logger.info("Trades exported to: %s", filename)
        return True
    except Exception as e:
        logger.error("Error exporting to Excel: %s", e)
        raise ExportError(f"Error exporting to Excel {filename}: {e}") from e

def export_to_json(trades: List[Trade], filename: str = "trades_export.json"):
    """
    Export trades to JSON file

    Args:
        trades: List of Trade objects
        filename: Output JSON filename
    """
    import json

    if not trades:
        raise NoTradesError("No trades to export.")

    try:
        trades_dict = [vars(t) for t in trades]
        # Convert datetime to string
        for t in trades_dict:
            if hasattr(t['timestamp'], 'isoformat'):
                t['timestamp'] = t['timestamp'].isoformat()

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(trades_dict, f, indent=2)

        logger.info("Trades exported to: %s", filename)
        return True
    except Exception as e:
        logger.error("Error exporting to JSON: %s", e)
        raise ExportError(f"Error exporting to JSON {filename}: {e}") from e
