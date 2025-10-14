"""
Tests for Flink adapter - FlinkTaskMapFunction.
"""

import pytest
from unittest.mock import Mock, patch

from pyriotbench.platforms.flink.adapter import FlinkTaskMapFunction
from pyriotbench.core.registry import TaskRegistry


class TestFlinkTaskMapFunction:
    """Test suite for FlinkTaskMapFunction adapter."""
    
    def test_init_valid_task(self):
        """Test initialization with valid task."""
        map_fn = FlinkTaskMapFunction('noop')
        assert map_fn.task_name == 'noop'
        assert map_fn.config == {}
        assert map_fn.task is None  # Not created until open()
    
    def test_init_with_config(self):
        """Test initialization with configuration."""
        config = {'key': 'value'}
        map_fn = FlinkTaskMapFunction('noop', config)
        assert map_fn.task_name == 'noop'
        assert map_fn.config == config
    
    def test_init_invalid_task(self):
        """Test initialization with unregistered task raises ValueError."""
        with pytest.raises(ValueError, match="not registered"):
            FlinkTaskMapFunction('nonexistent_task')
    
    def test_open_creates_task(self):
        """Test open() creates task instance and calls setup()."""
        map_fn = FlinkTaskMapFunction('noop')
        
        # Mock runtime context
        runtime_context = Mock()
        runtime_context.get_index_of_this_subtask.return_value = 0
        
        # Call open
        map_fn.open(runtime_context)
        
        # Verify task was created and setup called
        assert map_fn.task is not None
        assert map_fn.task.__class__.__name__ == 'NoOpTask'
        assert map_fn._start_time is not None
    
    def test_map_processes_data(self):
        """Test map() executes task on input."""
        map_fn = FlinkTaskMapFunction('noop')
        
        # Initialize task
        runtime_context = Mock()
        runtime_context.get_index_of_this_subtask.return_value = 0
        map_fn.open(runtime_context)
        
        # Process data
        result = map_fn.map("test_input")
        
        # Verify
        assert result == "test_input"  # NoOp passes through
        assert map_fn._record_count == 1
        assert map_fn._error_count == 0
    
    def test_map_multiple_records(self):
        """Test processing multiple records."""
        map_fn = FlinkTaskMapFunction('noop')
        
        runtime_context = Mock()
        runtime_context.get_index_of_this_subtask.return_value = 0
        map_fn.open(runtime_context)
        
        # Process multiple records
        for i in range(10):
            result = map_fn.map(f"record_{i}")
            assert result == f"record_{i}"
        
        assert map_fn._record_count == 10
        assert map_fn._error_count == 0
    
    def test_map_handles_errors(self):
        """Test error handling in map()."""
        map_fn = FlinkTaskMapFunction('noop')
        
        runtime_context = Mock()
        runtime_context.get_index_of_this_subtask.return_value = 0
        map_fn.open(runtime_context)
        
        # Mock task to raise error
        map_fn.task.execute = Mock(side_effect=ValueError("Test error"))
        
        # Process should return None on error
        result = map_fn.map("bad_input")
        assert result is None
        assert map_fn._error_count == 1
    
    def test_map_without_open(self):
        """Test map() without calling open() first."""
        map_fn = FlinkTaskMapFunction('noop')
        
        # map() should handle gracefully
        result = map_fn.map("test")
        assert result is None
    
    def test_close_cleanup(self):
        """Test close() tears down task."""
        map_fn = FlinkTaskMapFunction('noop')
        
        runtime_context = Mock()
        runtime_context.get_index_of_this_subtask.return_value = 0
        map_fn.open(runtime_context)
        
        # Process some data
        map_fn.map("data1")
        map_fn.map("data2")
        
        # Close should succeed
        map_fn.close()
        
        # Verify metrics were logged (no exception)
        assert map_fn._record_count == 2
    
    def test_close_without_open(self):
        """Test close() without open() is safe."""
        map_fn = FlinkTaskMapFunction('noop')
        map_fn.close()  # Should not raise
    
    def test_repr(self):
        """Test string representation."""
        config = {'key': 'value'}
        map_fn = FlinkTaskMapFunction('noop', config)
        repr_str = repr(map_fn)
        assert 'FlinkTaskMapFunction' in repr_str
        assert 'noop' in repr_str
        assert 'key' in repr_str


class TestFlinkTaskMapFunctionWithKalmanFilter:
    """Test FlinkTaskMapFunction with stateful Kalman filter."""
    
    def test_kalman_filter_processing(self):
        """Test Kalman filter maintains state across records."""
        config = {
            'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
            'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
            'STATISTICS.KALMAN_FILTER.INITIAL_ESTIMATE': 25.0,
            'STATISTICS.KALMAN_FILTER.INITIAL_ERROR': 1.0
        }
        
        map_fn = FlinkTaskMapFunction('kalman_filter', config)
        
        runtime_context = Mock()
        runtime_context.get_index_of_this_subtask.return_value = 0
        map_fn.open(runtime_context)
        
        # Process sequence
        measurements = ['25.0', '26.5', '24.8', '25.2', '26.0']
        results = [map_fn.map(m) for m in measurements]
        
        # Verify all processed
        assert len(results) == 5
        assert all(r is not None for r in results)
        
        # Kalman filter outputs floats - just verify they're numeric
        for r in results:
            assert isinstance(r, (int, float))
        
        map_fn.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
