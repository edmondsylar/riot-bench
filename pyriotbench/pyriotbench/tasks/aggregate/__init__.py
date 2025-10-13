"""
Aggregate tasks for RIoTBench.

This module contains aggregation and windowing benchmarks for IoT streaming data.

Available Tasks:
    - BlockWindowAverage: Windowed average aggregation
    - DistinctApproxCount: Approximate cardinality estimation using Durand-Flajolet algorithm
"""

from pyriotbench.tasks.aggregate.block_window_average import BlockWindowAverage
from pyriotbench.tasks.aggregate.distinct_approx_count import DistinctApproxCount

__all__ = ["BlockWindowAverage", "DistinctApproxCount"]
