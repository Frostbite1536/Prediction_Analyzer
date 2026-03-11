# prediction_analyzer/logging_config.py
"""
Centralized logging configuration.

All modules should use:
    import logging
    logger = logging.getLogger(__name__)

Logging is configured to write to stderr so that stdout remains clean
for MCP stdio transport and piped CLI output.
"""

import logging
import sys


def configure_logging(level: int = logging.INFO):
    """
    Configure the prediction_analyzer package logger to write to stderr.

    Args:
        level: Logging level (default INFO)
    """
    root_logger = logging.getLogger("prediction_analyzer")
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        root_logger.addHandler(handler)
    root_logger.setLevel(level)


# Auto-configure on import
configure_logging()
