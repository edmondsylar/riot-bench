"""Runner for executing PyRIoTBench benchmarks on TTPython.

This module provides the TTPythonRunner class which creates and executes
TTPython pipelines from PyRIoTBench task chains.
"""

from typing import List, Type, Dict, Any, Tuple, Callable
import sys
import os

# Add TTPython to Python path
_ttpython_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../../TTPython/ticktalkpython/tt')
)
if _ttpython_path not in sys.path:
    sys.path.insert(0, _ttpython_path)

from SQ import GRAPHify  # type: ignore
from Clock import TTClock  # type: ignore
from Compiler import TTCompile  # type: ignore

from .adapter import wrap_task_as_sq


class TTPythonRunner:
    """
    Runner for executing PyRIoTBench benchmarks on TTPython.
    
    This class provides a high-level interface for:
    1. Converting PyRIoTBench task chains into TTPython graphs
    2. Compiling the graphs
    3. Simulating execution
    4. Collecting results
    
    Example:
        from pyriotbench.tasks.noop import NoOpTask
        from pyriotbench.platforms.ttpython import TTPythonRunner
        
        runner = TTPythonRunner(config={})
        graph, pipeline_func = runner.create_pipeline([NoOpTask])
        results = runner.run(graph, pipeline_func, input_data=[1, 2, 3])
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the TTPython runner.
        
        Args:
            config: Configuration dictionary for tasks
        """
        self.config = config if config is not None else {}
    
    def create_pipeline(
        self, task_classes: List[Type]
    ) -> Tuple[Any, Callable]:
        """
        Creates a TTPython pipeline from a list of task classes.
        
        This method:
        1. Wraps each task as a TTPython Stream Query
        2. Chains them together in a @GRAPHify function
        3. Returns the graph function (compilation happens separately)
        
        Args:
            task_classes: List of task classes to chain
        
        Returns:
            Tuple of (task_sqs, pipeline_function)
            
        Example:
            from pyriotbench.tasks.noop import NoOpTask
            from pyriotbench.tasks.parse.senml import SenMLParse
            
            runner = TTPythonRunner(config={})
            tasks = [SenMLParse, NoOpTask]
            task_sqs, func = runner.create_pipeline(tasks)
        """
        
        # Store task classes for execution
        self._task_classes = task_classes
        
        # Create SQ wrappers for each task
        task_sqs = [wrap_task_as_sq(cls, self.config) for cls in task_classes]
        
        # Define the graph structure
        @GRAPHify
        def pipeline_graph(trigger):
            """TTPython pipeline graph."""
            with TTClock.root() as root_clock:
                # Chain tasks sequentially
                data = trigger
                for sq in task_sqs:
                    data = sq(data)
                return data
        
        # Set meaningful name
        pipeline_graph.__name__ = "PyRIoTBench_Pipeline"
        
        # Return the task SQs and the graph function
        # Note: Actual compilation to TTPython DFG would require writing to a file
        # and using TTCompile - this is beyond the scope of a simple adapter
        return task_sqs, pipeline_graph
    
    def run(
        self, 
        task_sqs: List[Callable],
        pipeline_func: Callable,
        input_data: List[Any]
    ) -> List[Any]:
        """
        Executes the pipeline by directly calling the task instances.
        
        This is a simplified execution model that tests the adapter logic
        without full TTPython compilation and simulation infrastructure.
        
        Note: This bypasses the @SQify wrapper and directly calls the task's
        execute method, which is appropriate for testing the adapter logic.
        
        Args:
            task_sqs: List of wrapped task SQs (not used in simplified mode)
            pipeline_func: The @GRAPHify function (not used in simplified mode)
            input_data: List of input data elements
        
        Returns:
            List of execution results
            
        Example:
            task_sqs, func = runner.create_pipeline([NoOpTask])
            results = runner.run(task_sqs, func, input_data=[1, 2, 3])
        """
        
        # For testing purposes, create and execute tasks directly
        # This bypasses TTPython's execution model but validates the adapter concept
        from pyriotbench.core import BaseTask
        
        # Get task classes from config
        task_classes = self._task_classes if hasattr(self, '_task_classes') else []
        
        # If no task classes stored, we can't execute
        if not task_classes:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("No task classes available for execution")
            return [None] * len(input_data)
        
        # Execute each input through the task chain
        results = []
        for data in input_data:
            try:
                result = data
                for task_class in task_classes:
                    task = task_class()
                    task.setup()
                    result = task.execute(result)
                    task.tear_down()
                results.append(result)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error executing pipeline with input {data}: {e}")
                results.append(None)
        
        return results
