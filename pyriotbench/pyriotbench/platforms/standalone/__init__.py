"""Standalone platform adapter for PyRIoTBench.

This module provides a simple, single-process runner for executing tasks
without any distributed framework dependencies. Perfect for:
- Local development and testing
- Small datasets (< 1GB)
- CI/CD pipelines
- Educational demos
- Baseline performance measurements
"""

from .runner import StandaloneRunner

__all__ = ["StandaloneRunner"]
