# tests/static_patterns/test_imports.py
"""
Import Integrity Tests

These tests verify that all modules can be imported without errors.
Run these tests BEFORE implementing new features to ensure the codebase
is in a stable state.
"""
import pytest
import sys


class TestPackageImports:
    """Test that the main package and all modules can be imported."""

    def test_main_package_import(self):
        """Main package should import without errors."""
        import prediction_analyzer
        assert prediction_analyzer is not None
        assert hasattr(prediction_analyzer, "__version__")

    def test_package_version_format(self):
        """Package version should be a valid semantic version string."""
        import prediction_analyzer
        version = prediction_analyzer.__version__
        assert isinstance(version, str)
        # Basic semver check: should have at least major.minor format
        parts = version.split(".")
        assert len(parts) >= 2, f"Version '{version}' should be in semver format"
        assert parts[0].isdigit(), f"Major version should be numeric"
        assert parts[1].isdigit(), f"Minor version should be numeric"


class TestCoreModuleImports:
    """Test imports of core modules."""

    def test_trade_loader_import(self):
        """trade_loader module should import."""
        from prediction_analyzer import trade_loader
        assert trade_loader is not None

    def test_trade_loader_classes(self):
        """trade_loader should export Trade dataclass."""
        from prediction_analyzer.trade_loader import Trade
        assert Trade is not None

    def test_trade_loader_functions(self):
        """trade_loader should export core functions."""
        from prediction_analyzer.trade_loader import load_trades, save_trades
        assert callable(load_trades)
        assert callable(save_trades)

    def test_pnl_import(self):
        """pnl module should import."""
        from prediction_analyzer import pnl
        assert pnl is not None

    def test_pnl_functions(self):
        """pnl should export calculation functions."""
        from prediction_analyzer.pnl import (
            calculate_pnl,
            calculate_global_pnl_summary,
            calculate_market_pnl,
            calculate_market_pnl_summary
        )
        assert callable(calculate_pnl)
        assert callable(calculate_global_pnl_summary)
        assert callable(calculate_market_pnl)
        assert callable(calculate_market_pnl_summary)

    def test_filters_import(self):
        """filters module should import."""
        from prediction_analyzer import filters
        assert filters is not None

    def test_filters_functions(self):
        """filters should export filter functions."""
        from prediction_analyzer.filters import (
            filter_by_date,
            filter_by_trade_type,
            filter_by_side,
            filter_by_pnl
        )
        assert callable(filter_by_date)
        assert callable(filter_by_trade_type)
        assert callable(filter_by_side)
        assert callable(filter_by_pnl)

    def test_config_import(self):
        """config module should import."""
        from prediction_analyzer import config
        assert config is not None

    def test_config_exports(self):
        """config should export expected constants and functions."""
        from prediction_analyzer.config import (
            API_BASE_URL,
            DEFAULT_TRADE_FILE,
            STYLES,
            get_trade_style,
            PRICE_RESOLUTION_THRESHOLD
        )
        assert isinstance(API_BASE_URL, str)
        assert isinstance(DEFAULT_TRADE_FILE, str)
        assert isinstance(STYLES, dict)
        assert callable(get_trade_style)
        assert isinstance(PRICE_RESOLUTION_THRESHOLD, (int, float))

    def test_trade_filter_import(self):
        """trade_filter module should import."""
        from prediction_analyzer import trade_filter
        assert trade_filter is not None

    def test_inference_import(self):
        """inference module should import."""
        from prediction_analyzer import inference
        assert inference is not None


class TestChartModuleImports:
    """Test imports of chart/visualization modules."""

    def test_charts_package_import(self):
        """charts package should import."""
        from prediction_analyzer import charts
        assert charts is not None

    def test_simple_chart_import(self):
        """simple chart module should import."""
        from prediction_analyzer.charts import simple
        assert simple is not None

    def test_simple_chart_function(self):
        """simple module should export generate_simple_chart."""
        from prediction_analyzer.charts.simple import generate_simple_chart
        assert callable(generate_simple_chart)

    def test_pro_chart_import(self):
        """pro chart module should import."""
        from prediction_analyzer.charts import pro
        assert pro is not None

    def test_enhanced_chart_import(self):
        """enhanced chart module should import."""
        from prediction_analyzer.charts import enhanced
        assert enhanced is not None

    def test_global_chart_import(self):
        """global_chart module should import."""
        from prediction_analyzer.charts import global_chart
        assert global_chart is not None


