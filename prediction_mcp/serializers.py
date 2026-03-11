# prediction_mcp/serializers.py
"""
JSON-safe serialization helpers for MCP tool responses.

Ensures all data returned from tools is JSON-serializable,
handling NaN/Infinity, datetime objects, and dataclass conversion.
"""

import json
import math
from typing import Any, Dict, List

from prediction_analyzer.trade_loader import Trade, sanitize_numeric


def serialize_trades(trades: List[Trade]) -> List[Dict[str, Any]]:
    """Convert a list of Trade objects to JSON-safe dicts."""
    return [t.to_dict() for t in trades]


def sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize a dictionary for JSON serialization.

    Replaces NaN/Infinity floats and converts non-serializable types.
    """
    result = {}
    for key, value in d.items():
        result[key] = _sanitize_value(value)
    return result


def _sanitize_value(value: Any) -> Any:
    """Sanitize a single value for JSON serialization."""
    if isinstance(value, float):
        return sanitize_numeric(value)
    if isinstance(value, dict):
        return sanitize_dict(value)
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def to_json_text(data: Any) -> str:
    """Serialize data to a formatted JSON string for MCP text responses."""
    if isinstance(data, dict):
        data = sanitize_dict(data)
    elif isinstance(data, (list, tuple)):
        data = [_sanitize_value(v) for v in data]
    return json.dumps(data, indent=2, default=str)
