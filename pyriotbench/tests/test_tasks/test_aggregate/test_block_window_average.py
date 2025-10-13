"""
Tests for Block Window Average Task.

Comprehensive tests for windowed aggregation including:
- Basic windowing logic
- Multi-sensor support
- Window reset behavior
- Edge cases
- Thread safety
"""

import threading
import pytest

from pyriotbench.tasks.aggregate.block_window_average import BlockWindowAverage
from pyriotbench.core.registry import TaskRegistry


class TestBlockWindowAverageRegistration:
    """Tests for task registration."""
    
    def test_task_registered(self):
        """Test that block_window_average is registered."""
        assert TaskRegistry.is_registered('block_window_average')
    
    def test_task_instantiation(self):
        """Test task can be instantiated from registry."""
        task_class = TaskRegistry.get('block_window_average')
        assert task_class is not None
        
        task = task_class()
        assert isinstance(task, BlockWindowAverage)


class TestBlockWindowAverageSetup:
    """Tests for setup and configuration."""
    
    def test_setup_with_defaults(self):
        """Test setup with default configuration."""
        task = BlockWindowAverage()
        task.config = {}
        task.setup()
        
        assert task._window_size == 10  # Default
        assert task._use_msg_field == 0
        assert task._sensor_id_field == 0
        assert task.windows is not None
    
    def test_setup_with_custom_config(self, window_config):
        """Test setup with custom configuration."""
        # Reset state
        BlockWindowAverage._setup_done = False
        
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        assert task._window_size == 3
        assert task._use_msg_field == 0
        assert task._sensor_id_field == 0
    
    def test_setup_thread_safety(self, window_config):
        """Test setup is thread-safe."""
        # Reset state
        BlockWindowAverage._setup_done = False
        
        tasks = [BlockWindowAverage() for _ in range(5)]
        for t in tasks:
            t.config = window_config
        
        threads = [threading.Thread(target=t.setup) for t in tasks]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All tasks should have same class config
        for task in tasks:
            assert task._window_size == 3


