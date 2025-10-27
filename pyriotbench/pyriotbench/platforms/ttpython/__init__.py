"""TTPython platform adapter for PyRIoTBench.

This module provides integration between PyRIoTBench tasks and the TTPython
distributed time-sensitive execution framework.

Key Components:
    - wrap_task_as_sq: Wraps PyRIoTBench tasks as TTPython Stream Queries
    - TTPythonRunner: Creates and executes TTPython pipelines
    - TTPythonConfig: Configuration for TTPython execution

Example:
    from pyriotbench.tasks.noop import NoOpTask
    from pyriotbench.platforms.ttpython import TTPythonRunner
    
    runner = TTPythonRunner(config={})
    graph, pipeline_func = runner.create_pipeline([NoOpTask])
    results = runner.run(graph, pipeline_func, input_data=[1, 2, 3])
"""

from .adapter import wrap_task_as_sq
from .runner import TTPythonRunner

__all__ = ['wrap_task_as_sq', 'TTPythonRunner']
