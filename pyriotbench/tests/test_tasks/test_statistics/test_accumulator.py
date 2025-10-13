"""
Tests for Accumulator task.
"""

import pytest
from pyriotbench.tasks.statistics.accumulator import Accumulator


@pytest.fixture
def accumulator_task():
    """Create accumulator task with default config."""
    task = Accumulator()
    task.config = {
        'AGGREGATE.ACCUMULATOR.TUPLE_WINDOW_SIZE': 3,
        'AGGREGATE.ACCUMULATOR.MULTIVALUE_OBSTYPE': '',
        'AGGREGATE.ACCUMULATOR.META_TIMESTAMP_FIELD': 0,
    }
    task.setup()
    return task


@pytest.fixture
def accumulator_multivalue():
    """Create accumulator task with multi-value config."""
    task = Accumulator()
    task.config = {
        'AGGREGATE.ACCUMULATOR.TUPLE_WINDOW_SIZE': 5,
        'AGGREGATE.ACCUMULATOR.MULTIVALUE_OBSTYPE': 'SLR,MULTI',
        'AGGREGATE.ACCUMULATOR.META_TIMESTAMP_FIELD': 0,
    }
    task.setup()
    return task


class TestAccumulatorBasics:
    """Test basic accumulator functionality."""
    
    def test_task_registration(self):
        """Test accumulator is registered."""
        from pyriotbench.core.registry import TaskRegistry
        assert TaskRegistry.is_registered('accumulator')
        task = TaskRegistry.create('accumulator')
        task.config = {}
        assert isinstance(task, Accumulator)
    
    def test_setup(self, accumulator_task):
        """Test setup configures window size."""
        assert accumulator_task.counter == 0
        assert len(accumulator_task.values_map) == 0
        assert accumulator_task._tuple_window_size == 3
    
    def test_initial_state(self, accumulator_task):
        """Test initial state before any data."""
        assert accumulator_task.get_current_count() == 0
        assert accumulator_task.get_accumulated_keys() == []


class TestSingleValueAccumulation:
    """Test accumulation with single-value observations."""
    
    def test_accumulate_one_tuple(self, accumulator_task):
        """Test accumulating single tuple returns None."""
        data = {
            'SENSORID': 'sensor_001',
            'OBSTYPE': 'TEMP',
            'OBSVALUE': '25.5',
            'META': '1234567890,location1',
            'TS': '1234567890',
        }
        result = accumulator_task.execute(data)
        assert result is None
        assert accumulator_task.get_current_count() == 1
    
    def test_accumulate_partial_window(self, accumulator_task):
        """Test accumulating partial window (2/3) returns None."""
        for i in range(2):
            data = {
                'SENSORID': 'sensor_001',
                'OBSTYPE': 'TEMP',
                'OBSVALUE': f'{20.0 + i}',
                'META': f'{1234567890 + i},location1',
                'TS': f'{1234567890 + i}',
            }
            result = accumulator_task.execute(data)
            assert result is None
        
        assert accumulator_task.get_current_count() == 2
    
    def test_accumulate_full_window(self, accumulator_task):
        """Test accumulating full window emits data."""
        # Accumulate 3 tuples
        for i in range(3):
            data = {
                'SENSORID': 'sensor_001',
                'OBSTYPE': 'TEMP',
                'OBSVALUE': f'{20.0 + i}',
                'META': f'{1234567890 + i},location1',
                'TS': f'{1234567890 + i}',
            }
            result = accumulator_task.execute(data)
            if i < 2:
                assert result is None
            else:
                # Window full on 3rd tuple
                assert result is not None
                assert isinstance(result, dict)
        
        # Check structure
        assert 'sensor_001TEMP' in result
        assert 'location1' in result['sensor_001TEMP']
        assert len(result['sensor_001TEMP']['location1']) == 3
        
        # Check values
        values = result['sensor_001TEMP']['location1']
        assert values[0][0] == '20.0'
        assert values[1][0] == '21.0'
        assert values[2][0] == '22.0'
        
        # Check counter reset
        assert accumulator_task.get_current_count() == 0
    
    def test_multiple_windows(self, accumulator_task):
        """Test multiple consecutive windows."""
        windows_emitted = 0
        
        # Send 9 tuples (should emit 3 windows)
        for i in range(9):
            data = {
                'SENSORID': 'sensor_001',
                'OBSTYPE': 'TEMP',
                'OBSVALUE': f'{i}',
                'META': f'{i},location1',
                'TS': f'{i}',
            }
            result = accumulator_task.execute(data)
            if result is not None:
                windows_emitted += 1
                # Each window should have 3 values
                assert len(result['sensor_001TEMP']['location1']) == 3
        
        assert windows_emitted == 3


