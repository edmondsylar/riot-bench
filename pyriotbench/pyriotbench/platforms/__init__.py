"""Platform adapters for PyRIoTBench.

This package contains adapters for various streaming platforms:
- standalone: Simple in-process runner (for testing/development)
- beam: Apache Beam integration
- flink: PyFlink integration
- ray: Ray integration
"""

from .standalone import StandaloneRunner

__all__ = ["StandaloneRunner"]
