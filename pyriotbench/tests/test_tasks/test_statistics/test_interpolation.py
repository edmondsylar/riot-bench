"""
Tests for Interpolation task.
"""

import pytest
from pyriotbench.tasks.statistics.interpolation import Interpolation


@pytest.fixture
def interpolation_task():
    """Create interpolation task with default config."""
    task = Interpolation()
    task.config = {
        'STATISTICS.INTERPOLATION.USE_MSG_FIELD': 'TEMP,HUM',
        'STATISTICS.INTERPOLATION.WINDOW_SIZE': 3,
    }
    task.setup()
    return task


@pytest.fixture
def single_field_task():
    """Create interpolation task for single observation type."""
    task = Interpolation()
    task.config = {
        'STATISTICS.INTERPOLATION.USE_MSG_FIELD': 'TEMP',
        'STATISTICS.INTERPOLATION.WINDOW_SIZE': 5,
    }
    task.setup()
    return task


class TestInterpolationBasics:
    """Test basic interpolation functionality."""
    
    def test_task_registration(self):
        """Test interpolation is registered."""
        from pyriotbench.core.registry import TaskRegistry
        assert TaskRegistry.is_registered('interpolation')
        task = TaskRegistry.create('interpolation')
        task.config = {}
        assert isinstance(task, Interpolation)
    
    def test_setup(self, interpolation_task):
        """Test setup configures fields and window size."""
        assert 'TEMP' in interpolation_task._use_msg_field
        assert 'HUM' in interpolation_task._use_msg_field
        assert interpolation_task._window_size == 3
    
    def test_initial_state(self, interpolation_task):
        """Test initial state before any data."""
        assert len(interpolation_task.values_map) == 0
        assert interpolation_task.get_window_state() == {}


class TestBasicInterpolation:
    """Test basic interpolation scenarios."""
    
    def test_first_valid_value(self, interpolation_task):
        """Test adding first valid value creates window."""
        data = {'SENSORID': 's1', 'TEMP': '25.0'}
        result = interpolation_task.execute(data)
        
        assert result == 25.0
        assert 's1TEMP' in interpolation_task.values_map
        assert len(interpolation_task.values_map['s1TEMP']) == 1
    
    def test_build_window(self, interpolation_task):
        """Test building up window with multiple values."""
        values = [25.0, 26.0, 27.0]
        for val in values:
            data = {'SENSORID': 's1', 'TEMP': str(val)}
            result = interpolation_task.execute(data)
            assert result == val
        
        # Window should have all 3 values
        window_vals = interpolation_task.get_window_values('s1', 'TEMP')
        assert window_vals == values
    
    def test_interpolate_null_value(self, interpolation_task):
        """Test interpolating a null value."""
        # Build history
        for val in [24.0, 26.0, 28.0]:
            interpolation_task.execute({'SENSORID': 's1', 'TEMP': str(val)})
        
        # Interpolate null
        result = interpolation_task.execute({'SENSORID': 's1', 'TEMP': 'null'})
        
        # Should return average: (24 + 26 + 28) / 3 = 26.0
        assert result == 26.0
    
    def test_interpolate_empty_string(self, interpolation_task):
        """Test interpolating empty string (treated as null)."""
        # Build history
        for val in [10.0, 20.0, 30.0]:
            interpolation_task.execute({'SENSORID': 's1', 'TEMP': str(val)})
        
        # Empty string should trigger interpolation
        result = interpolation_task.execute({'SENSORID': 's1', 'TEMP': ''})
        assert result == 20.0  # Average of 10, 20, 30
    
    def test_null_before_history(self, interpolation_task):
        """Test null value when no history exists yet."""
        result = interpolation_task.execute({'SENSORID': 's1', 'TEMP': 'null'})
        assert result is None  # Cannot interpolate without history


