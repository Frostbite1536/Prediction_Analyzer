# prediction_analyzer/utils/export.py
"""
Export utility functions
"""
import logging
import matplotlib.pyplot as plt
from typing import Any

from ..exceptions import ExportError

logger = logging.getLogger(__name__)

def export_chart(fig: Any, path: str):
    """
    Export a matplotlib or plotly figure to file

    Args:
        fig: matplotlib Figure or plotly graph object
        path: Output file path
    """
    try:
        # Check if it's a matplotlib figure
        if isinstance(fig, plt.Figure):
            fig.savefig(path, dpi=150, bbox_inches='tight')
            logger.info("Chart exported to: %s", path)
        # Check if it's a plotly figure
        elif hasattr(fig, 'write_html'):
            fig.write_html(path)
            logger.info("Interactive chart exported to: %s", path)
        elif hasattr(fig, 'write_image'):
            fig.write_image(path)
            logger.info("Chart exported to: %s", path)
        else:
            raise ExportError(f"Unsupported figure type for export: {type(fig).__name__}")
        return True
    except ExportError:
        raise
    except Exception as e:
        logger.error("Error exporting chart: %s", e)
        raise ExportError(f"Error exporting chart to {path}: {e}") from e
