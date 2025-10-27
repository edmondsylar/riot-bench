"""Adapter for wrapping PyRIoTBench tasks as TTPython Stream Queries.

This module provides the core adapter logic that bridges PyRIoTBench's class-based
task architecture with TTPython's function-based Stream Query model.
"""

from typing import Type, Dict, Any, Callable
import logging
import sys
import os

# Add TTPython to Python path
_ttpython_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../../TTPython/ticktalkpython/tt')
)
if _ttpython_path not in sys.path:
    sys.path.insert(0, _ttpython_path)

from SQ import SQify  # type: ignore


def wrap_task_as_sq(task_class: Type, config: Dict[str, Any] = None) -> Callable:
    """
    Wraps a PyRIoTBench task class as a TTPython @SQify function.
    
    This adapter bridges two different paradigms:
    - PyRIoTBench: Class-based tasks with setup/execute/teardown lifecycle
    - TTPython: Function-based Stream Queries with sq_state for persistence
    
    The adapter:
    1. Creates a task instance on first invocation
    2. Calls setup() once during initialization
    3. Calls execute() on every invocation
    4. Stores task instance in sq_state for persistence
    
    Args:
        task_class: Task class implementing BaseTask protocol
        config: Configuration dictionary for the task
    
    Returns:
        @SQify decorated function that wraps the task
        
    Example:
        from pyriotbench.tasks.noop import NoOpTask
        from pyriotbench.platforms.ttpython.adapter import wrap_task_as_sq
        
        config = {}
        noop_sq = wrap_task_as_sq(NoOpTask, config)
        
        # Now noop_sq can be used in a TTPython @GRAPHify function
    """
    
    if config is None:
        config = {}
    
    @SQify
    def task_sq_wrapper(input_data):
        """TTPython Stream Query wrapper for PyRIoTBench task."""
        global sq_state
        
        # Initialize task instance on first invocation
        if sq_state.get('task_instance') is None:
            # Create task
            task = task_class()
            
            # Create logger
            logger = logging.getLogger(f'pyriotbench.ttpython.{task_class.__name__}')
            logger.setLevel(logging.INFO)
            
            # Setup task
            task.setup()
            
            # Store in SQ state
            sq_state['task_instance'] = task
            sq_state['logger'] = logger
            sq_state['config'] = config
            
            logger.info(f"Initialized {task_class.__name__} in TTPython SQ")
        
        # Get task instance
        task = sq_state['task_instance']
        
        # Execute task with PyRIoTBench data format
        # PyRIoTBench tasks expect input_data directly
        # Use execute() which handles timing and error handling
        result = task.execute(input_data)
        
        # TTPython expects return values for dataflow
        # Return the result from the task
        return result
    
    # Set a meaningful name for debugging
    task_sq_wrapper.__name__ = f"{task_class.__name__}_SQ"
    
    return task_sq_wrapper
