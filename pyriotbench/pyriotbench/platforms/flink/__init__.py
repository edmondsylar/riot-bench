"""
PyFlink platform integration for PyRIoTBench.

This module provides adapters and runners for executing RIoTBench tasks
on Apache Flink's DataStream API.
"""

from pyriotbench.platforms.flink.adapter import FlinkTaskMapFunction
from pyriotbench.platforms.flink.runner import FlinkRunner

__all__ = ['FlinkTaskMapFunction', 'FlinkRunner']
