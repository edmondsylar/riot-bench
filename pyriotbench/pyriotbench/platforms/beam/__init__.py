"""
Apache Beam platform adapter for PyRIoTBench.

This module provides Apache Beam integration through the DoFn pattern,
allowing RIoTBench tasks to run in Beam pipelines with full portability.
"""

from pyriotbench.platforms.beam.adapter import BeamTaskDoFn
from pyriotbench.platforms.beam.runner import BeamRunner

__all__ = ["BeamTaskDoFn", "BeamRunner"]
