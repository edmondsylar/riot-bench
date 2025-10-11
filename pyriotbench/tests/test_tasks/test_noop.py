"""Tests for NoOpTask benchmark.

This module tests the NoOperation task implementation, which serves as:
- Baseline for performance measurement
- Framework overhead calculation
- Infrastructure validation test
- Template example for other tasks
"""

import pytest
import logging
from typing import Any

from pyriotbench.core import TaskRegistry, create_task, TaskMetrics, MetricsAggregator


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
    
    def test_setup_with_logger(self):
        """Test setup works (logger is created automatically)."""
        task = NoOpTask()
        
        # Should not raise
        task.setup()
        assert task._logger is not None
        task.tear_down()
    
    def test_setup_with_config(self):
        """Test setup works (even though NoOp doesn't use config)."""
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
        
        output = task.execute(42)
        assert output == 42, "Should pass through integer unchanged"
        
        # Get timing from last result
        result = task.get_last_result()
        assert result.execution_time_ms > 0, "Should have execution time"
        assert result.success, "Should be successful"
        
        task.tear_down()
    
    def test_pass_through_string(self):
        """Test passing through a string."""
        task = NoOpTask()
        task.setup()
        
        output = task.execute("hello world")
        assert output == "hello world", "Should pass through string unchanged"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_pass_through_float(self):
        """Test passing through a float."""
        task = NoOpTask()
        task.setup()
        
        output = task.execute(3.14159)
        assert output == 3.14159, "Should pass through float unchanged"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_pass_through_list(self):
        """Test passing through a list."""
        task = NoOpTask()
        task.setup()
        
        input_list = [1, 2, 3, 4, 5]
        output = task.execute(input_list)
        assert output == input_list, "Should pass through list unchanged"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_pass_through_dict_without_value_key(self):
        """Test passing through dict without 'value' key."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {"sensor": "temperature", "reading": 23.5}
        output = task.execute(input_dict)
        assert output == input_dict, "Should pass through dict unchanged"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_extract_value_from_dict(self):
        """Test extracting 'value' key from dict."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {"value": 123}
        output = task.execute(input_dict)
        assert output == 123, "Should extract 'value' field from dict"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_extract_value_with_other_keys(self):
        """Test extracting 'value' when dict has multiple keys."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {"sensor": "temp", "value": 42, "unit": "celsius"}
        output = task.execute(input_dict)
        assert output == 42, "Should extract 'value' field, ignoring other keys"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_pass_through_none(self):
        """Test passing through None."""
        task = NoOpTask()
        task.setup()
        
        output = task.execute(None)
        assert output is None, "Should pass through None unchanged"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_pass_through_boolean(self):
        """Test passing through boolean values."""
        task = NoOpTask()
        task.setup()
        
        output = task.execute(True)
        assert output is True, "Should pass through True unchanged"
        
        result1 = task.get_last_result()
        assert result1.execution_time_ms > 0
        assert result1.success
        
        output = task.execute(False)
        assert output is False, "Should pass through False unchanged"
        
        result2 = task.get_last_result()
        assert result2.execution_time_ms > 0
        assert result2.success
        
        task.tear_down()


class TestNoOpTaskTiming:
    """Test NoOpTask timing and metrics."""
    
    def test_execution_is_timed(self):
        """Test that execution time is recorded."""
        task = NoOpTask()
        task.setup()
        
        output = task.execute(100)
        assert output == 100, "Should have correct output"
        
        # TaskResult should have timing
        result = task.get_last_result()
        assert result.execution_time_ms > 0, "Should have positive execution time"
        assert result.value == 100, "Result value should match output"
        assert result.success, "Should be successful"
        
        task.tear_down()
    
    def test_execution_is_fast(self):
        """Test that NoOp execution is very fast (< 1000ms)."""
        task = NoOpTask()
        task.setup()
        
        output = task.execute(42)
        result = task.get_last_result()
        
        # NoOp should be extremely fast (under 1 second = 1000ms)
        assert result.execution_time_ms < 1000, "NoOp should execute in under 1 second"
        
        task.tear_down()
    
    def test_result_has_metadata(self):
        """Test that TaskResult contains metadata."""
        task = NoOpTask()
        task.setup()
        
        output = task.execute(999)
        result = task.get_last_result()
        
        assert result.metadata is not None, "Should have metadata"
        # Metadata content depends on BaseTask implementation
        
        task.tear_down()
    
    def test_multiple_executions(self):
        """Test multiple sequential executions."""
        task = NoOpTask()
        task.setup()
        
        values = [10, 20, 30, 40, 50]
        outputs = [task.execute(v) for v in values]
        
        # All should have correct outputs
        for i, output in enumerate(outputs):
            assert output == values[i], f"Output {i} should match input"
        
        # Last result should be available
        result = task.get_last_result()
        assert result.execution_time_ms > 0, "Last result should have timing"
        assert result.success, "Last result should be successful"
        
        task.tear_down()


class TestNoOpTaskMetrics:
    """Test NoOpTask metrics integration."""
    
    def test_can_create_metrics_from_result(self):
        """Test creating TaskMetrics from execution result."""
        task = NoOpTask()
        task.setup()
        
        output = task.execute(100)
        result = task.get_last_result()
        
        # Create metric from result (converting ms to μs)
        metric = TaskMetrics(
            task_name="noop",
            execution_time_us=result.execution_time_ms * 1000,  # Convert ms to μs
            status="success",
            metadata=result.metadata
        )
        
        assert metric.task_name == "noop"
        assert metric.is_success
        assert metric.execution_time_us > 0
        
        task.tear_down()
    
    def test_metrics_aggregation(self):
        """Test aggregating metrics from multiple executions."""
        task = NoOpTask()
        task.setup()
        
        # Collect metrics
        aggregator = MetricsAggregator("noop")
        
        for i in range(20):
            output = task.execute(i)
            result = task.get_last_result()
            
            metric = TaskMetrics(
                task_name="noop",
                execution_time_us=result.execution_time_ms * 1000,  # Convert ms to μs
                status="success"
            )
            aggregator.add(metric)
        
        # Verify aggregated metrics
        assert aggregator.count == 20
        assert aggregator.success_count == 20
        assert aggregator.error_count == 0
        assert aggregator.success_rate == 1.0
        assert aggregator.mean_time_us > 0
        
        task.tear_down()


class TestNoOpTaskEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_dict(self):
        """Test passing empty dict."""
        task = NoOpTask()
        task.setup()
        
        output = task.execute({})
        assert output == {}, "Should pass through empty dict"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_nested_dict_with_value(self):
        """Test dict with nested 'value' key."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {
            "value": {"nested": "data"},
            "other": "field"
        }
        output = task.execute(input_dict)
        
        # Should extract the value, even if it's a dict
        assert output == {"nested": "data"}, "Should extract nested value"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_value_is_none(self):
        """Test dict where 'value' is None."""
        task = NoOpTask()
        task.setup()
        
        input_dict = {"value": None, "other": "data"}
        output = task.execute(input_dict)
        
        assert output is None, "Should extract None value correctly"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        task.tear_down()
    
    def test_very_large_input(self):
        """Test with large input data."""
        task = NoOpTask()
        task.setup()
        
        large_list = list(range(10000))
        output = task.execute(large_list)
        
        assert output == large_list, "Should handle large data"
        assert len(output) == 10000, "Should preserve all elements"
        
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
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


