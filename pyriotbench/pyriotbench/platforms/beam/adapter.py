"""
Beam DoFn adapter for RIoTBench tasks.

This module wraps ITask implementations in Beam's DoFn interface,
enabling seamless execution in Apache Beam pipelines.

Design Pattern:
    Adapter Pattern - Adapts ITask interface to Beam's DoFn interface
    
Key Features:
    - Automatic task lifecycle management (setup/teardown)
    - Per-worker task instantiation
    - Metrics collection and propagation
    - Error handling with sentinel values
    - Thread-safe execution
    
Usage:
    from pyriotbench.platforms.beam.adapter import BeamTaskDoFn
    import apache_beam as beam
    
    with beam.Pipeline() as pipeline:
        (pipeline
         | beam.Create(['input1', 'input2'])
         | beam.ParDo(BeamTaskDoFn('kalman_filter', config))
         | beam.Map(print))
"""

import logging
import time
from typing import Any, Dict, Iterator, Optional

import apache_beam as beam
from apache_beam.metrics import Metrics

from pyriotbench.core.registry import TaskRegistry
from pyriotbench.core.task import ITask

logger = logging.getLogger(__name__)


class BeamTaskDoFn(beam.DoFn):
    """
    Apache Beam DoFn that wraps a RIoTBench task.
    
    This adapter enables any ITask implementation to run in Beam pipelines,
    maintaining full compatibility with RIoTBench's task interface while
    leveraging Beam's distributed execution capabilities.
    
    Lifecycle:
        1. __init__: Store task configuration (serializable)
        2. setup: Create task instance (once per worker)
        3. process: Execute task on each element
        4. teardown: Cleanup task resources
    
    Attributes:
        task_name: Name of the registered task
        config: Task configuration dictionary
        task: Task instance (created in setup())
    
    Example:
        >>> dofn = BeamTaskDoFn('kalman_filter', {
        ...     'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
        ...     'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
        ... })
        >>> p = beam.Pipeline()
        >>> (p | beam.Create(['25.0', '26.1', '24.8'])
        ...    | beam.ParDo(dofn)
        ...    | beam.Map(print))
    """
    
    def __init__(self, task_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Beam DoFn adapter.
        
        Args:
            task_name: Name of the registered task (e.g., 'kalman_filter')
            config: Task configuration dictionary (must be serializable)
        
        Raises:
            ValueError: If task_name is not registered
        """
        super().__init__()
        
        # Validate task exists
        if not TaskRegistry.is_registered(task_name):
            raise ValueError(
                f"Task '{task_name}' not registered. "
                f"Available tasks: {TaskRegistry.list_tasks()}"
            )
        
        self.task_name = task_name
        self.config = config or {}
        self.task: Optional[ITask] = None
        
        # Beam metrics (per-worker counters)
        self.success_counter = Metrics.counter(self.task_name, 'success')
        self.error_counter = Metrics.counter(self.task_name, 'error')
        self.execution_time_dist = Metrics.distribution(self.task_name, 'execution_time_ms')
        
        logger.debug(f"BeamTaskDoFn created for task: {task_name}")
    
    def setup(self):
        """
        Setup lifecycle hook - called once per worker.
        
        Creates and initializes the task instance. This is called by Beam
        before processing any elements on this worker, ensuring efficient
        resource usage (one task instance per worker, not per element).
        
        Raises:
            Exception: If task creation or setup fails
        """
        try:
            logger.info(f"Setting up task '{self.task_name}' on worker")
            
            # Create task instance
            self.task = TaskRegistry.create(self.task_name)
            
            # Configure task
            self.task.config = self.config
            
            # Initialize task
            self.task.setup()
            
            logger.info(f"Task '{self.task_name}' setup complete")
            
        except Exception as e:
            logger.error(f"Task setup failed: {type(e).__name__}: {str(e)}", exc_info=True)
            raise
    
    def process(self, element: Any) -> Iterator[Any]:
        """
        Process a single element through the task.
        
        This is called by Beam for each element in the PCollection. The task's
        execute() method is invoked, and the result is yielded if valid.
        
        Args:
            element: Input element to process
        
        Yields:
            Processed result (if not None and not error sentinel)
        
        Note:
            - Returns None are filtered out (e.g., windowed tasks accumulating)
            - Error sentinels (float('-inf')) are filtered out
            - Metrics are recorded for success/error rates
        """
        if self.task is None:
            logger.error("Task not initialized - setup() not called")
            self.error_counter.inc()
            return
        
        try:
            # Record start time
            start_time = time.perf_counter()
            
            # Execute task
            result = self.task.execute(element)
            
            # Record execution time
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            self.execution_time_dist.update(int(execution_time_ms))
            
            # Check for valid result
            if result is None:
                # Task chose not to emit (e.g., window not full)
                logger.debug(f"Task '{self.task_name}' returned None for element: {element}")
                return
            
            # Check for error sentinel
            if isinstance(result, float) and result == float('-inf'):
                # Task encountered error
                logger.warning(f"Task '{self.task_name}' returned error for element: {element}")
                self.error_counter.inc()
                return
            
            # Valid result - emit
            self.success_counter.inc()
            yield result
            
        except Exception as e:
            # Unexpected exception (should be caught by task, but safety net)
            logger.error(
                f"Task '{self.task_name}' raised exception: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            self.error_counter.inc()
    
    def teardown(self):
        """
        Teardown lifecycle hook - called once per worker at shutdown.
        
        Cleans up task resources. Called by Beam when the worker is shutting down,
        ensuring proper cleanup of any resources held by the task.
        """
        if self.task is not None:
            try:
                logger.info(f"Tearing down task '{self.task_name}' on worker")
                self.task.tear_down()
                logger.info(f"Task '{self.task_name}' teardown complete")
            except Exception as e:
                logger.error(
                    f"Task teardown failed: {type(e).__name__}: {str(e)}",
                    exc_info=True
                )
            finally:
                self.task = None
    
    def display_data(self) -> Dict[str, Any]:
        """
        Provide display data for Beam UI/monitoring.
        
        Returns:
            Dictionary of display information for Beam's monitoring UI
        """
        return {
            'task_name': self.task_name,
            'config_keys': list(self.config.keys()),
        }
