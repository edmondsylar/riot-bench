"""
Core task abstractions for PyRIoTBench.

This module defines the foundational interfaces and base classes for all benchmark tasks.
The design follows the Template Method pattern to enable automatic instrumentation while
keeping task implementations platform-agnostic.

Key Classes:
    - ITask: Protocol defining the task contract (no platform dependencies)
    - BaseTask: Abstract base class with automatic timing and error handling
    - TaskResult: Dataclass for task execution results

Architecture:
    Tasks implement the abstract `do_task()` method with pure business logic.
    The BaseTask handles timing, error handling, and lifecycle management automatically.
    This separation enables the same task to run on Beam, Flink, Ray, or standalone.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, Any, Optional, Dict
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """
    Result of a task execution with timing and status information.
    
    Attributes:
        value: The computed result (float for numeric tasks, Any for complex outputs)
        execution_time_ms: Time taken to execute do_task() in milliseconds
        success: Whether the task completed successfully
        error_message: Error details if task failed
        metadata: Additional task-specific information
    """
    value: Any
    execution_time_ms: float
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.value} ({self.execution_time_ms:.2f}ms)"


class ITask(Protocol):
    """
    Protocol defining the contract that all benchmark tasks must follow.
    
    This is a structural type (duck typing) - any class implementing these methods
    can be used as a task, regardless of inheritance. This provides maximum flexibility
    while maintaining type safety.
    
    The protocol ensures tasks are:
    - Platform-agnostic (no Storm/Beam/Flink dependencies)
    - Composable (can be chained in dataflows)
    - Testable (can be run standalone)
    - Instrumentable (timing/metrics can be added automatically)
    
    Lifecycle:
        1. setup() - Initialize resources, load models, connect to services
        2. do_task(input) - Process data (called repeatedly)
        3. get_last_result() - Retrieve result of last execution
        4. tear_down() - Cleanup resources
    """
    
    def setup(self) -> None:
        """
        Initialize task resources.
        
        Called once before task execution begins. Use this to:
        - Load ML models
        - Establish database connections
        - Initialize bloom filters
        - Parse configuration
        
        Raises:
            Exception: If setup fails (task should not be used)
        """
        ...
    
    def do_task(self, input_data: Any) -> Any:
        """
        Execute the task's core logic on input data.
        
        This is the main work method - called once per input element.
        Should be pure computation without side effects when possible.
        
        Args:
            input_data: Input element to process (type depends on task)
            
        Returns:
            Processed result (type depends on task)
            
        Raises:
            Exception: If processing fails (BaseTask catches and logs)
        """
        ...
    
    def get_last_result(self) -> TaskResult:
        """
        Retrieve the result of the most recent do_task() execution.
        
        Returns:
            TaskResult with value, timing, and status information
        """
        ...
    
    def tear_down(self) -> None:
        """
        Cleanup task resources.
        
        Called once after all processing is complete. Use this to:
        - Close database connections
        - Release file handles
        - Save final state
        - Log statistics
        """
        ...


class BaseTask(ABC):
    """
    Abstract base class implementing the ITask protocol with automatic instrumentation.
    
    This class uses the Template Method pattern:
    - Concrete methods handle timing, error handling, lifecycle
    - Abstract method `do_task()` is implemented by subclasses
    
    Features:
    - Automatic timing instrumentation (microsecond precision)
    - Error handling with graceful degradation (Float('-inf') signals)
    - Logging integration
    - Result caching
    
    Subclass Implementation:
        class MyTask(BaseTask):
            def setup(self) -> None:
                # Load resources
                self.model = load_model("path/to/model")
            
            def do_task(self, input_data: str) -> float:
                # Pure business logic - no timing code!
                return self.model.predict(input_data)
            
            def tear_down(self) -> None:
                # Cleanup
                self.model.close()
    
    Usage:
        task = MyTask()
        task.setup()
        result = task.do_task("some input")
        print(task.get_last_result())  # Includes timing!
        task.tear_down()
    """
    
    def __init__(self) -> None:
        """Initialize task state."""
        self._last_result: Optional[TaskResult] = None
        self._setup_complete: bool = False
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def setup(self) -> None:
        """
        Default setup implementation (can be overridden).
        
        Override this if your task needs initialization.
        Call super().setup() if you do override.
        """
        self._setup_complete = True
        self._logger.info(f"{self.__class__.__name__} setup complete")
    
    @abstractmethod
    def do_task(self, input_data: Any) -> Any:
        """
        Abstract method - MUST be implemented by subclasses.
        
        Implement your task's core logic here. Do NOT add timing code -
        it's handled automatically by execute().
        
        Args:
            input_data: Input to process
            
        Returns:
            Processed output
        """
        pass
    
    def execute(self, input_data: Any) -> Any:
        """
        Template method that wraps do_task() with instrumentation.
        
        This is what platform adapters should call, not do_task() directly.
        Handles:
        - Timing measurement
        - Error handling
        - Result caching
        - Logging
        
        Args:
            input_data: Input to process
            
        Returns:
            Result of do_task() (or Float('-inf') on error)
        """
        if not self._setup_complete:
            self._logger.warning(f"{self.__class__.__name__}.setup() not called!")
        
        start_time = time.perf_counter()
        
        try:
            # Call the subclass implementation
            result = self.do_task(input_data)
            
            # Capture timing
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            
            # Cache result
            self._last_result = TaskResult(
                value=result,
                execution_time_ms=execution_time_ms,
                success=True
            )
            
            self._logger.debug(f"Task executed in {execution_time_ms:.3f}ms")
            return result
            
        except Exception as e:
            # Error handling - log and return sentinel value
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            
            error_msg = f"Task failed: {type(e).__name__}: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            
            # Cache error result
            self._last_result = TaskResult(
                value=float('-inf'),
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=error_msg
            )
            
            # Return sentinel value (matches Java RIoTBench behavior)
            return float('-inf')
    
    def get_last_result(self) -> TaskResult:
        """
        Get the result of the most recent execute() call.
        
        Returns:
            TaskResult with timing and status, or a default if never executed
        """
        if self._last_result is None:
            return TaskResult(
                value=None,
                execution_time_ms=0.0,
                success=False,
                error_message="Task has not been executed yet"
            )
        return self._last_result
    
    def tear_down(self) -> None:
        """
        Default teardown implementation (can be overridden).
        
        Override this if your task needs cleanup.
        Call super().tear_down() if you do override.
        """
        self._logger.info(f"{self.__class__.__name__} teardown complete")
        self._setup_complete = False
    
    def __str__(self) -> str:
        """String representation showing task name and last result."""
        result = self._last_result
        if result:
            return f"{self.__class__.__name__}: {result}"
        return f"{self.__class__.__name__}: Not executed"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"<{self.__class__.__name__} at {hex(id(self))}>"


class StatefulTask(BaseTask):
    """
    Base class for tasks that maintain state across invocations.
    
    Some tasks need to remember previous results for:
    - Kalman filtering (requires previous state)
    - Moving averages (requires window of values)
    - Anomaly detection (requires baseline statistics)
    
    This class provides a simple state management interface.
    
    Example:
        class MovingAverageTask(StatefulTask):
            def setup(self) -> None:
                super().setup()
                self.window = []
                self.window_size = 10
            
            def do_task(self, value: float) -> float:
                self.window.append(value)
                if len(self.window) > self.window_size:
                    self.window.pop(0)
                return sum(self.window) / len(self.window)
    """
    
    def __init__(self) -> None:
        """Initialize stateful task."""
        super().__init__()
        self._state: Dict[str, Any] = {}
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value by key."""
        return self._state.get(key, default)
    
    def set_state(self, key: str, value: Any) -> None:
        """Set state value by key."""
        self._state[key] = value
    
    def clear_state(self) -> None:
        """Clear all state (useful for testing)."""
        self._state.clear()
    
    def tear_down(self) -> None:
        """Clear state on teardown."""
        self.clear_state()
        super().tear_down()


# Type alias for convenience
Task = BaseTask
