"""Tests for SenMLParseTask.

This module tests the SenML (Sensor Markup Language) parsing implementation,
validating JSON parsing, CSV handling, and measurement extraction.
"""

import pytest
import json
from typing import Dict, Any

from pyriotbench.core import TaskRegistry, create_task
from pyriotbench.tasks.parse.senml_parse import SenMLParseTask


# Import to ensure task is registered
import pyriotbench.tasks.parse


@pytest.fixture(autouse=True)
def ensure_senml_registered():
    """Ensure SenMLParseTask is registered before each test."""
    if not TaskRegistry.is_registered("senml_parse"):
        TaskRegistry.register("senml_parse", SenMLParseTask)
    yield


class TestSenMLParseRegistration:
    """Test SenMLParseTask registration in TaskRegistry."""
    
    def test_senml_parse_is_registered(self):
        """Test that SenMLParseTask is registered with correct name."""
        assert TaskRegistry.is_registered("senml_parse"), \
            "SenMLParseTask should be registered as 'senml_parse'"
    
    def test_senml_parse_get_task_class(self):
        """Test retrieving SenMLParseTask class from registry."""
        task_class = TaskRegistry.get("senml_parse")
        assert task_class is not None, "Should retrieve SenMLParseTask class"
        assert task_class is SenMLParseTask, "Should retrieve correct class"
    
    def test_senml_parse_in_task_list(self):
        """Test that 'senml_parse' appears in task listing."""
        tasks = TaskRegistry.list_tasks()
        assert "senml_parse" in tasks, "'senml_parse' should be in task list"
    
    def test_senml_parse_create_task(self):
        """Test creating SenMLParseTask via factory function."""
        task = create_task("senml_parse")
        assert task is not None, "Should create task instance"
        assert isinstance(task, SenMLParseTask), "Should create correct type"


class TestSenMLParseLifecycle:
    """Test SenMLParseTask setup, execution, and teardown lifecycle."""
    
    def test_setup_and_teardown(self):
        """Test basic setup and teardown."""
        task = SenMLParseTask()
        task.setup()
        task.tear_down()
    
    def test_setup_initializes_counters(self):
        """Test that setup initializes internal counters."""
        task = SenMLParseTask()
        task.setup()
        
        assert hasattr(task, '_parse_count'), "Should have parse counter"
        assert task._parse_count == 0, "Parse count should start at 0"
        
        task.tear_down()


class TestSenMLParseBasicExecution:
    """Test basic SenML parsing functionality."""
    
    def test_parse_simple_senml(self):
        """Test parsing simple SenML with one numeric measurement."""
        task = SenMLParseTask()
        task.setup()
        
        input_line = '1234567890,{"e":[{"v":"23.5","u":"celsius","n":"temp"}],"bt":"1234567890"}'
        result = task.execute(input_line)
        
        assert result["timestamp"] == 1234567890
        assert result["base_time"] == 1234567890
        assert len(result["measurements"]) == 1
        assert result["measurements"][0]["name"] == "temp"
        assert result["measurements"][0]["value"] == "23.5"
        assert result["measurements"][0]["unit"] == "celsius"
        
        task.tear_down()
    
    def test_parse_multiple_measurements(self):
        """Test parsing SenML with multiple measurements."""
        task = SenMLParseTask()
        task.setup()
        
        senml_json = {
            "e": [
                {"v": "25.0", "u": "celsius", "n": "temperature"},
                {"v": "60.0", "u": "percent", "n": "humidity"},
                {"v": "1013.25", "u": "hPa", "n": "pressure"}
            ],
            "bt": "9876543210"
        }
        input_line = f'9876543210,{json.dumps(senml_json)}'
        
        result = task.execute(input_line)
        
        assert len(result["measurements"]) == 3
        assert result["measurements"][0]["name"] == "temperature"
        assert result["measurements"][1]["name"] == "humidity"
        assert result["measurements"][2]["name"] == "pressure"
        
        task.tear_down()
    
    def test_parse_string_value(self):
        """Test parsing SenML with string value (sv)."""
        task = SenMLParseTask()
        task.setup()
        
        senml_json = {
            "e": [{"sv": "sensor_123", "u": "string", "n": "sensor_id"}],
            "bt": "1111111111"
        }
        input_line = f'1111111111,{json.dumps(senml_json)}'
        
        result = task.execute(input_line)
        
        assert result["measurements"][0]["string_value"] == "sensor_123"
        assert result["measurements"][0]["name"] == "sensor_id"
        
        task.tear_down()
    
    def test_parse_mixed_value_types(self):
        """Test parsing SenML with mixed value types (v and sv)."""
        task = SenMLParseTask()
        task.setup()
        
        senml_json = {
            "e": [
                {"sv": "ABC123", "u": "string", "n": "taxi_id"},
                {"v": "40.7128", "u": "lat", "n": "latitude"},
                {"v": "-74.0060", "u": "lon", "n": "longitude"}
            ],
            "bt": "2222222222"
        }
        input_line = f'2222222222,{json.dumps(senml_json)}'
        
        result = task.execute(input_line)
        
        assert len(result["measurements"]) == 3
        assert "string_value" in result["measurements"][0]
        assert "value" in result["measurements"][1]
        assert "value" in result["measurements"][2]
        
        task.tear_down()


