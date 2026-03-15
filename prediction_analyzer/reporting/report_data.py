# prediction_analyzer/reporting/report_data.py
"""Data export functionality (CSV, Excel, JSON)."""

import json
import logging
from typing import Callable, List

import pandas as pd

from ..trade_loader import Trade
from ..exceptions import NoTradesError, ExportError

logger = logging.getLogger(__name__)


def _export_with_logging(
    export_fn: Callable[[List[Trade], str], None],
    trades: List[Trade],
    filename: str,
    fmt_name: str,
) -> bool:
    """Guard, execute, and log an export operation."""
    if not trades:
        raise NoTradesError("No trades to export.")
    try:
        export_fn(trades, filename)
        logger.info("Trades exported to: %s", filename)
        return True
    except (NoTradesError, ExportError):
        raise
    except Exception as e:
        logger.error("Error exporting to %s: %s", fmt_name, e)
        raise ExportError(f"Error exporting to {fmt_name} {filename}: {e}") from e


def _write_csv(trades: List[Trade], filename: str) -> None:
    df = pd.DataFrame([t.to_dict() for t in trades])
    df.to_csv(filename, index=False)


def _write_excel(trades: List[Trade], filename: str) -> None:
    df = pd.DataFrame([t.to_dict() for t in trades])
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All Trades", index=False)
        summary = (
            df.groupby("market_slug")
            .agg({"cost": "sum", "pnl": "sum", "market": "first"})
            .rename(columns={"market": "market_name"})
        )
        summary["trade_count"] = df.groupby("market_slug").size()
        summary.to_excel(writer, sheet_name="Market Summary")


def _write_json(trades: List[Trade], filename: str) -> None:
    trades_dict = [t.to_dict() for t in trades]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(trades_dict, f, indent=2)


def export_to_csv(trades: List[Trade], filename: str = "trades_export.csv"):
    """Export trades to CSV file."""
    return _export_with_logging(_write_csv, trades, filename, "CSV")


def export_to_excel(trades: List[Trade], filename: str = "trades_export.xlsx"):
    """Export trades to Excel file with multiple sheets."""
    return _export_with_logging(_write_excel, trades, filename, "Excel")


def export_to_json(trades: List[Trade], filename: str = "trades_export.json"):
    """Export trades to JSON file."""
    return _export_with_logging(_write_json, trades, filename, "JSON")
