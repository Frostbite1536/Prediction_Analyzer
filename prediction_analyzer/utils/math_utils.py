# prediction_analyzer/utils/math_utils.py
"""
Mathematical utility functions
"""
import numpy as np
from typing import List

def moving_average(values: List[float], window: int = 5) -> np.ndarray:
    """
    Calculate simple moving average

    Args:
        values: List of numeric values
        window: Window size for moving average

    Returns:
        NumPy array of moving averages
    """
    if len(values) < window:
        window = len(values)
    return np.convolve(values, np.ones(window)/window, mode='valid')

def weighted_average(values: List[float], weights: List[float]) -> float:
    """
    Calculate weighted average

    Args:
        values: List of numeric values
        weights: List of weights (same length as values)

    Returns:
        Weighted average
    """
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")
    return np.average(values, weights=weights)

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division that returns default value if denominator is zero

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Value to return if denominator is zero

    Returns:
        Division result or default value
    """
    return numerator / denominator if denominator != 0 else default

def calculate_roi(pnl: float, investment: float) -> float:
    """
    Calculate return on investment percentage

    Args:
        pnl: Profit/loss amount
        investment: Initial investment amount

    Returns:
        ROI as percentage
    """
    return safe_divide(pnl, investment, 0.0) * 100
