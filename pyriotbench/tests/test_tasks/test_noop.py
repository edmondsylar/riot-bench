"""Tests for NoOpTask benchmark.

This module tests the NoOperation task implementation, which serves as:
- Baseline for performance measurement
- Framework overhead calculation
- Infrastructure validation test
- Template example for other tasks
"""

import pytest
import time
from typing import Any

from pyriotbench.core import TaskRegistry, create_task


# Import to ensure task is registered
import pyriotbench.tasks.noop
from pyriotbench.tasks.noop import NoOpTask


@pytest.fixture(autouse=True)
def ensure_noop_registered():
    """Ensure NoOpTask is registered before each test."""
    if not TaskRegistry.is_registered("noop"):
        # Re-register if registry was cleared
        TaskRegistry.register("noop", NoOpTask)
    yield


class TestNoOpTaskRegistration:
    """Test NoOpTask registration in TaskRegistry."""
    
    def test_noop_is_registered(self):
        """Test that NoOpTask is registered with correct name."""
        assert TaskRegistry.is_registered("noop"), "NoOpTask should be registered as 'noop'"
    
    def test_noop_get_task_class(self):
        """Test retrieving NoOpTask class from registry."""
        task_class = TaskRegistry.get("noop")
        assert task_class is not None, "Should retrieve NoOpTask class"
        assert task_class is NoOpTask, "Should retrieve correct class"
    
    def test_noop_in_task_list(self):
        """Test that 'noop' appears in task listing."""
        tasks = TaskRegistry.list_tasks()
        assert "noop" in tasks, "'noop' should be in task list"
    
    def test_noop_create_task(self):
        """Test creating NoOpTask via factory function."""
        task = create_task("noop")
        assert task is not None, "Should create task instance"
        assert isinstance(task, NoOpTask), "Should create correct type"


class TestNoOpTaskLifecycle:
    """Test NoOpTask setup, execution, and teardown lifecycle."""
    
    def test_setup_and_teardown(self):
        """Test basic setup and teardown."""
        task = NoOpTask()
        
        # Should not raise
        task.setup()
        task.tear_down()
    
    def test_setup_with_logger(self, caplog):
        """Test setup logs initialization."""
        import logging
        
        # Set up logging to capture
        logger = logging.getLogger("NoOpTask")
        logger.setLevel(logging.INFO)
        
        task = NoOpTask()
        task.setup()
        
        # Should log initialization message
        messages = [record.message for record in caplog.records]
        assert any("initialized" in msg.lower() for msg in messages), \
            "Should log initialization"
        
        task.tear_down()
    
    def test_setup_with_config(self):
        """Test setup works (no config needed for NoOp)."""
        task = NoOpTask()
        
        # Should not raise even though NoOp doesn't use config
        task.setup()
        task.tear_down()
    
    def test_multiple_setup_calls(self):
        """Test that multiple setup calls don't cause issues."""
        task = NoOpTask()
        
        task.setup()
        task.setup()  # Second call
        
        task.tear_down()