class TestWindowManagement:
    """Test window size management."""
    
    def test_window_size_limit(self, interpolation_task):
        """Test window respects max size."""
        # Add more values than window size
        for val in [20.0, 21.0, 22.0, 23.0, 24.0]:
            interpolation_task.execute({'SENSORID': 's1', 'TEMP': str(val)})
        
        # Window should only keep last 3 values
        window_vals = interpolation_task.get_window_values('s1', 'TEMP')
        assert len(window_vals) == 3
        assert window_vals == [22.0, 23.0, 24.0]
    
    def test_interpolation_uses_limited_window(self, interpolation_task):
        """Test interpolation only uses values within window."""
        # Add 5 values (window size is 3)
        for val in [10.0, 20.0, 30.0, 40.0, 50.0]:
            interpolation_task.execute({'SENSORID': 's1', 'TEMP': str(val)})
        
        # Interpolate - should use only last 3 values
        result = interpolation_task.execute({'SENSORID': 's1', 'TEMP': 'null'})
        assert result == 40.0  # Average of 30, 40, 50
    
    def test_window_size_zero_disables_interpolation(self):
        """Test window_size=0 disables interpolation."""
        task = Interpolation()
        task.config = {
            'STATISTICS.INTERPOLATION.USE_MSG_FIELD': 'TEMP',
            'STATISTICS.INTERPOLATION.WINDOW_SIZE': 0,
        }
        task.setup()
        
        # Any input should return None
        result = task.execute({'SENSORID': 's1', 'TEMP': '25.0'})
        assert result is None


class TestMultipleSensors:
    """Test interpolation with multiple sensors."""
    
    def test_independent_windows_per_sensor(self, interpolation_task):
        """Test each sensor maintains independent window."""
        # Add values for sensor 1
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '20.0'})
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '22.0'})
        
        # Add values for sensor 2
        interpolation_task.execute({'SENSORID': 's2', 'TEMP': '30.0'})
        interpolation_task.execute({'SENSORID': 's2', 'TEMP': '32.0'})
        
        # Check independent windows
        s1_vals = interpolation_task.get_window_values('s1', 'TEMP')
        s2_vals = interpolation_task.get_window_values('s2', 'TEMP')
        
        assert s1_vals == [20.0, 22.0]
        assert s2_vals == [30.0, 32.0]
    
    def test_interpolate_different_sensors(self, interpolation_task):
        """Test interpolation works independently per sensor."""
        # Build history for s1
        for val in [10.0, 20.0, 30.0]:
            interpolation_task.execute({'SENSORID': 's1', 'TEMP': str(val)})
        
        # Build history for s2
        for val in [50.0, 60.0, 70.0]:
            interpolation_task.execute({'SENSORID': 's2', 'TEMP': str(val)})
        
        # Interpolate for each
        result_s1 = interpolation_task.execute({'SENSORID': 's1', 'TEMP': 'null'})
        result_s2 = interpolation_task.execute({'SENSORID': 's2', 'TEMP': 'null'})
        
        assert result_s1 == 20.0  # Average of s1: 10, 20, 30
        assert result_s2 == 60.0  # Average of s2: 50, 60, 70


class TestMultipleObstypes:
    """Test interpolation with multiple observation types."""
    
    def test_independent_windows_per_obstype(self, interpolation_task):
        """Test each obstype maintains independent window."""
        # Add TEMP values
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '20.0', 'HUM': '50.0'})
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '22.0', 'HUM': '52.0'})
        
        # Check independent windows
        temp_vals = interpolation_task.get_window_values('s1', 'TEMP')
        hum_vals = interpolation_task.get_window_values('s1', 'HUM')
        
        assert temp_vals == [20.0, 22.0]
        assert hum_vals == [50.0, 52.0]
    
    def test_interpolate_different_obstypes(self, interpolation_task):
        """Test interpolation works independently per obstype."""
        # Build history
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '10.0', 'HUM': '60.0'})
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '20.0', 'HUM': '70.0'})
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '30.0', 'HUM': '80.0'})
        
        # Interpolate TEMP only
        result = interpolation_task.execute({'SENSORID': 's1', 'TEMP': 'null', 'HUM': '75.0'})
        
        # Should interpolate TEMP (average 20.0) and accept HUM (75.0)
        # Function returns last processed result
        assert result in [20.0, 75.0]  # Either is valid depending on dict order
    
    def test_only_configured_fields_interpolated(self, interpolation_task):
        """Test only fields in USE_MSG_FIELD are processed."""
        # PRESSURE not in config (only TEMP, HUM)
        data = {'SENSORID': 's1', 'TEMP': '25.0', 'PRESSURE': '1013.0'}
        result = interpolation_task.execute(data)
        
        # TEMP should be processed, PRESSURE ignored
        assert 's1TEMP' in interpolation_task.values_map
        assert 's1PRESSURE' not in interpolation_task.values_map


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_missing_sensorid(self, interpolation_task):
        """Test handling missing SENSORID."""
        data = {'TEMP': '25.0'}
        result = interpolation_task.execute(data)
        assert result is None
    
    def test_non_dict_input(self, interpolation_task):
        """Test handling non-dictionary input."""
        result = interpolation_task.execute("not a dict")
        assert result is None
    
    def test_invalid_numeric_value(self, interpolation_task):
        """Test handling invalid numeric value."""
        result = interpolation_task.execute({'SENSORID': 's1', 'TEMP': 'invalid'})
        assert result is None
    
    def test_special_field_names_ignored(self, interpolation_task):
        """Test META and TS fields are ignored."""
        data = {
            'SENSORID': 's1',
            'TEMP': '25.0',
            'META': 'some metadata',
            'TS': '1234567890',
        }
        result = interpolation_task.execute(data)
        
        # Only TEMP should be processed
        assert 's1TEMP' in interpolation_task.values_map
        assert 's1META' not in interpolation_task.values_map
        assert 's1TS' not in interpolation_task.values_map


