"""
Flink MapFunction adapter for RIoTBench tasks.

This module wraps ITask implementations in Flink's MapFunction interface,
enabling seamless execution in PyFlink DataStream pipelines.

Design Pattern:
    Adapter Pattern - Adapts ITask interface to Flink's MapFunction interface
    
Key Features:
    - Automatic task lifecycle management (setup/teardown)
    - Per-worker task instantiation
    - Metrics collection and propagation
    - Error handling with sentinel values
    - Thread-safe execution
    
Usage:
    from pyriotbench.platforms.flink.adapter import FlinkTaskMapFunction
    from pyflink.datastream import StreamExecutionEnvironment
    
    env = StreamExecutionEnvironment.get_execution_environment()
    ds = env.from_collection(['input1', 'input2'])
    ds.map(FlinkTaskMapFunction('kalman_filter', config)).print()
    env.execute()
"""

import logging
import time
from typing import Any, Dict, Optional

from pyflink.datastream import MapFunction

from pyriotbench.core.registry import TaskRegistry
from pyriotbench.core.task import ITask

logger = logging.getLogger(__name__)


class FlinkTaskMapFunction(MapFunction):
    """
    PyFlink MapFunction that wraps a RIoTBench task.
    
    This adapter enables any ITask implementation to run in Flink DataStream pipelines,
    maintaining full compatibility with RIoTBench's task interface while
    leveraging Flink's distributed execution capabilities.
    
    Lifecycle:
        1. __init__: Store task configuration (serializable)
        2. open: Create task instance (once per parallel instance)
        3. map: Execute task on each element
        4. close: Cleanup task resources
    
    Attributes:
        task_name: Name of the registered task
        config: Task configuration dictionary
        task: Task instance (created in open())
    
    Example:
        >>> from pyflink.datastream import StreamExecutionEnvironment
        >>> env = StreamExecutionEnvironment.get_execution_environment()
        >>> map_fn = FlinkTaskMapFunction('kalman_filter', {
        ...     'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
        ...     'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
        ... })
        >>> ds = env.from_collection(['25.0', '26.1', '24.8'])
        >>> ds.map(map_fn).print()
        >>> env.execute("Kalman Filter Example")
    """
    
    def __init__(self, task_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Flink MapFunction adapter.
        
        Args:
            task_name: Name of the registered task (e.g., 'kalman_filter')
            config: Task configuration dictionary (must be serializable)
        
        Raises:
            ValueError: If task_name is not registered
        """
        super().__init__()
        
        # Import tasks to ensure registration
        import pyriotbench.tasks  # noqa: F401
        
        # Validate task exists
        if not TaskRegistry.is_registered(task_name):
            raise ValueError(
                f"Task '{task_name}' is not registered. "
                f"Available tasks: {', '.join(TaskRegistry.list_tasks())}"
            )
        
        self.task_name = task_name
        self.config = config or {}
        self.task: Optional[ITask] = None
        self._start_time: Optional[float] = None
        self._record_count = 0
        self._error_count = 0
        
        logger.info(f"FlinkTaskMapFunction created for task '{task_name}'")
    
    def open(self, runtime_context) -> None:
        """
        Initialize the task instance (called once per parallel instance).
        
        This method is called by Flink when the parallel instance starts.
        It creates the task instance and calls setup().
        
        Args:
            runtime_context: Flink runtime context (provides task info, metrics, etc.)
        """
        # Import tasks to ensure registration in this process
        import pyriotbench.tasks  # noqa: F401
        
        # Create task instance
        task_class = TaskRegistry.get(self.task_name)
        self.task = task_class()
        
        # Set configuration - must be set BEFORE calling setup()
        self.task.config = self.config
        
        # Setup task
        try:
            self.task.setup()
            self._start_time = time.time()
            logger.info(
                f"Task '{self.task_name}' setup complete on "
                f"parallel instance {runtime_context.get_index_of_this_subtask()}"
            )
        except Exception as e:
            logger.error(f"Task setup failed: {e}", exc_info=True)
            raise
    
    def map(self, value: Any) -> Any:
        """
        Execute the task on a single input element.
        
        This is called by Flink for each record in the stream.
        
        Args:
            value: Input record (any type supported by the task)
        
        Returns:
            Output from the task's execute() method, or None on error
        """
        if self.task is None:
            logger.error("Task not initialized - open() was not called")
            return None
        
        try:
            result = self.task.execute(value)
            self._record_count += 1
            return result
        except Exception as e:
            self._error_count += 1
            logger.error(
                f"Task execution failed on record {self._record_count + 1}: {e}",
                exc_info=True
            )
            return None  # Flink continues processing
    
    def close(self) -> None:
        """
        Cleanup task resources (called when parallel instance terminates).
        
        This method is called by Flink during shutdown. It calls the task's
        tear_down() method and logs final metrics.
        """
        if self.task is None:
            return
        
        try:
            # Tear down task
            self.task.tear_down()
            
            # Log final metrics
            if self._start_time is not None:
                elapsed = time.time() - self._start_time
                throughput = self._record_count / elapsed if elapsed > 0 else 0
                
                logger.info(
                    f"Task '{self.task_name}' teardown complete. "
                    f"Processed {self._record_count} records "
                    f"({self._error_count} errors) in {elapsed:.2f}s "
                    f"({throughput:.2f} records/sec)"
                )
            
            # Get task metrics if available
            if hasattr(self.task, 'get_metrics'):
                metrics = self.task.get_metrics()
                logger.info(f"Task metrics: {metrics}")
        
        except Exception as e:
            logger.error(f"Task teardown failed: {e}", exc_info=True)
    
    def __repr__(self) -> str:
        """String representation of the MapFunction."""
        return (
            f"FlinkTaskMapFunction(task_name='{self.task_name}', "
            f"config={self.config})"
        )
