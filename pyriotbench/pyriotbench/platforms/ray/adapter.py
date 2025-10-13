"""
Ray Task Actor - Wraps ITask for execution in Ray actors.

This adapter enables any ITask implementation to run in Ray's actor-based
distributed computing model. Each actor maintains its own task instance with state.
"""

import logging
from typing import Any, Optional, Dict
import time

import ray

from pyriotbench.core.task import ITask
from pyriotbench.core.registry import TaskRegistry
from pyriotbench.core.metrics import TaskMetrics

# Import tasks to trigger registration
import pyriotbench.tasks  # noqa: F401


@ray.remote
class RayTaskActor:
    """
    Ray actor that wraps an ITask for distributed execution.
    
    This actor:
    - Creates a task instance on initialization
    - Maintains task state across multiple invocations
    - Collects execution metrics
    - Handles task lifecycle (setup/execute/tear_down)
    
    Usage:
        actor = RayTaskActor.remote('noop', config={})
        result = ray.get(actor.process.remote("input data"))
    
    Attributes:
        task_name: Name of the registered task to instantiate
        config: Configuration dictionary for the task
        task: The actual ITask instance (created on first __init__)
        metrics: Accumulated metrics for this actor
        _logger: Logger for this actor
    """
    
    def __init__(self, task_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Ray actor with a task instance.
        
        Args:
            task_name: Name of registered task (e.g., 'noop', 'senml_parse')
            config: Configuration dictionary to pass to task
        
        Raises:
            ValueError: If task_name is not registered
        """
        # Import tasks to ensure registration in this process
        import pyriotbench.tasks  # noqa: F401
        
        self.task_name = task_name
        self.config = config or {}
        self._logger = logging.getLogger(f"RayTaskActor[{task_name}]")
        
        # Create task instance
        if not TaskRegistry.is_registered(task_name):
            raise ValueError(f"Task '{task_name}' is not registered")
        
        task_class = TaskRegistry.get(task_name)
        self.task: ITask = task_class()
        
        # Set configuration
        if hasattr(self.task, 'config'):
            self.task.config = self.config
        
        # Setup task
        try:
            self.task.setup()
            self._logger.info(f"Task {task_name} setup complete")
        except Exception as e:
            self._logger.error(f"Task setup failed: {e}")
            raise
        
        # Initialize metrics
        self.metrics = {
            'total_processed': 0,
            'total_time': 0.0,
            'errors': 0,
            'none_filtered': 0,
        }
    
    def process(self, data: Any) -> Any:
        """
        Process a single data item through the task.
        
        Args:
            data: Input data for the task
        
        Returns:
            Task output (can be None for windowed tasks)
        
        Raises:
            Exception: If task execution fails
        """
        start_time = time.time()
        
        try:
            # Execute task
            result = self.task.execute(data)
            
            # Update metrics
            self.metrics['total_processed'] += 1
            
            # Handle None results (windowed tasks)
            if result is None:
                self.metrics['none_filtered'] += 1
            
            # Track timing
            elapsed = time.time() - start_time
            self.metrics['total_time'] += elapsed
            
            return result
            
        except Exception as e:
            self.metrics['errors'] += 1
            self._logger.error(f"Task execution failed: {e}")
            raise
    
    def process_batch(self, data_items: list) -> list:
        """
        Process a batch of data items.
        
        Args:
            data_items: List of input data items
        
        Returns:
            List of results (same length as input)
        """
        results = []
        for item in data_items:
            try:
                result = self.process(item)
                results.append(result)
            except Exception as e:
                self._logger.error(f"Batch item failed: {e}")
                results.append(None)
        
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get accumulated metrics for this actor.
        
        Returns:
            Dictionary with metrics:
                - total_processed: Number of items processed
                - total_time: Total processing time
                - errors: Number of errors
                - none_filtered: Number of None results
                - avg_time: Average time per item
                - throughput: Items per second
        """
        metrics = self.metrics.copy()
        
        # Calculate derived metrics
        if metrics['total_processed'] > 0:
            metrics['avg_time'] = metrics['total_time'] / metrics['total_processed']
            
            if metrics['total_time'] > 0:
                metrics['throughput'] = metrics['total_processed'] / metrics['total_time']
            else:
                metrics['throughput'] = 0.0
        else:
            metrics['avg_time'] = 0.0
            metrics['throughput'] = 0.0
        
        return metrics
    
    def tear_down(self) -> None:
        """
        Tear down the task and clean up resources.
        """
        try:
            self.task.tear_down()
            self._logger.info(f"Task {self.task_name} torn down")
        except Exception as e:
            self._logger.error(f"Task tear_down failed: {e}")
    
    def get_task_name(self) -> str:
        """Get the name of the wrapped task."""
        return self.task_name
    
    def get_config(self) -> Dict[str, Any]:
        """Get the task configuration."""
        return self.config.copy()


def create_ray_actor(task_name: str, config: Optional[Dict[str, Any]] = None) -> Any:
    """
    Helper function to create a Ray actor for a task.
    
    Args:
        task_name: Name of registered task
        config: Configuration dictionary
    
    Returns:
        Ray actor handle (ActorHandle)
    
    Example:
        actor = create_ray_actor('noop')
        result = ray.get(actor.process.remote("data"))
    """
    return RayTaskActor.remote(task_name, config)


def create_ray_actors(
    task_name: str,
    num_actors: int,
    config: Optional[Dict[str, Any]] = None
) -> list:
    """
    Create multiple Ray actors for parallel processing.
    
    Args:
        task_name: Name of registered task
        num_actors: Number of actors to create
        config: Configuration dictionary (shared by all actors)
    
    Returns:
        List of Ray actor handles
    
    Example:
        actors = create_ray_actors('senml_parse', num_actors=4)
        results = ray.get([actor.process.remote(data) for actor in actors])
    """
    return [RayTaskActor.remote(task_name, config) for _ in range(num_actors)]
