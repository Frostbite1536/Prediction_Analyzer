# prediction_analyzer/__init__.py
"""
Prediction Analyzer Package
A complete modular analysis tool for prediction market traders
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "MIT"

# Initialize logging to stderr (safe for MCP stdio transport)
from . import logging_config  # noqa: F401