class TestSenMLParseRealData:
    """Test parsing with real TAXI dataset format."""
    
    def test_parse_taxi_record(self):
        """Test parsing real TAXI SenML record."""
        task = SenMLParseTask()
        task.setup()
        
        # Real TAXI format from the dataset
        input_line = '''1358101800000,{"e":[{"u":"string","n":"taxi_identifier","sv":"149298F6D390FA640E80B41ED31199C5"},{"u":"string","n":"hack_license","sv":"08F944E76118632BE09B9D4B04C7012A"},{"u":"time","n":"pickup_datetime","sv":"2013-01-13 23:36:00"},{"v":"1440","u":"second","n":"trip_time_in_secs"},{"v":"9.08","u":"meter","n":"trip_distance"},{"u":"lon","n":"pickup_longitude","sv":"-73.982071"},{"u":"lat","n":"pickup_latitude","sv":"40.769081"},{"u":"lon","n":"dropoff_longitude","sv":"-73.915878"},{"u":"lat","n":"dropoff_latitude","sv":"40.868458"},{"u":"string","n":"payment_type","sv":"CSH"},{"v":"29.00","u":"dollar","n":"fare_amount"},{"v":"0.50","u":"percentage","n":"surcharge"},{"v":"0.50","u":"percentage","n":"mta_tax"},{"v":"0.00","u":"dollar","n":"tip_amount"},{"v":"0.00","u":"dollar","n":"tolls_amount"},{"v":"30.00","u":"dollar","n":"total_amount"}],"bt":1358101800000}'''
        
        result = task.execute(input_line)
        
        assert result["timestamp"] == 1358101800000
        assert result["base_time"] == 1358101800000
        assert len(result["measurements"]) == 16
        
        # Check specific fields
        taxi_id = next(m for m in result["measurements"] if m["name"] == "taxi_identifier")
        assert taxi_id["string_value"] == "149298F6D390FA640E80B41ED31199C5"
        
        fare = next(m for m in result["measurements"] if m["name"] == "fare_amount")
        assert fare["value"] == "29.00"
        assert fare["unit"] == "dollar"
        
        task.tear_down()


