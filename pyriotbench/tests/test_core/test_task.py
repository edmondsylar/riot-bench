"""
Tests for core task abstractions.

Tests cover:
- ITask protocol compliance
- BaseTask timing instrumentation
- Error handling and sentinel values
- TaskResult dataclass
- StatefulTask state management
"""

import pytest
import time
from typing import Any

from pyriotbench.core.task import (
    BaseTask,
    StatefulTask,
    TaskResult,
    ITask
)


class SimpleTask(BaseTask):
    """Simple task for testing - just doubles the input."""
    
    def do_task(self, input_data: float) -> float:
        return input_data * 2


class ErrorTask(BaseTask):
    """Task that always raises an exception."""
    
    def do_task(self, input_data: Any) -> Any:
        raise ValueError("Intentional error for testing")


class SlowTask(BaseTask):
    """Task that takes a measurable amount of time."""
    
    def do_task(self, input_data: float) -> float:
        time.sleep(0.01)  # 10ms
        return input_data * 2


class SetupTask(BaseTask):
    """Task that requires setup."""
    
    def setup(self) -> None:
        super().setup()
        self.multiplier = 3
    
    def do_task(self, input_data: float) -> float:
        return input_data * self.multiplier


class CounterTask(StatefulTask):
    """Stateful task that counts invocations."""
    
    def setup(self) -> None:
        super().setup()
        self.set_state("count", 0)
    
    def do_task(self, input_data: float) -> float:
        count = self.get_state("count", 0)
        count += 1
        self.set_state("count", count)
        return count


# Test ITask Protocol Compliance
def test_base_task_implements_itask():
    """BaseTask should satisfy ITask protocol."""
    task = SimpleTask()
    
    # Protocol compliance (duck typing)
    assert hasattr(task, 'setup')
    assert hasattr(task, 'do_task')
    assert hasattr(task, 'get_last_result')
    assert hasattr(task, 'tear_down')
    assert callable(task.setup)
    assert callable(task.do_task)
    assert callable(task.get_last_result)
    assert callable(task.tear_down)


# Test Basic Execution
def test_simple_task_execution():
    """Test basic task execution and result."""
    task = SimpleTask()
    task.setup()
    
    result = task.execute(5.0)
    
    assert result == 10.0
    assert task.get_last_result().value == 10.0
    assert task.get_last_result().success is True


def test_multiple_executions():
    """Test that multiple executions work and update last result."""
    task = SimpleTask()
    task.setup()
    
    result1 = task.execute(2.0)
    result2 = task.execute(3.0)
    result3 = task.execute(4.0)
    
    assert result1 == 4.0
    assert result2 == 6.0
    assert result3 == 8.0
    
    # Last result should be from most recent execution
    last = task.get_last_result()
    assert last.value == 8.0
    assert last.success is True


# Test Timing Instrumentation
def test_timing_measurement():
    """Test that execution time is measured correctly."""
    task = SlowTask()
    task.setup()
    
    task.execute(5.0)
    result = task.get_last_result()
    
    # Should take at least 10ms
    assert result.execution_time_ms >= 10.0
    # But not more than 100ms (generous upper bound)
    assert result.execution_time_ms < 100.0


def test_timing_precision():
    """Test that fast tasks have low measured time."""
    task = SimpleTask()
    task.setup()
    
    task.execute(1.0)
    result = task.get_last_result()
    
    # Should be very fast (< 1ms for simple multiplication)
    assert result.execution_time_ms < 1.0


# Test Error Handling
def test_error_handling():
    """Test that errors are caught and logged."""
    task = ErrorTask()
    task.setup()
    
    result = task.execute("test")
    
    # Should return sentinel value
    assert result == float('-inf')
    
    # Result should indicate failure
    last = task.get_last_result()
    assert last.success is False
    assert last.error_message is not None
    assert "Intentional error" in last.error_message
    assert last.value == float('-inf')


def test_error_timing_still_measured():
    """Test that execution time is measured even on error."""
    task = ErrorTask()
    task.setup()
    
    task.execute("test")
    result = task.get_last_result()
    
    # Should have measured time despite error
    assert result.execution_time_ms > 0


