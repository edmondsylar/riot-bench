"""
Tests for task registry functionality.

Tests cover:
- Task registration via decorator
- Task registration via direct call
- Task lookup by name
- Task creation (factory pattern)
- Registry enumeration
- Error handling
"""

import pytest
from typing import Any

from pyriotbench.core.task import BaseTask
from pyriotbench.core.registry import (
    TaskRegistry,
    register_task,
    get_task,
    create_task,
    list_tasks
)


class DummyTask(BaseTask):
    """Simple task for testing."""
    
    def do_task(self, input_data: Any) -> Any:
        return input_data


class AnotherTask(BaseTask):
    """Another task for testing."""
    
    def do_task(self, input_data: Any) -> Any:
        return input_data * 2


# Fixture to clear registry before each test
@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry before each test."""
    TaskRegistry.clear()
    yield
    TaskRegistry.clear()


# Test Registration
def test_register_task_manually():
    """Test manual task registration."""
    TaskRegistry.register("dummy", DummyTask)
    
    assert TaskRegistry.is_registered("dummy")
    assert TaskRegistry.count() == 1


def test_register_via_decorator():
    """Test registration via @register_task decorator."""
    # Register a task using the decorator
    @register_task("decorated-task")
    class DecoratedTask(BaseTask):
        """Task registered via decorator."""
        
        def do_task(self, input_data: Any) -> Any:
            return input_data + 1
    
    assert TaskRegistry.is_registered("decorated-task")
    
    task_class = TaskRegistry.get("decorated-task")
    assert task_class == DecoratedTask


def test_register_multiple_tasks():
    """Test registering multiple tasks."""
    TaskRegistry.register("task1", DummyTask)
    TaskRegistry.register("task2", AnotherTask)
    
    assert TaskRegistry.count() == 2
    assert TaskRegistry.is_registered("task1")
    assert TaskRegistry.is_registered("task2")


def test_register_duplicate_name_warning():
    """Test registering duplicate name logs warning but replaces."""
    TaskRegistry.register("duplicate", DummyTask)
    TaskRegistry.register("duplicate", AnotherTask)
    
    # Should replace with second task
    task_class = TaskRegistry.get("duplicate")
    assert task_class == AnotherTask
    assert TaskRegistry.count() == 1


def test_register_empty_name_raises():
    """Test that empty name raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        TaskRegistry.register("", DummyTask)


def test_register_invalid_class_raises():
    """Test that non-BaseTask class raises ValueError."""
    class NotATask:
        pass
    
    with pytest.raises(ValueError, match="must inherit from BaseTask"):
        TaskRegistry.register("invalid", NotATask)  # type: ignore


# Test Lookup
def test_get_task_by_name():
    """Test getting task by name."""
    TaskRegistry.register("test-task", DummyTask)
    
    task_class = TaskRegistry.get("test-task")
    
    assert task_class == DummyTask


def test_get_nonexistent_task_returns_none():
    """Test getting non-existent task returns None."""
    task_class = TaskRegistry.get("nonexistent")
    
    assert task_class is None


def test_get_or_raise_success():
    """Test get_or_raise with existing task."""
    TaskRegistry.register("test-task", DummyTask)
    
    task_class = TaskRegistry.get_or_raise("test-task")
    
    assert task_class == DummyTask


def test_get_or_raise_failure():
    """Test get_or_raise with non-existent task raises KeyError."""
    with pytest.raises(KeyError, match="not found in registry"):
        TaskRegistry.get_or_raise("nonexistent")


def test_get_or_raise_shows_available_tasks():
    """Test that error message shows available tasks."""
    TaskRegistry.register("task1", DummyTask)
    TaskRegistry.register("task2", AnotherTask)
    
    with pytest.raises(KeyError, match="task1, task2"):
        TaskRegistry.get_or_raise("nonexistent")


# Test Task Creation (Factory)
def test_create_task_instance():
    """Test creating task instance via factory."""
    TaskRegistry.register("test-task", DummyTask)
    
    task = TaskRegistry.create("test-task")
    
    assert isinstance(task, DummyTask)
    assert isinstance(task, BaseTask)


def test_create_nonexistent_task_raises():
    """Test creating non-existent task raises KeyError."""
    with pytest.raises(KeyError):
        TaskRegistry.create("nonexistent")


def test_create_task_with_args():
    """Test creating task with constructor arguments."""
    
    class TaskWithArgs(BaseTask):
        def __init__(self, multiplier: int):
            super().__init__()
            self.multiplier = multiplier
        
        def do_task(self, input_data: float) -> float:
            return input_data * self.multiplier
    
    TaskRegistry.register("task-with-args", TaskWithArgs)
    
    task = TaskRegistry.create("task-with-args", 5)
    
    assert task.multiplier == 5