class TestSenMLParseInputFormats:
    """Test different input format handling."""
    
    def test_parse_string_input(self):
        """Test parsing from string input."""
        task = SenMLParseTask()
        task.setup()
        
        input_str = '100,{"e":[{"v":"1.0","n":"x"}],"bt":"100"}'
        result = task.execute(input_str)
        
        assert result["timestamp"] == 100
        
        task.tear_down()
    
    def test_parse_dict_with_value_key(self):
        """Test parsing from dict with 'value' key."""
        task = SenMLParseTask()
        task.setup()
        
        input_dict = {"value": '200,{"e":[{"v":"2.0","n":"y"}],"bt":"200"}'}
        result = task.execute(input_dict)
        
        assert result["timestamp"] == 200
        
        task.tear_down()
    
    def test_parse_already_parsed_dict(self):
        """Test that already parsed dict passes through."""
        task = SenMLParseTask()
        task.setup()
        
        already_parsed = {
            "timestamp": 300,
            "base_time": 300,
            "measurements": [{"name": "z", "value": "3.0"}]
        }
        result = task.execute(already_parsed)
        
        assert result == already_parsed
        
        task.tear_down()


class TestSenMLParseEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_measurements(self):
        """Test parsing SenML with empty measurements array."""
        task = SenMLParseTask()
        task.setup()
        
        input_line = '500,{"e":[],"bt":"500"}'
        result = task.execute(input_line)
        
        assert result["timestamp"] == 500
        assert len(result["measurements"]) == 0
        
        task.tear_down()
    
    def test_missing_base_time(self):
        """Test parsing when base_time is missing."""
        task = SenMLParseTask()
        task.setup()
        
        input_line = '600,{"e":[{"v":"1.0","n":"test"}]}'
        result = task.execute(input_line)
        
        assert result["timestamp"] == 600
        assert result["base_time"] == 600  # Should default to timestamp
        
        task.tear_down()
    
    def test_measurement_without_unit(self):
        """Test measurement without unit field."""
        task = SenMLParseTask()
        task.setup()
        
        senml_json = {"e": [{"v": "42", "n": "answer"}], "bt": "700"}
        input_line = f'700,{json.dumps(senml_json)}'
        
        result = task.execute(input_line)
        
        assert result["measurements"][0]["unit"] == ""
        
        task.tear_down()
    
    def test_measurement_without_name(self):
        """Test measurement without name field."""
        task = SenMLParseTask()
        task.setup()
        
        senml_json = {"e": [{"v": "99", "u": "unit"}], "bt": "800"}
        input_line = f'800,{json.dumps(senml_json)}'
        
        result = task.execute(input_line)
        
        assert result["measurements"][0]["name"] == ""
        
        task.tear_down()
    
    def test_invalid_csv_format(self):
        """Test error handling for invalid CSV format."""
        task = SenMLParseTask()
        task.setup()
        
        # execute() catches exceptions - test do_task() directly
        with pytest.raises(ValueError, match="Invalid SenML CSV format"):
            task.do_task("invalid_no_comma")
        
        task.tear_down()
    
    def test_invalid_timestamp(self):
        """Test error handling for invalid timestamp."""
        task = SenMLParseTask()
        task.setup()
        
        # execute() catches exceptions - test do_task() directly
        with pytest.raises(ValueError, match="Invalid timestamp"):
            task.do_task("not_a_number,{\"e\":[],\"bt\":0}")
        
        task.tear_down()
    
    def test_invalid_json(self):
        """Test error handling for invalid JSON."""
        task = SenMLParseTask()
        task.setup()
        
        # execute() catches exceptions - test do_task() directly
        with pytest.raises(ValueError, match="Invalid JSON"):
            task.do_task("1234567890,{invalid json}")
        
        task.tear_down()
    
    def test_dict_without_value_key_raises_error(self):
        """Test that dict without 'value' or parsed keys raises error."""
        task = SenMLParseTask()
        task.setup()
        
        # execute() catches exceptions - test do_task() directly
        with pytest.raises(ValueError, match="Dict input must have"):
            task.do_task({"some_key": "some_value"})
        
        task.tear_down()


