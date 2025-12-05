# prediction_analyzer/utils/export.py
"""
Export utility functions
"""
import matplotlib.pyplot as plt
from typing import Any

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
            print(f"✅ Chart exported to: {path}")
        # Check if it's a plotly figure
        elif hasattr(fig, 'write_html'):
            fig.write_html(path)
            print(f"✅ Interactive chart exported to: {path}")
        elif hasattr(fig, 'write_image'):
            fig.write_image(path)
            print(f"✅ Chart exported to: {path}")
        else:
            print(f"❌ Unsupported figure type for export")
            return False
        return True
    except Exception as e:
        print(f"❌ Error exporting chart: {e}")
        return False
