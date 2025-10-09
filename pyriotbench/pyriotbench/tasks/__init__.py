"""Benchmark task implementations.

This package contains all 26 micro-benchmarks organized by category:
- noop: No-operation baseline (1 task)
- parse: Data parsing and transformation (4 tasks)
- filter: Filtering operations (2 tasks)
- statistics: Statistical computations (6 tasks)
- predict: Machine learning tasks (6 tasks)
- io: I/O operations (7 tasks)
- visualize: Visualization tasks (1 task)
"""

from pyriotbench.tasks.noop import NoOpTask
from pyriotbench.tasks.parse import SenMLParseTask

__all__ = [
    "NoOpTask",
    "SenMLParseTask",
]
