"""
Task registry for dynamic task discovery and instantiation.

This module provides a centralized registry for benchmark tasks, enabling:
- Automatic task discovery via decorator
- Dynamic task loading by name
- Task enumeration for CLI/UI
- Factory pattern without boilerplate

The registry eliminates the need for manual factory classes and switch statements,
making it easy to add new benchmarks without modifying core code.

Usage:
    # Register a task
    @register_task("my-benchmark")
    class MyBenchmark(BaseTask):
        pass
    
    # Get task by name
    task_class = TaskRegistry.get("my-benchmark")
    task = task_class()
    
    # List all tasks
    for name in TaskRegistry.list_tasks():
        print(name)
"""

from typing import Dict, Type, Optional, Callable, List, Any
from pyriotbench.core.task import BaseTask
import logging

logger = logging.getLogger(__name__)


class TaskRegistry:
    """
    Singleton registry for benchmark tasks.
    
    Provides centralized storage and lookup for all registered tasks.
    Tasks are registered either via @register_task decorator or manually.
    
    Thread Safety:
        This implementation is NOT thread-safe. Registration should happen
        during module import time (single-threaded by Python's import system).
        Lookup operations are thread-safe (dict reads are atomic in CPython).
    
    Design Pattern:
        Singleton + Registry + Factory
        - Singleton: One global registry
        - Registry: Central storage for tasks
        - Factory: Creates task instances by name
    """
    
    # Class-level storage (singleton pattern)
    _tasks: Dict[str, Type[BaseTask]] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, name: str, task_class: Type[BaseTask]) -> None:
        """
        Register a task class with a given name.
        
        Args:
            name: Unique identifier for the task (e.g., "bloom-filter")
            task_class: The task class (must inherit from BaseTask)
            
        Raises:
            ValueError: If name is already registered or task_class is invalid
            
        Example:
            TaskRegistry.register("my-task", MyTaskClass)
        """
        if not name:
            raise ValueError("Task name cannot be empty")
        
        if not isinstance(task_class, type) or not issubclass(task_class, BaseTask):
            raise ValueError(
                f"Task class must inherit from BaseTask, got {task_class}"
            )
        
        if name in cls._tasks:
            existing = cls._tasks[name]
            if existing != task_class:
                logger.warning(
                    f"Task '{name}' already registered as {existing.__name__}, "
                    f"replacing with {task_class.__name__}"
                )
        
        cls._tasks[name] = task_class
        logger.debug(f"Registered task: {name} -> {task_class.__name__}")
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseTask]]:
        """
        Get a task class by name.
        
        Args:
            name: Task identifier (e.g., "bloom-filter")
            
        Returns:
            Task class if found, None otherwise
            
        Example:
            task_class = TaskRegistry.get("bloom-filter")
            if task_class:
                task = task_class()
        """
        return cls._tasks.get(name)
    
    @classmethod
    def get_or_raise(cls, name: str) -> Type[BaseTask]:
        """
        Get a task class by name, raising an exception if not found.
        
        Args:
            name: Task identifier
            
        Returns:
            Task class
            
        Raises:
            KeyError: If task is not registered
            
        Example:
            task_class = TaskRegistry.get_or_raise("bloom-filter")
            task = task_class()
        """
        task_class = cls._tasks.get(name)
        if task_class is None:
            available = ", ".join(cls.list_tasks())
            raise KeyError(
                f"Task '{name}' not found in registry. "
                f"Available tasks: {available or 'none'}"
            )
        return task_class
    
    @classmethod
    def list_tasks(cls) -> List[str]:
        """
        Get list of all registered task names.
        
        Returns:
            Sorted list of task names
            
        Example:
            for task_name in TaskRegistry.list_tasks():
                print(f"Available: {task_name}")
        """
        return sorted(cls._tasks.keys())
    
    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered tasks.
        
        Useful for testing. Not intended for production use.
        """
        cls._tasks.clear()
        logger.debug("Task registry cleared")
    
    @classmethod
    def count(cls) -> int:
        """
        Get the number of registered tasks.
        
        Returns:
            Number of tasks in registry
        """
        return len(cls._tasks)
    
    @classmethod
    def create(cls, name: str, *args: Any, **kwargs: Any) -> BaseTask:
        """
        Factory method: get task class and instantiate it.
        
        Args:
            name: Task identifier
            *args: Positional arguments for task constructor
            **kwargs: Keyword arguments for task constructor
            
        Returns:
            Instantiated task
            
        Raises:
            KeyError: If task not found
            
        Example:
            task = TaskRegistry.create("bloom-filter", config=my_config)
            task.setup()
            result = task.execute(data)
        """
        task_class = cls.get_or_raise(name)
        return task_class(*args, **kwargs)
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a task name is registered.
        
        Args:
            name: Task identifier
            
        Returns:
            True if task is registered, False otherwise
        """
        return name in cls._tasks


def register_task(name: str) -> Callable[[Type[BaseTask]], Type[BaseTask]]:
    """
    Decorator to automatically register a task class.
    
    This is the preferred way to register tasks - just add the decorator
    to your task class and it will be automatically available in the registry.
    
    Args:
        name: Unique identifier for the task
        
    Returns:
        Decorator function
        
    Example:
        @register_task("bloom-filter")
        class BloomFilterTask(BaseTask):
            def do_task(self, input_data):
                # Implementation
                pass
        
        # Task is now available:
        task = TaskRegistry.create("bloom-filter")
    
    Notes:
        - The task module must be imported for registration to occur
        - Import happens during module load, before main() execution
        - Use lazy imports if you have heavy dependencies
    """
    def decorator(task_class: Type[BaseTask]) -> Type[BaseTask]:
        TaskRegistry.register(name, task_class)
        return task_class
    
    return decorator


# Aliases for convenience
register = register_task
get_task = TaskRegistry.get
create_task = TaskRegistry.create
list_tasks = TaskRegistry.list_tasks