class TestStateManagement:
    """Test state management and cleanup."""
    
    def test_tear_down_clears_state(self, interpolation_task):
        """Test tear_down clears window state."""
        # Build some history
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '25.0'})
        assert len(interpolation_task.values_map) > 0
        
        # Tear down
        interpolation_task.tear_down()
        assert len(interpolation_task.values_map) == 0
    
    def test_get_window_state(self, interpolation_task):
        """Test getting window state for all sensors."""
        # Add data for multiple sensors and obstypes
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '20.0', 'HUM': '50.0'})
        interpolation_task.execute({'SENSORID': 's1', 'TEMP': '22.0'})
        interpolation_task.execute({'SENSORID': 's2', 'TEMP': '30.0'})
        
        state = interpolation_task.get_window_state()
        
        assert state['s1TEMP'] == 2
        assert state['s1HUM'] == 1
        assert state['s2TEMP'] == 1


class TestConfiguration:
    """Test configuration options."""
    
    def test_custom_window_size(self):
        """Test custom window size configuration."""
        task = Interpolation()
        task.config = {
            'STATISTICS.INTERPOLATION.USE_MSG_FIELD': 'TEMP',
            'STATISTICS.INTERPOLATION.WINDOW_SIZE': 10,
        }
        task.setup()
        
        assert task._window_size == 10
        
        # Add 10 values
        for i in range(10):
            task.execute({'SENSORID': 's1', 'TEMP': str(i)})
        
        # Window should hold all 10
        window_vals = task.get_window_values('s1', 'TEMP')
        assert len(window_vals) == 10
    
    def test_default_configuration(self):
        """Test default configuration values."""
        task = Interpolation()
        task.config = {}
        task.setup()
        
        assert task._use_msg_field == set()
        assert task._window_size == 5
    
    def test_empty_field_list(self):
        """Test empty USE_MSG_FIELD disables interpolation."""
        task = Interpolation()
        task.config = {
            'STATISTICS.INTERPOLATION.USE_MSG_FIELD': '',
            'STATISTICS.INTERPOLATION.WINDOW_SIZE': 3,
        }
        task.setup()
        
        assert task._use_msg_field == set()
        
        # Any input should be ignored
        result = task.execute({'SENSORID': 's1', 'TEMP': '25.0'})
        assert result is None
    
    def test_field_list_parsing(self):
        """Test parsing comma-separated field list."""
        task = Interpolation()
        task.config = {
            'STATISTICS.INTERPOLATION.USE_MSG_FIELD': 'TEMP, HUM , PRESSURE',
            'STATISTICS.INTERPOLATION.WINDOW_SIZE': 3,
        }
        task.setup()
        
        # Should strip whitespace
        assert task._use_msg_field == {'TEMP', 'HUM', 'PRESSURE'}
