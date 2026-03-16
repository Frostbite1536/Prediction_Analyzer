# prediction_analyzer/utils/math_utils.py
"""Mathematical utility functions"""

import numpy as np
from typing import List


def moving_average(values: List[float], window: int = 5) -> np.ndarray:
    """Calculate simple moving average over the given window size."""
    if len(values) < window:
        window = len(values)
    return np.convolve(values, np.ones(window) / window, mode="valid")


def weighted_average(values: List[float], weights: List[float]) -> float:
    """Calculate weighted average; values and weights must have same length."""
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")
    return np.average(values, weights=weights)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide numerator by denominator; return default on zero."""
    return numerator / denominator if denominator != 0 else default


def calculate_roi(pnl: float, investment: float) -> float:
    """Calculate return on investment as a percentage."""
    return safe_divide(pnl, investment, 0.0) * 100
