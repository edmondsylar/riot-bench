"""
Statistics tasks for RIoTBench.

This module contains statistical computation benchmarks for IoT streaming data.

Available Tasks:
    - Accumulator: Windowed accumulator for batching sensor data
    - Interpolation: Linear interpolation for missing sensor values
    - KalmanFilter: 1D Kalman filter for sensor noise reduction
    - SecondOrderMoment: Variance/distribution surprise detection using Alon-Matias-Szegedy algorithm
"""

from pyriotbench.tasks.statistics.accumulator import Accumulator
from pyriotbench.tasks.statistics.interpolation import Interpolation
from pyriotbench.tasks.statistics.kalman_filter import KalmanFilterTask
from pyriotbench.tasks.statistics.second_order_moment import SecondOrderMoment

__all__ = ["Accumulator", "Interpolation", "KalmanFilterTask", "SecondOrderMoment"]
