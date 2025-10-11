"""NoOperation task - baseline for measuring framework overhead.

This module provides the NoOpTask benchmark, which performs minimal computation
to measure the pure overhead of the PyRIoTBench framework. It's useful for:
- Baseline performance measurement
- Framework overhead calculation
- Testing task infrastructure
- Template for implementing new tasks
"""

from __future__ import annotations

from typing import Any
import logging

from pyriotbench.core import BaseTask, register_task


@register_task("noop")
class NoOpTask(BaseTask):
    """
    No-operation task that simply passes through the input.
    
    This benchmark measures the pure overhead of the PyRIoTBench framework
    without any actual computation. The task simply returns the input data
    unchanged, allowing measurement of the framework's instrumentation,
    timing, and metric collection overhead.
    
    **Purpose:**
    - Baseline for performance comparison
    - Framework overhead measurement
    - Infrastructure validation
    - Template for new task implementations
    
    **Input:**
    - Any data type (str, int, dict, etc.)
    
    **Output:**
    - Same as input (pass-through)
    
    **Configuration:**
    None required - this task has no configuration parameters.
    
    **Example:**
    ```python
    from pyriotbench.tasks.noop import NoOpTask
    
    task = NoOpTask()
    task.setup()
    
    # Pass through a value
    result = task.execute(42)
    print(result)  # 42
    
    # Pass through a dict
    result = task.execute({"sensor": "temp", "value": 23.5})
    print(result)  # {"sensor": "temp", "value": 23.5}
    
    # Get metrics
    metrics = task.get_last_result()
    print(f"Execution time: {metrics.execution_time_ms:.3f}ms")
    
    task.tear_down()
    ```
    """
    
    def setup(self) -> None:
        """
        Setup the NoOp task.
        
        This task requires minimal setup since it performs no actual computation.
        """
        super().setup()
        self._logger.info("NoOpTask initialized - ready for pass-through operations")
        self._logger.debug("NoOpTask configuration: None required (no-operation benchmark)")
    
    def do_task(self, input_data: Any) -> Any:
        """
        Pass through the input data unchanged.
        
        This method simply returns the input data as-is. If the input is a dictionary
        with a "value" key, it returns that value; otherwise, it returns the entire
        input unchanged.
        
        Args:
            input_data: Any input data (str, int, dict, list, etc.)
            
        Returns:
            The input data unchanged, or the "value" field if input is a dict
            
        Examples:
            >>> task = NoOpTask()
            >>> task.setup()
            >>> task.do_task(42)
            42
            >>> task.do_task("hello")
            "hello"
            >>> task.do_task({"value": 123})
            123
            >>> task.do_task({"sensor": "temp", "reading": 23.5})
            {"sensor": "temp", "reading": 23.5}
        """
        # If it's a dict with a "value" key, extract it
        # Otherwise, pass through as-is
        if isinstance(input_data, dict) and "value" in input_data:
            return input_data["value"]
        return input_data
    
    def tear_down(self) -> None:
        """
        Cleanup the NoOp task.
        
        Minimal cleanup since no resources were allocated.
        """
        self._logger.info("NoOpTask complete")
