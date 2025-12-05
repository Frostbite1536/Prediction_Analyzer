# prediction_analyzer/reporting/report_data.py
"""
Data export functionality (CSV, Excel, JSON)
"""
import pandas as pd
from typing import List
from ..trade_loader import Trade

def export_to_csv(trades: List[Trade], filename: str = "trades_export.csv"):
    """
    Export trades to CSV file

    Args:
        trades: List of Trade objects
        filename: Output CSV filename
    """
    if not trades:
        print("⚠️ No trades to export.")
        return False

    try:
        df = pd.DataFrame([vars(t) for t in trades])
        df.to_csv(filename, index=False)
        print(f"✅ Trades exported to: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error exporting to CSV: {e}")
        return False

def export_to_excel(trades: List[Trade], filename: str = "trades_export.xlsx"):
    """
    Export trades to Excel file with multiple sheets

    Args:
        trades: List of Trade objects
        filename: Output Excel filename
    """
    if not trades:
        print("⚠️ No trades to export.")
        return False

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

        print(f"✅ Trades exported to: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error exporting to Excel: {e}")
        return False

def export_to_json(trades: List[Trade], filename: str = "trades_export.json"):
    """
    Export trades to JSON file

    Args:
        trades: List of Trade objects
        filename: Output JSON filename
    """
    import json

    if not trades:
        print("⚠️ No trades to export.")
        return False

    try:
        trades_dict = [vars(t) for t in trades]
        # Convert datetime to string
        for t in trades_dict:
            if hasattr(t['timestamp'], 'isoformat'):
                t['timestamp'] = t['timestamp'].isoformat()

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(trades_dict, f, indent=2)

        print(f"✅ Trades exported to: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error exporting to JSON: {e}")
        return False