class TestMultipleSensors:
    """Test accumulation with multiple sensors."""
    
    def test_multiple_sensors_same_obstype(self, accumulator_task):
        """Test accumulating from multiple sensors with same observation type."""
        # Send data from 3 different sensors
        sensors = ['sensor_001', 'sensor_002', 'sensor_003']
        for sensor in sensors:
            data = {
                'SENSORID': sensor,
                'OBSTYPE': 'TEMP',
                'OBSVALUE': '25.0',
                'META': '1234567890,location1',
                'TS': '1234567890',
            }
            result = accumulator_task.execute(data)
            if sensor != sensors[-1]:
                assert result is None
        
        # Window full on 3rd tuple
        assert result is not None
        
        # Should have 3 different composite keys
        assert len(result) == 3
        assert 'sensor_001TEMP' in result
        assert 'sensor_002TEMP' in result
        assert 'sensor_003TEMP' in result
    
    def test_multiple_obstypes_same_sensor(self, accumulator_task):
        """Test accumulating multiple observation types from same sensor."""
        obstypes = ['TEMP', 'HUM', 'PRESSURE']
        for obstype in obstypes:
            data = {
                'SENSORID': 'sensor_001',
                'OBSTYPE': obstype,
                'OBSVALUE': '25.0',
                'META': '1234567890,location1',
                'TS': '1234567890',
            }
            result = accumulator_task.execute(data)
            if obstype != obstypes[-1]:
                assert result is None
        
        # Window full
        assert result is not None
        assert len(result) == 3
        assert 'sensor_001TEMP' in result
        assert 'sensor_001HUM' in result
        assert 'sensor_001PRESSURE' in result


class TestMultiValueObstype:
    """Test accumulation with multi-value observation types."""
    
    def test_multivalue_parsing(self, accumulator_multivalue):
        """Test parsing multi-value observation (SLR with # separator)."""
        # Send one multi-value tuple
        data = {
            'SENSORID': 'sensor_001',
            'OBSTYPE': 'SLR',
            'OBSVALUE': '1.5#2.3#3.1',
            'META': '1234567890,location1',
            'TS': '1234567890',
        }
        accumulator_multivalue.execute(data)
        
        # Check that 3 values were stored
        assert accumulator_multivalue.get_current_count() == 1  # Still 1 tuple
        values = accumulator_multivalue.values_map['sensor_001SLR']['location1']
        assert len(values) == 3
        assert values[0][0] == '1.5'
        assert values[1][0] == '2.3'
        assert values[2][0] == '3.1'
    
    def test_multivalue_full_window(self, accumulator_multivalue):
        """Test full window with multi-value observations."""
        # Send 5 tuples with multi-value data
        for i in range(5):
            data = {
                'SENSORID': 'sensor_001',
                'OBSTYPE': 'SLR',
                'OBSVALUE': f'{i}.1#{i}.2#{i}.3',
                'META': f'{1234567890 + i},location1',
                'TS': f'{1234567890 + i}',
            }
            result = accumulator_multivalue.execute(data)
            if i < 4:
                assert result is None
        
        # Window should be full
        assert result is not None
        values = result['sensor_001SLR']['location1']
        # 5 tuples * 3 values each = 15 values
        assert len(values) == 15
    
    def test_mixed_single_and_multivalue(self, accumulator_multivalue):
        """Test mixed single-value and multi-value observations."""
        data_items = [
            {'SENSORID': 's1', 'OBSTYPE': 'TEMP', 'OBSVALUE': '25.0', 'META': '1,l1', 'TS': '1'},
            {'SENSORID': 's1', 'OBSTYPE': 'SLR', 'OBSVALUE': '1.1#1.2', 'META': '2,l1', 'TS': '2'},
            {'SENSORID': 's1', 'OBSTYPE': 'HUM', 'OBSVALUE': '60.0', 'META': '3,l1', 'TS': '3'},
            {'SENSORID': 's1', 'OBSTYPE': 'MULTI', 'OBSVALUE': '2.1#2.2#2.3', 'META': '4,l1', 'TS': '4'},
            {'SENSORID': 's1', 'OBSTYPE': 'TEMP', 'OBSVALUE': '26.0', 'META': '5,l1', 'TS': '5'},
        ]
        
        for i, data in enumerate(data_items):
            result = accumulator_multivalue.execute(data)
            if i < 4:
                assert result is None
        
        # Check final window
        assert result is not None
        assert len(result) == 4  # TEMP, SLR, HUM, MULTI
        
        # Single-value observations
        assert len(result['s1TEMP']['l1']) == 2
        assert len(result['s1HUM']['l1']) == 1
        
        # Multi-value observations
        assert len(result['s1SLR']['l1']) == 2
        assert len(result['s1MULTI']['l1']) == 3


