"""Core abstractions for PyRIoTBench.

This module contains the fundamental building blocks:
- ITask: Platform-agnostic task protocol
- BaseTask: Abstract base class with template method pattern
- TaskRegistry: Central registry for task discovery
- Configuration management
- Metrics and instrumentation
"""

from pyriotbench.core.task import (
    ITask,
    BaseTask,
    StatefulTask,
    TaskResult,
    Task,
)
from pyriotbench.core.registry import (
    TaskRegistry,
    register_task,
    register,
    get_task,
    create_task,
    list_tasks,
)
from pyriotbench.core.config import (
    BenchmarkConfig,
    PlatformConfig,
    TaskConfig,
    PlatformType,
    LogLevel,
    load_config,
)
from pyriotbench.core.metrics import (
    TaskMetrics,
    MetricsAggregator,
    create_metric,
)

__all__ = [
    # Task abstractions
    "ITask",
    "BaseTask",
    "StatefulTask",
    "TaskResult",
    "Task",
    # Registry
    "TaskRegistry",
    "register_task",
    "register",
    "get_task",
    "create_task",
    "list_tasks",
    # Configuration
    "BenchmarkConfig",
    "PlatformConfig",
    "TaskConfig",
    "PlatformType",
    "LogLevel",
    "load_config",
    # Metrics
    "TaskMetrics",
    "MetricsAggregator",
    "create_metric",
]
