"""
Math tasks for RIoTBench.

This module contains mathematical computation benchmarks for IoT streaming data.

Available Tasks:
    - PiByViete: Calculate π (pi) using Viète's infinite product formula
"""

from pyriotbench.tasks.math.pi_by_viete import PiByViete

__all__ = ["PiByViete"]
