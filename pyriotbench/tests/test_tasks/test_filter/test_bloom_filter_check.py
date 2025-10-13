"""
Tests for BloomFilterCheck task.

Tests cover:
- Task registration
- Setup and initialization
- Membership testing (true positives)
- Non-membership testing (true negatives)
- Field extraction from CSV
- Random mode testing
- Thread safety
- Error handling
"""

import threading

import pytest

from pyriotbench.core.registry import TaskRegistry
from pyriotbench.tasks.filter.bloom_filter_check import BloomFilterCheck


class TestBloomFilterCheckRegistration:
    """Test task registration and discovery."""
    
    def test_task_is_registered(self):
        """Test that BloomFilterCheck is registered."""
        assert TaskRegistry.is_registered("bloom_filter_check")
    
    def test_can_get_task_class(self):
        """Test retrieving task class from registry."""
        task_cls = TaskRegistry.get("bloom_filter_check")
        assert task_cls is BloomFilterCheck
    
    def test_can_create_task_instance(self):
        """Test creating task instance."""
        task = TaskRegistry.create("bloom_filter_check")
        assert isinstance(task, BloomFilterCheck)


class TestBloomFilterCheckSetup:
    """Test setup and initialization."""
    
    def test_setup_loads_model(self, bloom_filter_config):
        """Test that setup loads bloom filter model."""
        config, _ = bloom_filter_config
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        assert BloomFilterCheck._bloom_filter is not None
        assert BloomFilterCheck._setup_done is True
    
    def test_setup_without_config_raises_error(self):
        """Test that setup without config raises error."""
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = {}
        
        with pytest.raises(ValueError, match="MODEL_PATH not configured"):
            task.setup()
    
    def test_setup_with_invalid_path_raises_error(self):
        """Test that setup with invalid path raises error."""
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = {
            'FILTER.BLOOM_FILTER.MODEL_PATH': '/nonexistent/path/model.pkl'
        }
        
        with pytest.raises(FileNotFoundError):
            task.setup()
    
    def test_setup_only_once_with_multiple_instances(self, bloom_filter_config):
        """Test that setup is only executed once even with multiple instances."""
        config, _ = bloom_filter_config
        
        # Reset class state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task1 = BloomFilterCheck()
        task1.config = config
        task1.setup()
        
        filter_ref = BloomFilterCheck._bloom_filter
        
        task2 = BloomFilterCheck()
        task2.config = config
        task2.setup()
        
        # Should be the same bloom filter instance
        assert BloomFilterCheck._bloom_filter is filter_ref


class TestBloomFilterCheckMembership:
    """Test bloom filter membership checking."""
    
    def test_check_known_member(self, bloom_filter_config):
        """Test checking value that is in the bloom filter."""
        config, test_values = bloom_filter_config
        config['FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD'] = 1  # Use first field
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        # Test with known value
        result = task.do_task("sensor_001,42.5,normal")
        assert result == 1.0  # Should be found
    
    def test_check_known_non_member(self, bloom_filter_config):
        """Test checking value that is not in the bloom filter."""
        config, test_values = bloom_filter_config
        config['FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD'] = 1
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        # Test with unknown value
        result = task.do_task("unknown_sensor,42.5,normal")
        assert result == 0.0  # Should not be found
    
    def test_check_multiple_values(self, bloom_filter_config):
        """Test checking multiple values."""
        config, test_values = bloom_filter_config
        config['FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD'] = 1
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        # Test known values (should be found)
        for value in test_values[:3]:
            result = task.do_task(f"{value},42.5,normal")
            assert result == 1.0, f"Expected {value} to be found"


class TestBloomFilterCheckFieldExtraction:
    """Test CSV field extraction."""
    
    def test_extract_first_field(self, bloom_filter_config, sample_csv_data):
        """Test extracting first field from CSV."""
        config, _ = bloom_filter_config
        config['FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD'] = 1
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        result = task.do_task(sample_csv_data[0])
        assert result in (0.0, 1.0)  # Valid result
    
    def test_extract_second_field(self, bloom_filter_config):
        """Test extracting second field from CSV."""
        config, _ = bloom_filter_config
        config['FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD'] = 2
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        result = task.do_task("sensor_001,temperature,normal")
        assert result == 1.0  # "temperature" is in test values
    
    def test_field_index_out_of_range(self, bloom_filter_config):
        """Test field index out of range returns error."""
        config, _ = bloom_filter_config
        config['FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD'] = 10  # Too high
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        result = task.do_task("sensor_001,42.5")
        assert result == float('-inf')  # Error sentinel


class TestBloomFilterCheckRandomMode:
    """Test random value generation mode."""
    
    def test_random_mode(self, bloom_filter_config):
        """Test random mode generates values."""
        config, _ = bloom_filter_config
        config['FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD'] = 0  # Random mode
        config['FILTER.BLOOM_FILTER_CHECK.TESTING_RANGE'] = 100
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        # Run multiple times - should produce valid results
        results = []
        for _ in range(10):
            result = task.do_task("ignored_input")
            assert result in (0.0, 1.0)
            results.append(result)
        
        # With random values, we should get at least one 0.0 (not found)
        # given the small testing range
        assert 0.0 in results


class TestBloomFilterCheckExecution:
    """Test full execution with timing."""
    
    def test_execute_records_timing(self, bloom_filter_config):
        """Test that execute records timing metrics."""
        config, test_values = bloom_filter_config
        config['FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD'] = 1
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        result_value = task.execute(f"{test_values[0]},42.5,normal")
        result = task.get_last_result()
        
        assert result_value in (0.0, 1.0)
        assert result.value in (0.0, 1.0)
        assert result.execution_time_ms > 0
        assert result.success is True
    
    def test_execute_with_error(self, bloom_filter_config):
        """Test execute with error condition."""
        config, _ = bloom_filter_config
        config['FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD'] = 10
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        result_value = task.execute("short,csv")
        result = task.get_last_result()
        
        assert result_value == float('-inf')
        assert result.value == float('-inf')
        assert result.success is True  # Success=True because do_task returned normally


class TestBloomFilterCheckThreadSafety:
    """Test thread safety of setup."""
    
    def test_concurrent_setup(self, bloom_filter_config):
        """Test that concurrent setup is thread-safe."""
        config, _ = bloom_filter_config
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        results = []
        errors = []
        
        def setup_task():
            try:
                task = BloomFilterCheck()
                task.config = config
                task.setup()
                results.append(BloomFilterCheck._bloom_filter)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=setup_task) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have no errors
        assert len(errors) == 0
        
        # All results should reference the same bloom filter
        assert len(set(id(bf) for bf in results)) == 1


class TestBloomFilterCheckTearDown:
    """Test teardown and cleanup."""
    
    def test_tear_down(self, bloom_filter_config):
        """Test tear_down completes without error."""
        config, _ = bloom_filter_config
        
        # Reset state
        BloomFilterCheck._setup_done = False
        BloomFilterCheck._bloom_filter = None
        
        task = BloomFilterCheck()
        task.config = config
        task.setup()
        
        # Should not raise
        task.tear_down()