class TestBlockWindowAverageBasicWindowing:
    """Tests for basic windowing logic."""
    
    def test_accumulate_until_full(self, window_config):
        """Test window accumulation (no output until full)."""
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        # Window size is 3
        value1 = task.execute("10.0")
        assert value1 is None  # 1/3
        
        value2 = task.execute("20.0")
        assert value2 is None  # 2/3
        
        value3 = task.execute("30.0")
        assert value3 == 20.0  # 3/3 -> average = (10+20+30)/3 = 20
    
    def test_window_reset_after_emission(self, window_config):
        """Test window resets after emitting average."""
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        # First window
        task.execute("10.0")
        task.execute("20.0")
        value = task.execute("30.0")
        assert value == 20.0
        
        # Second window (should start fresh)
        task.execute("40.0")
        task.execute("50.0")
        value = task.execute("60.0")
        assert value == 50.0  # (40+50+60)/3 = 50
    
    def test_multiple_windows(self, temperature_stream):
        """Test multiple consecutive windows."""
        task = BlockWindowAverage()
        task.config = {'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 3}
        task.setup()
        
        values = [task.execute(value) for value in temperature_stream]
        
        # Extract non-None outputs
        averages = [v for v in values if v is not None]
        
        # Should have 3 averages (9 values / 3 window size)
        assert len(averages) == 3
        
        # Check expected averages (with reasonable tolerance for floating point)
        assert abs(averages[0] - 22.8) < 0.01  # (22.5+23.1+22.8)/3
        assert abs(averages[1] - 23.17) < 0.01  # (23.4+22.9+23.2)/3 = 23.1666...
        assert abs(averages[2] - 23.0) < 0.01  # (23.0+22.7+23.3)/3


class TestBlockWindowAverageFieldExtraction:
    """Tests for CSV field extraction."""
    
    def test_single_field_input(self, window_config):
        """Test with single field (no CSV)."""
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        task.execute("100.0")
        task.execute("200.0")
        value = task.execute("300.0")
        
        assert value == 200.0
    
    def test_multi_field_extraction(self, multi_field_config):
        """Test extracting specific field from CSV."""
        task = BlockWindowAverage()
        task.config = multi_field_config
        task.setup()
        
        # Window size is 5, extract field 2 (second field)
        task.execute("timestamp,25.0")
        task.execute("timestamp,26.0")
        task.execute("timestamp,27.0")
        task.execute("timestamp,28.0")
        value = task.execute("timestamp,29.0")
        
        assert value == 27.0  # (25+26+27+28+29)/5
    
    def test_last_field_when_no_field_specified(self):
        """Test using last field when no field specified."""
        task = BlockWindowAverage()
        task.config = {
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 2,
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD': 0,  # Not specified
        }
        task.setup()
        
        task.execute("10.0,20.0,30.0")  # Should use 30.0
        value = task.execute("40.0,50.0,60.0")  # Should use 60.0
        
        assert value == 45.0  # (30+60)/2


class TestBlockWindowAverageMultiSensor:
    """Tests for multi-sensor support."""
    
    def test_independent_windows(self, multi_sensor_config):
        """Test each sensor has independent window."""
        task = BlockWindowAverage()
        task.config = multi_sensor_config
        task.setup()
        
        # Interleave sensors
        task.execute("sensor_001,10.0")  # Sensor 1: 1/3
        task.execute("sensor_002,100.0")  # Sensor 2: 1/3
        task.execute("sensor_001,20.0")  # Sensor 1: 2/3
        task.execute("sensor_002,200.0")  # Sensor 2: 2/3
        v1 = task.execute("sensor_001,30.0")  # Sensor 1: 3/3 -> emit
        v2 = task.execute("sensor_002,300.0")  # Sensor 2: 3/3 -> emit
        
        # Check sensor averages
        assert v1 == 20.0  # (10+20+30)/3
        assert v2 == 200.0  # (100+200+300)/3
    
    def test_multiple_sensor_windows(self, sensor_data):
        """Test multiple sensors complete their windows."""
        task = BlockWindowAverage()
        task.config = {
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 3,
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD': 2,
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.SENSOR_ID_FIELD': 1,
        }
        task.setup()
        
        results = []
        for data in sensor_data:
            value = task.execute(data)
            if value is not None:
                results.append(value)
        
        # Should have 2 averages (one per sensor)
        assert len(results) == 2
        assert results[0] == 26.0  # Sensor 1: (25+26+27)/3
        assert results[1] == 31.0  # Sensor 2: (30+31+32)/3
    
    def test_get_window_state(self, multi_sensor_config):
        """Test window state inspection."""
        task = BlockWindowAverage()
        task.config = multi_sensor_config
        task.setup()
        
        task.execute("sensor_001,10.0")
        task.execute("sensor_002,100.0")
        task.execute("sensor_001,20.0")
        
        state = task.get_window_state()
        assert state['sensor_001'] == 2
        assert state['sensor_002'] == 1


class TestBlockWindowAverageEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_input(self, window_config):
        """Test handling empty string."""
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        value = task.execute("")
        assert value == float('-inf')
    
    def test_invalid_numeric_value(self, window_config):
        """Test handling non-numeric value."""
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        value = task.execute("not_a_number")
        assert value == float('-inf')
    
    def test_missing_field(self):
        """Test handling missing field."""
        task = BlockWindowAverage()
        task.config = {
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 2,
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD': 5,  # Field doesn't exist
        }
        task.setup()
        
        value = task.execute("10.0,20.0")  # Only 2 fields
        assert value == float('-inf')
    
    def test_single_value_window(self):
        """Test window size of 1."""
        task = BlockWindowAverage()
        task.config = {'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 1}
        task.setup()
        
        value = task.execute("42.0")
        assert value == 42.0  # Immediate output
    
    def test_negative_values(self, window_config):
        """Test with negative values."""
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        task.execute("-10.0")
        task.execute("-20.0")
        value = task.execute("-30.0")
        
        assert value == -20.0  # (-10-20-30)/3 = -20
    
    def test_float_precision(self, window_config):
        """Test floating point precision."""
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        task.execute("0.1")
        task.execute("0.2")
        value = task.execute("0.3")
        
        assert abs(value - 0.2) < 1e-10


class TestBlockWindowAverageExecution:
    """Tests for execute() method and metrics."""
    
    def test_execution_timing(self, window_config):
        """Test that execution timing is recorded."""
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        value = task.execute("10.0")
        result = task.get_last_result()
        
        assert result.execution_time_ms > 0
        assert value is None  # Window not full
    
    def test_execution_with_no_output(self, window_config):
        """Test execution returns None when window not full."""
        task = BlockWindowAverage()
        task.config = window_config
        task.setup()
        
        value = task.execute("10.0")  # 1/3
        result = task.get_last_result()
        
        assert value is None
        assert result.success is True
        assert result.execution_time_ms > 0


class TestBlockWindowAverageThreadSafety:
    """Tests for thread safety."""
    
    def test_concurrent_setup(self, window_config):
        """Test concurrent setup calls."""
        # Reset state
        BlockWindowAverage._setup_done = False
        
        tasks = [BlockWindowAverage() for _ in range(10)]
        for t in tasks:
            t.config = window_config
        
        def setup_task(task):
            task.setup()
        
        threads = [threading.Thread(target=setup_task, args=(t,)) for t in tasks]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All should be set up correctly
        for task in tasks:
            assert task._window_size == 3
    
    def test_concurrent_execution(self, window_config):
        """Test concurrent execution with separate task instances."""
        task1 = BlockWindowAverage()
        task1.config = window_config
        task1.setup()
        
        task2 = BlockWindowAverage()
        task2.config = window_config
        task2.setup()
        
        results1 = []
        results2 = []
        
        def execute_stream(task, results):
            for value in ["10.0", "20.0", "30.0"]:
                result_value = task.execute(value)
                if result_value is not None:
                    results.append(result_value)
        
        t1 = threading.Thread(target=execute_stream, args=(task1, results1))
        t2 = threading.Thread(target=execute_stream, args=(task2, results2))
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # Both should produce same average
        assert results1 == [20.0]
        assert results2 == [20.0]


class TestBlockWindowAverageTearDown:
    """Tests for cleanup."""
    
    def test_tear_down_clears_windows(self, multi_sensor_config):
        """Test tear_down clears all windows."""
        task = BlockWindowAverage()
        task.config = multi_sensor_config
        task.setup()
        
        # Accumulate some values
        task.execute("sensor_001,10.0")
        task.execute("sensor_002,100.0")
        
        assert len(task.windows) > 0
        
        task.tear_down()
        
        assert len(task.windows) == 0
    
    def test_tear_down_reset(self, window_config):
        """Test task can be reused after tear_down."""
        task = BlockWindowAverage()
        task.config = window_config
        
        # First run
        task.setup()
        task.execute("10.0")
        task.tear_down()
        
        # Second run
        task.setup()
        task.execute("100.0")
        task.execute("200.0")
        value = task.execute("300.0")
        
        assert value == 200.0  # Fresh window