class TestUtilityModuleImports:
    """Test imports of utility modules."""

    def test_utils_package_import(self):
        """utils package should import."""
        from prediction_analyzer import utils
        assert utils is not None

    def test_math_utils_import(self):
        """math_utils module should import."""
        from prediction_analyzer.utils import math_utils
        assert math_utils is not None

    def test_math_utils_functions(self):
        """math_utils should export expected functions."""
        from prediction_analyzer.utils.math_utils import (
            moving_average,
            weighted_average,
            safe_divide,
            calculate_roi
        )
        assert callable(moving_average)
        assert callable(weighted_average)
        assert callable(safe_divide)
        assert callable(calculate_roi)

    def test_time_utils_import(self):
        """time_utils module should import."""
        from prediction_analyzer.utils import time_utils
        assert time_utils is not None

    def test_time_utils_functions(self):
        """time_utils should export expected functions."""
        from prediction_analyzer.utils.time_utils import (
            parse_date,
            format_timestamp,
            get_date_range
        )
        assert callable(parse_date)
        assert callable(format_timestamp)
        assert callable(get_date_range)

    def test_auth_import(self):
        """auth module should import."""
        from prediction_analyzer.utils import auth
        assert auth is not None

    def test_data_utils_import(self):
        """data utils module should import."""
        from prediction_analyzer.utils import data
        assert data is not None

    def test_export_utils_import(self):
        """export utils module should import."""
        from prediction_analyzer.utils import export
        assert export is not None


class TestReportingModuleImports:
    """Test imports of reporting modules."""

    def test_reporting_package_import(self):
        """reporting package should import."""
        from prediction_analyzer import reporting
        assert reporting is not None

    def test_report_text_import(self):
        """report_text module should import."""
        from prediction_analyzer.reporting import report_text
        assert report_text is not None

    def test_report_data_import(self):
        """report_data module should import."""
        from prediction_analyzer.reporting import report_data
        assert report_data is not None

    def test_report_data_functions(self):
        """report_data should export export functions."""
        from prediction_analyzer.reporting.report_data import (
            export_to_csv,
            export_to_excel,
            export_to_json
        )
        assert callable(export_to_csv)
        assert callable(export_to_excel)
        assert callable(export_to_json)


class TestCoreSubpackageImports:
    """Test imports of core subpackage modules."""

    def test_core_package_import(self):
        """core package should import."""
        from prediction_analyzer import core
        assert core is not None

    def test_interactive_import(self):
        """interactive module should import."""
        from prediction_analyzer.core import interactive
        assert interactive is not None


class TestMainModuleImport:
    """Test the main module can be imported."""

    def test_main_module_import(self):
        """__main__ module should import."""
        from prediction_analyzer import __main__
        assert __main__ is not None


class TestNoCircularImports:
    """Verify there are no circular import issues."""

    def test_all_modules_import_together(self):
        """All modules should be importable in sequence without circular import errors."""
        # Clear any cached imports
        modules_to_clear = [key for key in sys.modules if key.startswith("prediction_analyzer")]
        for mod in modules_to_clear:
            del sys.modules[mod]

        # Import all modules in one test
        from prediction_analyzer import (
            trade_loader,
            pnl,
            filters,
            config,
            trade_filter,
            inference,
        )
        from prediction_analyzer.charts import (
            simple,
            pro,
            enhanced,
            global_chart
        )
        from prediction_analyzer.utils import (
            math_utils,
            time_utils,
            auth,
            data,
            export
        )
        from prediction_analyzer.reporting import (
            report_text,
            report_data
        )
        from prediction_analyzer.core import interactive

        # If we get here, no circular import errors
        assert True


class TestDependencyImports:
    """Verify that required dependencies can be imported."""

    def test_pandas_import(self):
        """pandas should be importable."""
        import pandas as pd
        assert pd is not None

    def test_numpy_import(self):
        """numpy should be importable."""
        import numpy as np
        assert np is not None

    def test_matplotlib_import(self):
        """matplotlib should be importable."""
        import matplotlib
        assert matplotlib is not None

    def test_plotly_import(self):
        """plotly should be importable."""
        import plotly
        assert plotly is not None

    def test_requests_import(self):
        """requests should be importable."""
        import requests
        assert requests is not None

    def test_openpyxl_import(self):
        """openpyxl should be importable."""
        import openpyxl
        assert openpyxl is not None