# Test TaskResult
def test_task_result_creation():
    """Test TaskResult dataclass creation."""
    result = TaskResult(
        value=42.0,
        execution_time_ms=15.5,
        success=True
    )
    
    assert result.value == 42.0
    assert result.execution_time_ms == 15.5
    assert result.success is True
    assert result.error_message is None
    assert result.metadata == {}


def test_task_result_with_error():
    """Test TaskResult for failed execution."""
    result = TaskResult(
        value=float('-inf'),
        execution_time_ms=5.0,
        success=False,
        error_message="Something went wrong"
    )
    
    assert result.value == float('-inf')
    assert result.success is False
    assert result.error_message == "Something went wrong"


def test_task_result_str():
    """Test TaskResult string representation."""
    result_success = TaskResult(value=100.0, execution_time_ms=12.34, success=True)
    result_error = TaskResult(value=float('-inf'), execution_time_ms=5.0, success=False)
    
    assert "✓" in str(result_success)
    assert "100.0" in str(result_success)
    assert "12.34" in str(result_success)
    
    assert "✗" in str(result_error)


# Test Setup and Teardown
def test_setup_required():
    """Test that task with setup() works correctly."""
    task = SetupTask()
    task.setup()
    
    result = task.execute(10.0)
    
    # Should use multiplier set in setup
    assert result == 30.0


def test_teardown_called():
    """Test that teardown cleans up state."""
    task = SimpleTask()
    task.setup()
    task.execute(5.0)
    
    assert task._setup_complete is True
    
    task.tear_down()
    
    assert task._setup_complete is False


# Test Stateful Tasks
def test_stateful_task():
    """Test StatefulTask state management."""
    task = CounterTask()
    task.setup()
    
    # Execute multiple times
    count1 = task.execute(1.0)
    count2 = task.execute(2.0)
    count3 = task.execute(3.0)
    
    assert count1 == 1
    assert count2 == 2
    assert count3 == 3


def test_stateful_task_state_methods():
    """Test StatefulTask get/set state methods."""
    task = CounterTask()
    task.setup()
    
    task.set_state("test_key", "test_value")
    value = task.get_state("test_key")
    
    assert value == "test_value"


def test_stateful_task_clear_state():
    """Test StatefulTask clear state."""
    task = CounterTask()
    task.setup()
    
    task.set_state("key1", "value1")
    task.set_state("key2", "value2")
    
    task.clear_state()
    
    assert task.get_state("key1") is None
    assert task.get_state("key2") is None


def test_stateful_task_teardown_clears_state():
    """Test that teardown clears state."""
    task = CounterTask()
    task.setup()
    
    task.execute(1.0)
    task.execute(2.0)
    
    assert task.get_state("count") == 2
    
    task.tear_down()
    
    assert task.get_state("count") is None


# Test Edge Cases
def test_get_last_result_before_execution():
    """Test get_last_result() when task hasn't been executed."""
    task = SimpleTask()
    
    result = task.get_last_result()
    
    assert result.value is None
    assert result.success is False
    assert "not been executed" in result.error_message


def test_execute_without_setup():
    """Test that execute works even without setup (with warning)."""
    task = SimpleTask()
    # Deliberately skip setup()
    
    result = task.execute(5.0)
    
    # Should still work, just logs a warning
    assert result == 10.0


def test_task_str_representation():
    """Test task string representation."""
    task = SimpleTask()
    task.setup()
    
    # Before execution
    str_before = str(task)
    assert "SimpleTask" in str_before
    assert "Not executed" in str_before
    
    # After execution
    task.execute(5.0)
    str_after = str(task)
    assert "SimpleTask" in str_after
    assert "10.0" in str_after


def test_task_repr():
    """Test task repr."""
    task = SimpleTask()
    repr_str = repr(task)
    
    assert "SimpleTask" in repr_str
    assert "0x" in repr_str  # Memory address


# Test Type Safety
def test_task_result_metadata():
    """Test TaskResult metadata field."""
    result = TaskResult(
        value=42.0,
        execution_time_ms=10.0,
        metadata={"input_size": 100, "algorithm": "v2"}
    )
    
    assert result.metadata["input_size"] == 100
    assert result.metadata["algorithm"] == "v2"


def test_stateful_task_default_value():
    """Test StatefulTask get_state with default."""
    task = CounterTask()
    task.setup()
    
    # Key doesn't exist, should return default
    value = task.get_state("nonexistent", "default_value")
    
    assert value == "default_value"
