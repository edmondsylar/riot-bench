"""
Tests for RangeFilterCheck task - Range validation for sensor values.
"""

import pytest
from pyriotbench.core.registry import TaskRegistry
from pyriotbench.tasks.filter.range_filter_check import RangeFilterCheck


@pytest.fixture
def range_task():
    """Create a RangeFilterCheck task with default configuration."""
    task = RangeFilterCheck()
    task.config = {
        'FILTER.RANGE_FILTER.VALID_RANGE': 'TEMP:15:30,HUM:20:80,PRESSURE:950:1050'
    }
    task.setup()
    return task


@pytest.fixture
def single_range_task():
    """Create task with single field range."""
    task = RangeFilterCheck()
    task.config = {
        'FILTER.RANGE_FILTER.VALID_RANGE': 'SPEED:0:120'
    }
    task.setup()
    return task


class TestRangeFilterCheckBasics:
    """Test basic functionality and setup."""
    
    def test_task_registration(self):
        """Test that task is properly registered."""
        assert TaskRegistry.is_registered('range_filter_check')
        task_class = TaskRegistry.get('range_filter_check')
        assert task_class == RangeFilterCheck
    
    def test_setup(self, range_task):
        """Test task setup with configuration."""
        ranges = range_task.get_configured_ranges()
        assert len(ranges) == 3
        assert ranges['TEMP'] == (15.0, 30.0)
        assert ranges['HUM'] == (20.0, 80.0)
        assert ranges['PRESSURE'] == (950.0, 1050.0)
    
    def test_setup_single_range(self, single_range_task):
        """Test setup with single range."""
        ranges = single_range_task.get_configured_ranges()
        assert len(ranges) == 1
        assert ranges['SPEED'] == (0.0, 120.0)


class TestRangeValidation:
    """Test range validation logic."""
    
    def test_all_fields_valid(self, range_task):
        """Test with all fields in valid range."""
        result = range_task.execute('TEMP:25,HUM:60,PRESSURE:1000')
        assert result == 1.0
    
    def test_single_field_valid(self, single_range_task):
        """Test with single field in range."""
        result = single_range_task.execute('SPEED:80')
        assert result == 1.0
    
    def test_temp_out_of_range_high(self, range_task):
        """Test with temperature too high."""
        result = range_task.execute('TEMP:35,HUM:60,PRESSURE:1000')
        assert result == 0.0
    
    def test_temp_out_of_range_low(self, range_task):
        """Test with temperature too low."""
        result = range_task.execute('TEMP:10,HUM:60,PRESSURE:1000')
        assert result == 0.0
    
    def test_hum_out_of_range(self, range_task):
        """Test with humidity out of range."""
        result = range_task.execute('TEMP:25,HUM:90,PRESSURE:1000')
        assert result == 0.0
    
    def test_pressure_out_of_range(self, range_task):
        """Test with pressure out of range."""
        result = range_task.execute('TEMP:25,HUM:60,PRESSURE:900')
        assert result == 0.0
    
    def test_multiple_fields_out_of_range(self, range_task):
        """Test with multiple fields out of range."""
        result = range_task.execute('TEMP:35,HUM:90,PRESSURE:900')
        assert result == 0.0
    
    def test_at_min_boundary(self, range_task):
        """Test with value at minimum boundary."""
        result = range_task.execute('TEMP:15,HUM:20,PRESSURE:950')
        assert result == 1.0  # Inclusive boundaries
    
    def test_at_max_boundary(self, range_task):
        """Test with value at maximum boundary."""
        result = range_task.execute('TEMP:30,HUM:80,PRESSURE:1050')
        assert result == 1.0  # Inclusive boundaries
    
    def test_just_below_min(self, single_range_task):
        """Test with value just below minimum."""
        result = single_range_task.execute('SPEED:-0.1')
        assert result == 0.0
    
    def test_just_above_max(self, single_range_task):
        """Test with value just above maximum."""
        result = single_range_task.execute('SPEED:120.1')
        assert result == 0.0


class TestPartialData:
    """Test with partial/missing fields."""
    
    def test_missing_field(self, range_task):
        """Test with one field missing."""
        # Only TEMP and HUM, no PRESSURE
        result = range_task.execute('TEMP:25,HUM:60')
        assert result == 1.0  # Present fields are valid
    
    def test_only_one_field(self, range_task):
        """Test with only one field present."""
        result = range_task.execute('TEMP:25')
        assert result == 1.0
    
    def test_unconfigured_field(self, range_task):
        """Test with field not in configuration."""
        # WIND_SPEED not configured, should be ignored
        result = range_task.execute('TEMP:25,WIND_SPEED:100')
        assert result == 1.0
    
    def test_mix_configured_unconfigured(self, range_task):
        """Test mix of configured and unconfigured fields."""
        result = range_task.execute('TEMP:25,HUM:60,WIND:50,PRESSURE:1000')
        assert result == 1.0