class TestNoOpIntegration:
    """End-to-end integration tests."""
    
    def test_complete_workflow(self):
        """Test complete workflow: registry -> task -> execution -> metrics."""
        # Create via registry
        task = create_task("noop")
        assert isinstance(task, NoOpTask)
        
        # Setup
        task.setup()
        
        # Execute
        output = task.execute({"value": 42})
        assert output == 42
        
        # Get result
        result = task.get_last_result()
        assert result.execution_time_ms > 0
        assert result.success
        
        # Create metrics from result
        metric = TaskMetrics(
            task_name="noop",
            execution_time_us=result.execution_time_ms * 1000,  # Convert ms to μs
            status="success",
            metadata=result.metadata
        )
        
        assert metric.task_name == "noop"
        assert metric.is_success
        
        # Cleanup
        task.tear_down()
    
    def test_multiple_tasks_independent(self):
        """Test creating multiple NoOp tasks independently."""
        # Create two separate instances
        task1 = create_task("noop")
        task2 = create_task("noop")
        
        task1.setup()
        task2.setup()
        
        # Execute both
        output1 = task1.execute(100)
        output2 = task2.execute(200)
        
        # Both should work independently
        assert output1 == 100
        assert output2 == 200
        
        task1.tear_down()
        task2.tear_down()
    
    def test_metrics_collection_workflow(self):
        """Test collecting metrics from multiple NoOp executions."""
        task = create_task("noop")
        task.setup()
        
        # Collect metrics
        aggregator = MetricsAggregator("noop")
        
        for i in range(50):
            output = task.execute(i)
            result = task.get_last_result()
            
            metric = TaskMetrics(
                task_name="noop",
                execution_time_us=result.execution_time_ms * 1000,  # Convert ms to μs
                status="success"
            )
            aggregator.add(metric)
        
        # Verify aggregated metrics
        assert aggregator.count == 50
        assert aggregator.success_count == 50
        assert aggregator.error_count == 0
        assert aggregator.success_rate == 1.0
        assert aggregator.mean_time_us > 0
        assert aggregator.min_time_us > 0
        
        task.tear_down()