class TestSenMLParseTiming:
    """Test timing and performance characteristics."""
    
    def test_execution_is_timed(self):
        """Test that execution time is recorded."""
        task = SenMLParseTask()
        task.setup()
        
        input_line = '1000,{"e":[{"v":"1","n":"test"}],"bt":"1000"}'
        result = task.execute(input_line)
        
        task_result = task.get_last_result()
        assert task_result.success, "Parse should succeed"
        assert task_result.execution_time_ms >= 0, "Should have timing"
        
        task.tear_down()
    
    def test_execution_is_fast(self):
        """Test that SenML parsing is reasonably fast."""
        task = SenMLParseTask()
        task.setup()
        
        input_line = '2000,{"e":[{"v":"2","n":"x"}],"bt":"2000"}'
        task.execute(input_line)
        
        task_result = task.get_last_result()
        # SenML parsing should be fast (< 10ms for simple records)
        assert task_result.execution_time_ms < 10.0, \
            f"Parse should be fast, took {task_result.execution_time_ms}ms"
        
        task.tear_down()
    
    def test_multiple_executions(self):
        """Test multiple sequential parse operations."""
        task = SenMLParseTask()
        task.setup()
        
        inputs = [
            '1000,{"e":[{"v":"1","n":"a"}],"bt":"1000"}',
            '2000,{"e":[{"v":"2","n":"b"}],"bt":"2000"}',
            '3000,{"e":[{"v":"3","n":"c"}],"bt":"3000"}',
        ]
        
        results = [task.execute(inp) for inp in inputs]
        
        assert len(results) == 3
        assert results[0]["timestamp"] == 1000
        assert results[1]["timestamp"] == 2000
        assert results[2]["timestamp"] == 3000
        
        task.tear_down()


class TestSenMLParseCounters:
    """Test internal counter tracking."""
    
    def test_parse_count_increments(self):
        """Test that parse counter increments."""
        task = SenMLParseTask()
        task.setup()
        
        assert task._parse_count == 0
        
        task.execute('100,{"e":[],"bt":"100"}')
        assert task._parse_count == 1
        
        task.execute('200,{"e":[],"bt":"200"}')
        assert task._parse_count == 2
        
        task.execute('300,{"e":[],"bt":"300"}')
        assert task._parse_count == 3
        
        task.tear_down()
    
    def test_teardown_logs_statistics(self, caplog):
        """Test that teardown logs parse statistics."""
        import logging
        logger = logging.getLogger("SenMLParseTask")
        logger.setLevel(logging.INFO)
        
        task = SenMLParseTask()
        task.setup()
        
        # Parse a few records
        for i in range(5):
            # Fix f-string: double braces escape JSON braces
            task.execute(f'{i},{{\"e\":[],\"bt\":{i}}}')
        
        task.tear_down()
        
        # Should log completion with count
        messages = [record.message for record in caplog.records]
        assert any("parsed 5 records" in msg for msg in messages), \
            "Should log parse count on teardown"


class TestSenMLParseDocumentation:
    """Test that SenMLParseTask has proper documentation."""
    
    def test_has_proper_docstring(self):
        """Test that SenMLParseTask has comprehensive docstring."""
        assert SenMLParseTask.__doc__ is not None
        assert len(SenMLParseTask.__doc__) > 200
        assert "SenML" in SenMLParseTask.__doc__
        assert "sensor" in SenMLParseTask.__doc__.lower()
    
    def test_methods_have_docstrings(self):
        """Test that all methods have docstrings."""
        assert SenMLParseTask.setup.__doc__ is not None
        assert SenMLParseTask.do_task.__doc__ is not None
        assert SenMLParseTask.tear_down.__doc__ is not None
    
    def test_follows_basetask_pattern(self):
        """Test that SenMLParseTask follows BaseTask pattern correctly."""
        from pyriotbench.core import BaseTask
        
        assert issubclass(SenMLParseTask, BaseTask)
        assert hasattr(SenMLParseTask, 'do_task')
        assert callable(getattr(SenMLParseTask, 'do_task'))
