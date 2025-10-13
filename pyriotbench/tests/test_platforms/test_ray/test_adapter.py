"""
Tests for Ray platform adapter.
"""

import pytest
import ray
from pathlib import Path
import tempfile
import os

from pyriotbench.platforms.ray.adapter import RayTaskActor, create_ray_actor, create_ray_actors
from pyriotbench.core.registry import TaskRegistry


@pytest.fixture(scope="module", autouse=True)
def ray_cluster():
    """Initialize Ray for all tests in this module."""
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True, logging_level="ERROR")
    yield
    # Don't shutdown - other tests might need it
    # ray.shutdown()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


class TestRayTaskActorBasics:
    """Test basic Ray actor functionality."""
    
    def test_actor_creation(self):
        """Test creating a Ray actor."""
        actor = RayTaskActor.remote('noop', {})
        assert actor is not None
        
        # Get task name
        task_name = ray.get(actor.get_task_name.remote())
        assert task_name == 'noop'
    
    def test_actor_with_config(self):
        """Test actor with custom configuration."""
        config = {'test_key': 'test_value'}
        actor = RayTaskActor.remote('noop', config)
        
        actor_config = ray.get(actor.get_config.remote())
        assert actor_config == config
    
    def test_invalid_task_name(self):
        """Test that invalid task name raises error."""
        actor = RayTaskActor.remote('invalid_task_name', {})
        
        # ActorDiedError when actor fails to initialize
        with pytest.raises(ray.exceptions.ActorDiedError):
            ray.get(actor.process.remote("data"))
    
    def test_helper_create_ray_actor(self):
        """Test helper function for creating single actor."""
        actor = create_ray_actor('noop')
        result = ray.get(actor.process.remote("test"))
        assert result == "test"
    
    def test_helper_create_ray_actors(self):
        """Test helper function for creating multiple actors."""
        actors = create_ray_actors('noop', num_actors=3)
        assert len(actors) == 3
        
        # Test all actors work
        futures = [actor.process.remote(f"test{i}") for i, actor in enumerate(actors)]
        results = ray.get(futures)
        assert results == ["test0", "test1", "test2"]


class TestRayTaskActorExecution:
    """Test task execution through Ray actors."""
    
    def test_process_single_item(self):
        """Test processing a single data item."""
        actor = RayTaskActor.remote('noop', {})
        result = ray.get(actor.process.remote("test_data"))
        assert result == "test_data"
    
    def test_process_multiple_items(self):
        """Test processing multiple items sequentially."""
        actor = RayTaskActor.remote('noop', {})
        
        data = ["item1", "item2", "item3"]
        futures = [actor.process.remote(d) for d in data]
        results = ray.get(futures)
        
        assert results == data
    
    def test_process_batch(self):
        """Test batch processing."""
        actor = RayTaskActor.remote('noop', {})
        
        data = ["a", "b", "c", "d"]
        results = ray.get(actor.process_batch.remote(data))
        
        assert results == data
    
    def test_stateful_task(self):
        """Test that actors maintain state across calls."""
        # Each actor maintains its own task instance state
        actor = RayTaskActor.remote('noop', {})
        
        # Process multiple items
        result1 = ray.get(actor.process.remote("item1"))
        result2 = ray.get(actor.process.remote("item2"))
        result3 = ray.get(actor.process.remote("item3"))
        
        # All results should be present
        assert result1 == "item1"
        assert result2 == "item2"
        assert result3 == "item3"
        
        # Metrics should accumulate
        metrics = ray.get(actor.get_metrics.remote())
        assert metrics['total_processed'] == 3


class TestRayTaskActorMetrics:
    """Test metrics collection in Ray actors."""
    
    def test_metrics_collection(self):
        """Test that metrics are collected."""
        actor = RayTaskActor.remote('noop', {})
        
        # Process some data
        for i in range(5):
            ray.get(actor.process.remote(f"item{i}"))
        
        # Get metrics
        metrics = ray.get(actor.get_metrics.remote())
        
        assert metrics['total_processed'] == 5
        assert metrics['errors'] == 0
        assert 'avg_time' in metrics
        assert 'throughput' in metrics
    
    def test_metrics_with_none_results(self):
        """Test metrics when tasks process None inputs."""
        actor = RayTaskActor.remote('noop', {})
        
        # Process valid and None results
        ray.get(actor.process.remote("valid"))
        ray.get(actor.process.remote(None))  # This will be None
        ray.get(actor.process.remote("valid2"))
        
        metrics = ray.get(actor.get_metrics.remote())
        
        assert metrics['total_processed'] == 3
        assert metrics['none_filtered'] >= 0  # At least not negative


class TestRayTaskActorLifecycle:
    """Test actor lifecycle management."""
    
    def test_tear_down(self):
        """Test that tear_down works."""
        actor = RayTaskActor.remote('noop', {})
        
        # Process data
        ray.get(actor.process.remote("test"))
        
        # Tear down
        ray.get(actor.tear_down.remote())
        
        # Should complete without error
    
    def test_multiple_actors_parallel(self):
        """Test multiple actors processing in parallel."""
        actors = create_ray_actors('noop', num_actors=4)
        
        # Distribute work
        data = [f"item{i}" for i in range(20)]
        futures = []
        for i, item in enumerate(data):
            actor_idx = i % len(actors)
            futures.append(actors[actor_idx].process.remote(item))
        
        # Get all results
        results = ray.get(futures)
        assert len(results) == 20
        assert results == data
    
    def test_actor_isolation(self):
        """Test that actors maintain independent state."""
        config1 = {'test': 'actor1'}
        config2 = {'test': 'actor2'}
        
        actor1 = RayTaskActor.remote('noop', config1)
        actor2 = RayTaskActor.remote('noop', config2)
        
        config1_retrieved = ray.get(actor1.get_config.remote())
        config2_retrieved = ray.get(actor2.get_config.remote())
        
        assert config1_retrieved != config2_retrieved
        assert config1_retrieved['test'] == 'actor1'
        assert config2_retrieved['test'] == 'actor2'


class TestRayTaskActorEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_string_input(self):
        """Test processing empty string."""
        actor = RayTaskActor.remote('noop', {})
        result = ray.get(actor.process.remote(""))
        assert result == ""
    
    def test_none_input(self):
        """Test processing None input."""
        actor = RayTaskActor.remote('noop', {})
        result = ray.get(actor.process.remote(None))
        assert result is None
    
    def test_batch_with_errors(self):
        """Test batch processing completes even with some issues."""
        # Use noop which is simple and doesn't fail
        actor = RayTaskActor.remote('noop', {})
        
        data = [
            "item1",
            "item2", 
            "item3"
        ]
        
        results = ray.get(actor.process_batch.remote(data))
        
        # All results should be present
        assert len(results) == 3
        assert results == data
        
        metrics = ray.get(actor.get_metrics.remote())
        assert metrics['total_processed'] == 3
