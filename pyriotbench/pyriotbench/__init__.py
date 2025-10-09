"""PyRIoTBench - Python IoT Benchmark Suite.

A comprehensive benchmark suite for evaluating Distributed Stream Processing Systems
in IoT contexts. Python port of the original RIoTBench with multi-platform support.
"""

__version__ = "0.1.0"
__author__ = "PyRIoTBench Team"
__license__ = "Apache-2.0"

from pyriotbench.core.task import ITask, BaseTask, StatefulTask, TaskResult
from pyriotbench.core.registry import (
    TaskRegistry,
    register_task,
    create_task,
    list_tasks,
)

__all__ = [
    "ITask",
    "BaseTask",
    "StatefulTask",
    "TaskResult",
    "TaskRegistry",
    "register_task",
    "create_task",
    "list_tasks",
    "__version__",
]