class TestDataParsing:
    """Test input data parsing."""
    
    def test_parse_colon_format(self, range_task):
        """Test parsing field:value format."""
        result = range_task.execute('TEMP:25')
        assert result == 1.0
    
    def test_parse_multiple_colons(self, range_task):
        """Test parsing value with multiple colons (time format)."""
        # Should split on first colon only
        result = range_task.execute('TEMP:25,TIME:12:30:45')
        assert result == 1.0  # TIME not configured, ignored
    
    def test_whitespace_handling(self, range_task):
        """Test that whitespace is handled correctly."""
        result = range_task.execute('  TEMP : 25 , HUM : 60  ')
        assert result == 1.0
    
    def test_empty_input(self, range_task):
        """Test with empty input."""
        result = range_task.execute('')
        assert result == 1.0  # No data, pass by default
    
    def test_whitespace_only(self, range_task):
        """Test with whitespace-only input."""
        result = range_task.execute('   ')
        assert result == 1.0


class TestInvalidData:
    """Test handling of invalid data."""
    
    def test_non_numeric_value(self, range_task):
        """Test with non-numeric value."""
        result = range_task.execute('TEMP:abc,HUM:60')
        assert result == 0.0  # Invalid value fails
    
    def test_partially_invalid(self, range_task):
        """Test with mix of valid and invalid values."""
        result = range_task.execute('TEMP:25,HUM:invalid,PRESSURE:1000')
        assert result == 0.0


class TestConfiguration:
    """Test configuration parsing."""
    
    def test_single_range_config(self):
        """Test configuration with single range."""
        task = RangeFilterCheck()
        task.config = {'FILTER.RANGE_FILTER.VALID_RANGE': 'FIELD:10:20'}
        task.setup()
        
        ranges = task.get_configured_ranges()
        assert len(ranges) == 1
        assert ranges['FIELD'] == (10.0, 20.0)
    
    def test_multiple_ranges_config(self):
        """Test configuration with multiple ranges."""
        task = RangeFilterCheck()
        task.config = {
            'FILTER.RANGE_FILTER.VALID_RANGE': 'A:1:10,B:20:30,C:40:50'
        }
        task.setup()
        
        ranges = task.get_configured_ranges()
        assert len(ranges) == 3
        assert ranges['A'] == (1.0, 10.0)
        assert ranges['B'] == (20.0, 30.0)
        assert ranges['C'] == (40.0, 50.0)
    
    def test_float_ranges(self):
        """Test configuration with floating point ranges."""
        task = RangeFilterCheck()
        task.config = {
            'FILTER.RANGE_FILTER.VALID_RANGE': 'VOLTAGE:3.2:3.4,CURRENT:0.5:1.5'
        }
        task.setup()
        
        ranges = task.get_configured_ranges()
        assert ranges['VOLTAGE'] == (3.2, 3.4)
        assert ranges['CURRENT'] == (0.5, 1.5)
    
    def test_negative_ranges(self):
        """Test configuration with negative values."""
        task = RangeFilterCheck()
        task.config = {
            'FILTER.RANGE_FILTER.VALID_RANGE': 'TEMP:-20:40,ALTITUDE:-100:8848'
        }
        task.setup()
        
        result = task.execute('TEMP:-10,ALTITUDE:1000')
        assert result == 1.0
        
        result = task.execute('TEMP:-25')
        assert result == 0.0
    
    def test_empty_configuration(self):
        """Test with empty configuration."""
        task = RangeFilterCheck()
        task.config = {'FILTER.RANGE_FILTER.VALID_RANGE': ''}
        task.setup()
        
        ranges = task.get_configured_ranges()
        assert len(ranges) == 0
        
        # Should pass by default with no config
        result = task.execute('FIELD:100')
        assert result == 1.0
    
    def test_malformed_entries_skipped(self):
        """Test that malformed entries are skipped."""
        task = RangeFilterCheck()
        task.config = {
            'FILTER.RANGE_FILTER.VALID_RANGE': 'GOOD:10:20,BAD:30,GOOD2:40:50'
        }
        task.setup()
        
        ranges = task.get_configured_ranges()
        # Only valid entries should be parsed
        assert 'GOOD' in ranges
        assert 'GOOD2' in ranges
        assert 'BAD' not in ranges
    
    def test_invalid_range_order(self):
        """Test with min > max (should be skipped with warning)."""
        task = RangeFilterCheck()
        task.config = {
            'FILTER.RANGE_FILTER.VALID_RANGE': 'VALID:10:20,INVALID:50:40'
        }
        task.setup()
        
        ranges = task.get_configured_ranges()
        assert 'VALID' in ranges
        # INVALID should be skipped (min > max)
        assert 'INVALID' not in ranges


