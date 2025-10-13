"""
Ray platform adapter for PyRIoTBench.

This module provides Ray integration for running benchmark tasks using Ray's
distributed computing framework. Tasks are wrapped in Ray actors for parallel execution.
"""

from pyriotbench.platforms.ray.adapter import RayTaskActor
from pyriotbench.platforms.ray.runner import RayRunner

__all__ = ["RayTaskActor", "RayRunner"]