def test_create_task_with_kwargs():
    """Test creating task with keyword arguments."""
    
    class TaskWithKwargs(BaseTask):
        def __init__(self, multiplier: int = 1, offset: int = 0):
            super().__init__()
            self.multiplier = multiplier
            self.offset = offset
        
        def do_task(self, input_data: float) -> float:
            return input_data * self.multiplier + self.offset
    
    TaskRegistry.register("task-with-kwargs", TaskWithKwargs)
    
    task = TaskRegistry.create("task-with-kwargs", multiplier=3, offset=10)
    
    assert task.multiplier == 3
    assert task.offset == 10


# Test Enumeration
def test_list_tasks_empty():
    """Test listing tasks when registry is empty."""
    tasks = TaskRegistry.list_tasks()
    
    assert tasks == []


def test_list_tasks():
    """Test listing all registered tasks."""
    TaskRegistry.register("task-a", DummyTask)
    TaskRegistry.register("task-b", AnotherTask)
    TaskRegistry.register("task-c", DummyTask)
    
    tasks = TaskRegistry.list_tasks()
    
    # Should be sorted
    assert tasks == ["task-a", "task-b", "task-c"]


def test_is_registered():
    """Test checking if task is registered."""
    TaskRegistry.register("test-task", DummyTask)
    
    assert TaskRegistry.is_registered("test-task")
    assert not TaskRegistry.is_registered("nonexistent")


def test_count():
    """Test counting registered tasks."""
    assert TaskRegistry.count() == 0
    
    TaskRegistry.register("task1", DummyTask)
    assert TaskRegistry.count() == 1
    
    TaskRegistry.register("task2", AnotherTask)
    assert TaskRegistry.count() == 2


# Test Convenience Functions
def test_get_task_function():
    """Test get_task convenience function."""
    TaskRegistry.register("test-task", DummyTask)
    
    task_class = get_task("test-task")
    
    assert task_class == DummyTask


def test_create_task_function():
    """Test create_task convenience function."""
    TaskRegistry.register("test-task", DummyTask)
    
    task = create_task("test-task")
    
    assert isinstance(task, DummyTask)


def test_list_tasks_function():
    """Test list_tasks convenience function."""
    TaskRegistry.register("task-a", DummyTask)
    TaskRegistry.register("task-b", AnotherTask)
    
    tasks = list_tasks()
    
    assert tasks == ["task-a", "task-b"]


# Test Decorator Function
def test_register_task_decorator_returns_class():
    """Test that decorator returns the original class."""
    
    @register_task("test-decorator")
    class TestTask(BaseTask):
        def do_task(self, input_data: Any) -> Any:
            return input_data
    
    # Decorator should return the class unchanged
    assert TestTask.__name__ == "TestTask"
    
    # But it should be registered
    assert TaskRegistry.is_registered("test-decorator")
    assert TaskRegistry.get("test-decorator") == TestTask


def test_register_task_decorator_with_instantiation():
    """Test that decorated class can be instantiated directly."""
    
    @register_task("instant-task")
    class InstantTask(BaseTask):
        def do_task(self, input_data: Any) -> Any:
            return input_data + 10
    
    # Should be able to create instance directly
    task1 = InstantTask()
    task1.setup()
    result1 = task1.execute(5)
    assert result1 == 15
    
    # Should also be able to create via registry
    task2 = TaskRegistry.create("instant-task")
    task2.setup()
    result2 = task2.execute(5)
    assert result2 == 15


# Test Clear (for testing)
def test_clear_registry():
    """Test clearing registry."""
    TaskRegistry.register("task1", DummyTask)
    TaskRegistry.register("task2", AnotherTask)
    
    assert TaskRegistry.count() == 2
    
    TaskRegistry.clear()
    
    assert TaskRegistry.count() == 0
    assert not TaskRegistry.is_registered("task1")
    assert not TaskRegistry.is_registered("task2")


# Integration Test
def test_full_workflow():
    """Test complete workflow: register, list, create, execute."""
    
    @register_task("workflow-task")
    class WorkflowTask(BaseTask):
        def do_task(self, input_data: float) -> float:
            return input_data ** 2
    
    # List available tasks
    tasks = TaskRegistry.list_tasks()
    assert "workflow-task" in tasks
    
    # Create instance
    task = TaskRegistry.create("workflow-task")
    assert isinstance(task, WorkflowTask)
    
    # Execute
    task.setup()
    result = task.execute(5.0)
    assert result == 25.0
    
    # Check result
    last_result = task.get_last_result()
    assert last_result.success is True
    assert last_result.value == 25.0
    
    # Teardown
    task.tear_down()