class TestMetadataHandling:
    """Test metadata and timestamp handling."""
    
    def test_timestamp_from_ts_field(self, accumulator_task):
        """Test using TS field for timestamp."""
        data = {
            'SENSORID': 'sensor_001',
            'OBSTYPE': 'TEMP',
            'OBSVALUE': '25.0',
            'META': 'location1',
            'TS': '1234567890',
        }
        accumulator_task.execute(data)
        
        values = accumulator_task.values_map['sensor_001TEMP']['location1']
        assert values[0][1] == '1234567890'
    
    def test_timestamp_from_meta_field(self, accumulator_task):
        """Test extracting timestamp from META field."""
        data = {
            'SENSORID': 'sensor_001',
            'OBSTYPE': 'TEMP',
            'OBSVALUE': '25.0',
            'META': '9876543210,location1',
            'TS': '',  # Empty TS, should extract from META
        }
        accumulator_task.execute(data)
        
        values = accumulator_task.values_map['sensor_001TEMP']['location1']
        # Should use timestamp from META field 0
        assert values[0][1] == '9876543210'
    
    def test_different_meta_keys(self, accumulator_task):
        """Test accumulating data with different meta keys."""
        # Send data with different locations (last field in META)
        locations = ['location1', 'location2', 'location3']
        for loc in locations:
            data = {
                'SENSORID': 'sensor_001',
                'OBSTYPE': 'TEMP',
                'OBSVALUE': '25.0',
                'META': f'1234567890,{loc}',
                'TS': '1234567890',
            }
            result = accumulator_task.execute(data)
            if loc != locations[-1]:
                assert result is None
        
        # Should have 3 different meta keys under same composite key
        assert result is not None
        assert len(result['sensor_001TEMP']) == 3
        assert 'location1' in result['sensor_001TEMP']
        assert 'location2' in result['sensor_001TEMP']
        assert 'location3' in result['sensor_001TEMP']


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_missing_sensorid(self, accumulator_task):
        """Test handling missing SENSORID."""
        data = {
            'OBSTYPE': 'TEMP',
            'OBSVALUE': '25.0',
            'META': '1234567890,location1',
            'TS': '1234567890',
        }
        result = accumulator_task.execute(data)
        assert result is None
        assert accumulator_task.get_current_count() == 0
    
    def test_missing_obstype(self, accumulator_task):
        """Test handling missing OBSTYPE."""
        data = {
            'SENSORID': 'sensor_001',
            'OBSVALUE': '25.0',
            'META': '1234567890,location1',
            'TS': '1234567890',
        }
        result = accumulator_task.execute(data)
        assert result is None
        assert accumulator_task.get_current_count() == 0
    
    def test_missing_obsvalue(self, accumulator_task):
        """Test handling missing OBSVALUE."""
        data = {
            'SENSORID': 'sensor_001',
            'OBSTYPE': 'TEMP',
            'META': '1234567890,location1',
            'TS': '1234567890',
        }
        result = accumulator_task.execute(data)
        assert result is None
        assert accumulator_task.get_current_count() == 0
    
    def test_string_input_not_supported(self, accumulator_task):
        """Test string input returns None."""
        result = accumulator_task.execute("sensor_001,TEMP,25.0")
        assert result is None
    
    def test_empty_meta(self, accumulator_task):
        """Test handling empty META field."""
        data = {
            'SENSORID': 'sensor_001',
            'OBSTYPE': 'TEMP',
            'OBSVALUE': '25.0',
            'META': '',
            'TS': '1234567890',
        }
        result = accumulator_task.execute(data)
        # Should use "default" as meta key
        assert accumulator_task.get_current_count() == 1
        assert 'default' in accumulator_task.values_map['sensor_001TEMP']