class TestEdgeCases:
    """Test edge cases."""
    
    def test_zero_range(self):
        """Test with zero-width range (min == max)."""
        task = RangeFilterCheck()
        task.config = {'FILTER.RANGE_FILTER.VALID_RANGE': 'CONSTANT:42:42'}
        task.setup()
        
        assert task.execute('CONSTANT:42') == 1.0
        assert task.execute('CONSTANT:42.0') == 1.0
        assert task.execute('CONSTANT:41.9') == 0.0
        assert task.execute('CONSTANT:42.1') == 0.0
    
    def test_very_large_numbers(self):
        """Test with very large numbers."""
        task = RangeFilterCheck()
        task.config = {'FILTER.RANGE_FILTER.VALID_RANGE': 'BIG:1e6:1e9'}
        task.setup()
        
        assert task.execute('BIG:5e8') == 1.0
        assert task.execute('BIG:1e10') == 0.0
    
    def test_very_small_numbers(self):
        """Test with very small numbers."""
        task = RangeFilterCheck()
        task.config = {'FILTER.RANGE_FILTER.VALID_RANGE': 'TINY:1e-9:1e-6'}
        task.setup()
        
        assert task.execute('TINY:1e-7') == 1.0
        assert task.execute('TINY:1e-10') == 0.0


class TestStateManagement:
    """Test state management and cleanup."""
    
    def test_tear_down(self, range_task):
        """Test that tear_down works without errors."""
        range_task.execute('TEMP:25')
        range_task.tear_down()
        # Should complete without error
    
    def test_multiple_setups(self):
        """Test that setup can be called multiple times."""
        task = RangeFilterCheck()
        
        task.config = {'FILTER.RANGE_FILTER.VALID_RANGE': 'A:1:10'}
        task.setup()
        assert len(task.get_configured_ranges()) == 1
        
        task.config = {'FILTER.RANGE_FILTER.VALID_RANGE': 'A:1:10,B:20:30'}
        task.setup()
        assert len(task.get_configured_ranges()) == 2
    
    def test_get_configured_fields(self, range_task):
        """Test getting list of configured fields."""
        fields = range_task.get_configured_fields()
        assert 'TEMP' in fields
        assert 'HUM' in fields
        assert 'PRESSURE' in fields
        assert len(fields) == 3


class TestRealWorldScenarios:
    """Test realistic IoT scenarios."""
    
    def test_temperature_sensor(self):
        """Test typical temperature sensor validation."""
        task = RangeFilterCheck()
        task.config = {
            'FILTER.RANGE_FILTER.VALID_RANGE': 'TEMP:-40:85'  # Typical sensor range
        }
        task.setup()
        
        # Normal readings
        assert task.execute('TEMP:20') == 1.0
        assert task.execute('TEMP:25.5') == 1.0
        
        # Sensor malfunction
        assert task.execute('TEMP:150') == 0.0
        assert task.execute('TEMP:-50') == 0.0
    
    def test_multi_sensor_device(self):
        """Test validation for multi-sensor IoT device."""
        task = RangeFilterCheck()
        task.config = {
            'FILTER.RANGE_FILTER.VALID_RANGE': 
                'TEMP:-40:85,HUM:0:100,LIGHT:0:100000,BATTERY:0:100'
        }
        task.setup()
        
        # All sensors healthy
        result = task.execute('TEMP:22,HUM:55,LIGHT:5000,BATTERY:87')
        assert result == 1.0
        
        # Battery critical (but still valid)
        result = task.execute('TEMP:22,HUM:55,LIGHT:5000,BATTERY:5')
        assert result == 1.0
        
        # Humidity sensor error
        result = task.execute('TEMP:22,HUM:105,LIGHT:5000,BATTERY:87')
        assert result == 0.0