class TestNoOpTaskExecution:
    """Test NoOpTask execution behavior."""
    
    def test_pass_through_integer(self):
        """Test passing through an integer."""
        task = NoOpTask()
        task.setup()
        
        result = task.execute(42)
        assert result == 42, "Should pass through integer unchanged"
        
        task.tear_down()
    
    def test_pass_through_string(self):
        """Test passing through a string."""
        task = NoOpTask()
        task.setup()
        
        result = task.execute("hello world")
        assert result == "hello world", "Should pass through string unchanged"
        
        task.tear_down()
    
    def test_pass_through_float(self):
        """Test passing through a float."""
        task = NoOpTask()
        task.setup()
        
        result = task.execute(3.14159)
        assert result == 3.14159, "Should pass through float unchanged"
        
        task.tear_down()
    
    def test_pass_through_list(self):
        """Test passing through a list."""
        task = NoOpTask()
        task.setup()
        
        input_list = [1, 2, 3, 4, 5]
        result = task.execute(input_list)
        assert result == input_list, "Should pass through list unchanged"
        
        task.tear_down()
    
    def test_pass_through_dict_without_value_key(self):
        """Test passing through dict without 'value' key."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {"sensor": "temperature", "reading": 23.5}
        result = task.execute(input_dict)
        assert result == input_dict, "Should pass through dict unchanged"
        
        task.tear_down()
    
    def test_extract_value_from_dict(self):
        """Test extracting 'value' key from dict."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {"value": 123}
        result = task.execute(input_dict)
        assert result == 123, "Should extract 'value' field from dict"
        
        task.tear_down()
    
    def test_extract_value_with_other_keys(self):
        """Test extracting 'value' when dict has multiple keys."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {"sensor": "temp", "value": 42, "unit": "celsius"}
        result = task.execute(input_dict)
        assert result == 42, "Should extract 'value' field, ignoring other keys"
        
        task.tear_down()
    
    def test_pass_through_none(self):
        """Test passing through None."""
        task = NoOpTask()
        task.setup()
        
        result = task.execute(None)
        assert result is None, "Should pass through None unchanged"
        
        task.tear_down()
    
    def test_pass_through_boolean(self):
        """Test passing through boolean values."""
        task = NoOpTask()
        task.setup()
        
        result = task.execute(True)
        assert result is True, "Should pass through True unchanged"
        
        result = task.execute(False)
        assert result is False, "Should pass through False unchanged"
        
        task.tear_down()


class TestNoOpTaskTiming:
    """Test NoOpTask timing and metrics."""
    
    def test_execution_is_timed(self):
        """Test that execution time is recorded."""
        task = NoOpTask()
        task.setup()
        
        task.execute(100)
        result = task.get_last_result()
        
        assert result.success, "Execution should be successful"
        assert result.execution_time_ms >= 0, "Should have non-negative execution time"
        
        task.tear_down()
    
    def test_execution_is_fast(self):
        """Test that NoOp execution is very fast (< 1ms)."""
        task = NoOpTask()
        task.setup()
        
        task.execute(42)
        result = task.get_last_result()
        
        # NoOp should be extremely fast
        assert result.execution_time_ms < 1.0, "NoOp should execute in under 1ms"
        
        task.tear_down()
    
    def test_last_result_stores_value(self):
        """Test that get_last_result() returns correct value."""
        task = NoOpTask()
        task.setup()
        
        task.execute(999)
        result = task.get_last_result()
        
        assert result.value == 999, "Should store correct result value"
        
        task.tear_down()
    
    def test_execution_count_increments(self):
        """Test that execution increments properly."""
        task = NoOpTask()
        task.setup()
        
        # Execute multiple times
        task.execute(1)
        task.execute(2)
        task.execute(3)
        
        # Should have executed successfully each time
        result = task.get_last_result()
        assert result.success, "Should track successful executions"
        
        task.tear_down()
    
    def test_multiple_executions(self):
        """Test multiple sequential executions."""
        task = NoOpTask()
        task.setup()
        
        values = [10, 20, 30, 40, 50]
        results = [task.execute(v) for v in values]
        
        assert results == values, "All executions should pass through correctly"
        
        task.tear_down()


class TestNoOpTaskMetrics:
    """Test NoOpTask metrics integration."""
    
    def test_metrics_success_status(self):
        """Test that successful execution sets correct status."""
        task = NoOpTask()
        task.setup()
        
        task.execute(100)
        result = task.get_last_result()
        
        assert result.success, "Status should indicate success"
        assert result.value == 100, "Should store correct value"
        
        task.tear_down()
    
    def test_metrics_value_stored(self):
        """Test that metrics contain correct value."""
        task = NoOpTask()
        task.setup()
        
        task.execute(42)
        result = task.get_last_result()
        
        assert result.value == 42, "Value should be stored correctly"
        
        task.tear_down()
    
    def test_metrics_execution_time(self):
        """Test that execution time is recorded."""
        task = NoOpTask()
        task.setup()
        
        task.execute(123)
        result = task.get_last_result()
        
        assert result.execution_time_ms >= 0, "Should have non-negative execution time"
        assert result.execution_time_ms < 10.0, "NoOp should be very fast (< 10ms)"
        
        task.tear_down()
    
    def test_teardown_logs_statistics(self, caplog):
        """Test that teardown logs completion."""
        import logging
        logger = logging.getLogger("NoOpTask")
        logger.setLevel(logging.INFO)
        
        task = NoOpTask()
        task.setup()
        
        # Execute multiple times
        for i in range(5):
            task.execute(i)
        
        task.tear_down()
        
        # Should log completion
        messages = [record.message for record in caplog.records]
        assert any("complete" in msg.lower() for msg in messages), \
            "Should log completion on teardown"


class TestNoOpTaskEdgeCases:
    """Test edge cases and error handling."""
    
    def test_execute_before_setup(self):
        """Test executing without calling setup first."""
        task = NoOpTask()
        
        # Should still work (setup is idempotent via parent class)
        result = task.execute(42)
        assert result == 42, "Should work even without explicit setup"
    
    def test_empty_dict(self):
        """Test passing empty dict."""
        task = NoOpTask()
        task.setup()
        
        result = task.execute({})
        assert result == {}, "Should pass through empty dict"
        
        task.tear_down()
    
    def test_nested_dict_with_value(self):
        """Test dict with nested 'value' key."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {
            "value": {"nested": "data"},
            "other": "field"
        }
        result = task.execute(input_dict)
        
        # Should extract the value, even if it's a dict
        assert result == {"nested": "data"}, "Should extract nested value"
        
        task.tear_down()
    
    def test_value_is_none(self):
        """Test dict where 'value' is None."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {"value": None, "other": "data"}
        result = task.execute(input_dict)
        
        assert result is None, "Should extract None value correctly"
        
        task.tear_down()
    
    def test_very_large_input(self):
        """Test with very large input data."""
        task = NoOpTask()
        task.setup()
        
        large_list = list(range(100000))
        result = task.execute(large_list)
        
        assert result == large_list, "Should handle large data"
        assert len(result) == 100000, "Should preserve all elements"
        
        task.tear_down()


class TestNoOpTaskAsTemplate:
    """Test that NoOpTask serves as good template for other tasks."""
    
    def test_has_proper_docstring(self):
        """Test that NoOpTask has comprehensive docstring."""
        assert NoOpTask.__doc__ is not None, "Should have class docstring"
        assert len(NoOpTask.__doc__) > 100, "Should have detailed docstring"
        assert "baseline" in NoOpTask.__doc__.lower(), "Should mention baseline use"
    
    def test_methods_have_docstrings(self):
        """Test that all methods have docstrings."""
        assert NoOpTask.setup.__doc__ is not None, "setup() should have docstring"
        assert NoOpTask.do_task.__doc__ is not None, "do_task() should have docstring"
        assert NoOpTask.tear_down.__doc__ is not None, "tear_down() should have docstring"
    
    def test_follows_basetask_pattern(self):
        """Test that NoOpTask follows BaseTask pattern correctly."""
        from pyriotbench.core import BaseTask
        
        assert issubclass(NoOpTask, BaseTask), "Should inherit from BaseTask"
        
        # Should implement required abstract method
        assert hasattr(NoOpTask, 'do_task'), "Should implement do_task()"
        assert callable(getattr(NoOpTask, 'do_task')), "do_task() should be callable"