class TestStateManagement:
    """Test state management and cleanup."""
    
    def test_tear_down_clears_state(self, accumulator_task):
        """Test tear_down clears accumulated state."""
        # Accumulate some data
        data = {
            'SENSORID': 'sensor_001',
            'OBSTYPE': 'TEMP',
            'OBSVALUE': '25.0',
            'META': '1234567890,location1',
            'TS': '1234567890',
        }
        accumulator_task.execute(data)
        assert accumulator_task.get_current_count() == 1
        
        # Tear down
        accumulator_task.tear_down()
        assert accumulator_task.get_current_count() == 0
        assert len(accumulator_task.values_map) == 0
    
    def test_get_accumulated_keys(self, accumulator_task):
        """Test getting list of accumulated keys."""
        # Send data from different sensors
        data1 = {
            'SENSORID': 'sensor_001',
            'OBSTYPE': 'TEMP',
            'OBSVALUE': '25.0',
            'META': '1,l1',
            'TS': '1',
        }
        data2 = {
            'SENSORID': 'sensor_002',
            'OBSTYPE': 'HUM',
            'OBSVALUE': '60.0',
            'META': '2,l1',
            'TS': '2',
        }
        
        accumulator_task.execute(data1)
        accumulator_task.execute(data2)
        
        keys = accumulator_task.get_accumulated_keys()
        assert len(keys) == 2
        assert 'sensor_001TEMP' in keys
        assert 'sensor_002HUM' in keys


class TestConfiguration:
    """Test configuration options."""
    
    def test_custom_window_size(self):
        """Test custom window size configuration."""
        task = Accumulator()
        task.config = {
            'AGGREGATE.ACCUMULATOR.TUPLE_WINDOW_SIZE': 5,
            'AGGREGATE.ACCUMULATOR.MULTIVALUE_OBSTYPE': '',
            'AGGREGATE.ACCUMULATOR.META_TIMESTAMP_FIELD': 0,
        }
        task.setup()
        
        # Should require 5 tuples for full window
        for i in range(4):
            data = {
                'SENSORID': 's1',
                'OBSTYPE': 'TEMP',
                'OBSVALUE': f'{i}',
                'META': f'{i},l1',
                'TS': f'{i}',
            }
            result = task.execute(data)
            assert result is None
        
        # 5th tuple triggers emission
        data = {'SENSORID': 's1', 'OBSTYPE': 'TEMP', 'OBSVALUE': '4', 'META': '4,l1', 'TS': '4'}
        result = task.execute(data)
        assert result is not None
    
    def test_default_config(self):
        """Test default configuration values."""
        task = Accumulator()
        task.config = {}
        task.setup()
        
        # Should use defaults
        assert task._tuple_window_size == 10
        assert task._multivalue_obstype == []
        assert task._timestamp_field == 0
    
    def test_custom_timestamp_field(self):
        """Test custom timestamp field index."""
        task = Accumulator()
        task.config = {
            'AGGREGATE.ACCUMULATOR.TUPLE_WINDOW_SIZE': 3,
            'AGGREGATE.ACCUMULATOR.MULTIVALUE_OBSTYPE': '',
            'AGGREGATE.ACCUMULATOR.META_TIMESTAMP_FIELD': 1,  # Second field
        }
        task.setup()
        
        data = {
            'SENSORID': 's1',
            'OBSTYPE': 'TEMP',
            'OBSVALUE': '25.0',
            'META': 'location1,9999999999,extra',
            'TS': '',  # Empty, should use META field 1
        }
        task.execute(data)
        
        values = task.values_map['s1TEMP']['extra']
        assert values[0][1] == '9999999999'
