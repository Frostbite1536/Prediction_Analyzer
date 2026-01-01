# tests/static_patterns/test_config_integrity.py
"""
Configuration Integrity Tests

These tests verify that configuration values are valid and consistent.
Invalid configuration can cause runtime errors or incorrect behavior.
"""
import pytest
import re


class TestAPIConfiguration:
    """Verify API configuration values."""

    def test_api_base_url_is_valid_url(self):
        """API_BASE_URL should be a valid HTTPS URL."""
        from prediction_analyzer.config import API_BASE_URL

        assert isinstance(API_BASE_URL, str)
        assert API_BASE_URL.startswith("https://"), \
            "API_BASE_URL should use HTTPS"
        assert len(API_BASE_URL) > 10, \
            "API_BASE_URL seems too short"

    def test_default_trade_file_is_valid_filename(self):
        """DEFAULT_TRADE_FILE should be a valid filename."""
        from prediction_analyzer.config import DEFAULT_TRADE_FILE

        assert isinstance(DEFAULT_TRADE_FILE, str)
        assert DEFAULT_TRADE_FILE.endswith(".json"), \
            "Default trade file should be JSON"
        # Should not contain path separators
        assert "/" not in DEFAULT_TRADE_FILE
        assert "\\" not in DEFAULT_TRADE_FILE


class TestStylesConfiguration:
    """Verify STYLES dictionary configuration."""

    def test_styles_is_dict(self):
        """STYLES should be a dictionary."""
        from prediction_analyzer.config import STYLES

        assert isinstance(STYLES, dict)

    def test_styles_has_all_trade_type_combinations(self):
        """STYLES should have entries for all trade type combinations."""
        from prediction_analyzer.config import STYLES

        required_combinations = [
            ("Buy", "YES"), ("Buy", "NO"),
            ("Sell", "YES"), ("Sell", "NO"),
            ("Market Buy", "YES"), ("Market Buy", "NO"),
            ("Market Sell", "YES"), ("Market Sell", "NO"),
            ("Limit Buy", "YES"), ("Limit Buy", "NO"),
            ("Limit Sell", "YES"), ("Limit Sell", "NO"),
        ]

        for combo in required_combinations:
            assert combo in STYLES, f"Missing style for {combo}"

    def test_styles_values_are_tuples(self):
        """Each STYLES value should be a tuple of (color, marker, label)."""
        from prediction_analyzer.config import STYLES

        for key, value in STYLES.items():
            assert isinstance(value, tuple), \
                f"Style for {key} should be a tuple"
            assert len(value) == 3, \
                f"Style for {key} should have 3 elements (color, marker, label)"

    def test_styles_colors_are_valid_hex(self):
        """Style colors should be valid hex color codes."""
        from prediction_analyzer.config import STYLES

        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")

        for key, (color, marker, label) in STYLES.items():
            assert hex_pattern.match(color), \
                f"Color '{color}' for {key} is not valid hex"

    def test_styles_markers_are_valid(self):
        """Style markers should be valid matplotlib markers."""
        from prediction_analyzer.config import STYLES

        valid_markers = {"o", "x", "^", "v", "s", "d", "+", "*", ".", ","}

        for key, (color, marker, label) in STYLES.items():
            assert marker in valid_markers, \
                f"Marker '{marker}' for {key} is not a recognized marker"

    def test_styles_labels_are_non_empty(self):
        """Style labels should be non-empty strings."""
        from prediction_analyzer.config import STYLES

        for key, (color, marker, label) in STYLES.items():
            assert isinstance(label, str), \
                f"Label for {key} should be a string"
            assert len(label) > 0, \
                f"Label for {key} should not be empty"


class TestGetTradeStyleFunction:
    """Verify get_trade_style function behavior."""

    def test_get_trade_style_known_combination(self):
        """get_trade_style should return correct style for known combinations."""
        from prediction_analyzer.config import get_trade_style, STYLES

        for (trade_type, side), expected_style in STYLES.items():
            result = get_trade_style(trade_type, side)
            assert result == expected_style, \
                f"Unexpected style for ({trade_type}, {side})"

    def test_get_trade_style_unknown_returns_fallback(self):
        """get_trade_style should return fallback for unknown combinations."""
        from prediction_analyzer.config import get_trade_style

        result = get_trade_style("Unknown Type", "YES")

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_get_trade_style_normalizes_buy_types(self):
        """get_trade_style should normalize types containing 'Buy'."""
        from prediction_analyzer.config import get_trade_style

        # Any type containing "Buy" should map to a Buy-style
        result = get_trade_style("Some Buy Type", "YES")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_get_trade_style_normalizes_sell_types(self):
        """get_trade_style should normalize types containing 'Sell'."""
        from prediction_analyzer.config import get_trade_style

        result = get_trade_style("Some Sell Type", "NO")
        assert isinstance(result, tuple)
        assert len(result) == 3


class TestAnalysisParameters:
    """Verify analysis parameter configuration."""

    def test_price_resolution_threshold_is_numeric(self):
        """PRICE_RESOLUTION_THRESHOLD should be numeric."""
        from prediction_analyzer.config import PRICE_RESOLUTION_THRESHOLD

        assert isinstance(PRICE_RESOLUTION_THRESHOLD, (int, float))

    def test_price_resolution_threshold_is_valid_range(self):
        """PRICE_RESOLUTION_THRESHOLD should be between 0 and 1."""
        from prediction_analyzer.config import PRICE_RESOLUTION_THRESHOLD

        assert 0 <= PRICE_RESOLUTION_THRESHOLD <= 1, \
            "Threshold should be between 0 and 1 (represents 0-100 cents)"


class TestColorConsistency:
    """Verify color consistency across styles."""

    def test_yes_buy_colors_are_consistent(self):
        """YES buy colors should be consistent (green family)."""
        from prediction_analyzer.config import STYLES

        yes_buy_styles = [
            STYLES[("Buy", "YES")],
            STYLES[("Market Buy", "YES")],
            STYLES[("Limit Buy", "YES")],
        ]

        # All should be in green family (starts with lower hex in green channel)
        for color, _, _ in yes_buy_styles:
            # Green colors typically have high G value
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            assert g >= r and g >= b, \
                f"YES buy color {color} should be greenish"

    def test_no_buy_colors_are_consistent(self):
        """NO buy colors should be consistent (magenta family)."""
        from prediction_analyzer.config import STYLES

        no_buy_styles = [
            STYLES[("Buy", "NO")],
            STYLES[("Market Buy", "NO")],
            STYLES[("Limit Buy", "NO")],
        ]

        # All should be in magenta/purple family
        for color, _, _ in no_buy_styles:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            # Magenta has high R and B, low G
            assert r > g and b > g, \
                f"NO buy color {color} should be magenta-ish"
