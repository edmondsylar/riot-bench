"""
Tests for CsvToSenMLParse task - CSV to SenML JSON conversion.
"""

import pytest
import json
import tempfile
from pathlib import Path
from pyriotbench.core.registry import TaskRegistry
from pyriotbench.tasks.parse.csv_to_senml_parse import CsvToSenMLParse


@pytest.fixture
def schema_file(tmp_path):
    """Create a temporary schema file."""
    schema = tmp_path / "schema.txt"
    schema.write_text(
        "timestamp,temp,humidity,pressure\n"
        ",C,%,hPa\n"
        ",v,v,v\n"
    )
    return str(schema)


@pytest.fixture
def task_with_schema(schema_file):
    """Create task with schema file configuration."""
    task = CsvToSenMLParse()
    task.config = {
        'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': schema_file,
        'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
    }
    task.setup()
    return task


@pytest.fixture
def task_with_defaults():
    """Create task with default schema."""
    task = CsvToSenMLParse()
    task.config = {
        'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': '',
        'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
    }
    task.setup()
    return task


@pytest.fixture(autouse=True)
def reset_class_state():
    """Reset class state before each test."""
    CsvToSenMLParse._done_setup = False
    CsvToSenMLParse._schema_map = {}
    CsvToSenMLParse._timestamp_field = 0
    CsvToSenMLParse._use_msg_field = -1
    CsvToSenMLParse._sample_data = ""
    yield


class TestCsvToSenMLParseBasics:
    """Test basic functionality and setup."""
    
    def test_task_registration(self):
        """Test that task is properly registered."""
        assert TaskRegistry.is_registered('csv_to_senml_parse')
        task_class = TaskRegistry.get('csv_to_senml_parse')
        assert task_class == CsvToSenMLParse
    
    def test_setup_with_schema(self, schema_file):
        """Test setup with schema file."""
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': schema_file,
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        info = task.get_schema_info()
        assert info['field_count'] == 4
        assert info['timestamp_field'] == 0
        assert len(info['fields']) == 4
    
    def test_setup_with_defaults(self, task_with_defaults):
        """Test setup with default schema."""
        info = task_with_defaults.get_schema_info()
        assert info['field_count'] == 4
        assert info['timestamp_field'] == 0


class TestSchemaLoading:
    """Test schema file loading."""
    
    def test_load_simple_schema(self, tmp_path):
        """Test loading a simple schema."""
        schema = tmp_path / "simple.txt"
        schema.write_text(
            "time,value\n"
            ",units\n"
            ",v\n"
        )
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        info = task.get_schema_info()
        assert info['field_count'] == 2
    
    def test_load_complex_schema(self, tmp_path):
        """Test loading a schema with many fields."""
        schema = tmp_path / "complex.txt"
        schema.write_text(
            "timestamp,f1,f2,f3,f4,f5\n"
            ",u1,u2,u3,u4,u5\n"
            ",v,v,s,v,v\n"
        )
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        info = task.get_schema_info()
        assert info['field_count'] == 6
        assert len(task.get_field_names()) == 5  # Excluding timestamp
    
    def test_missing_schema_file(self):
        """Test handling of missing schema file."""
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': '/nonexistent/schema.txt',
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        
        with pytest.raises(FileNotFoundError):
            task.setup()
    
    def test_malformed_schema_short(self, tmp_path):
        """Test handling of malformed schema (too few lines)."""
        schema = tmp_path / "malformed.txt"
        schema.write_text("column1,column2\n")  # Only 1 line
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        
        with pytest.raises(ValueError, match="must have 3 lines"):
            task.setup()
    
    def test_malformed_schema_mismatch(self, tmp_path):
        """Test handling of schema with mismatched lengths."""
        schema = tmp_path / "mismatch.txt"
        schema.write_text(
            "col1,col2,col3\n"
            "u1,u2\n"  # Only 2 units
            "v,v,v\n"
        )
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        
        with pytest.raises(ValueError, match="Schema mismatch"):
            task.setup()


class TestConversion:
    """Test CSV to SenML conversion."""
    
    def test_basic_conversion(self, task_with_schema):
        """Test basic CSV to SenML conversion."""
        csv_data = "2024-01-01 12:00:00,25.5,60,1013"
        result = task_with_schema.execute(csv_data)
        
        assert result is not None
        senml = json.loads(result)
        assert 'bt' in senml
        assert 'e' in senml
        assert senml['bt'] == "2024-01-01 12:00:00"
        assert len(senml['e']) == 3  # Excluding timestamp
    
    def test_conversion_with_defaults(self, task_with_defaults):
        """Test conversion with default schema."""
        csv_data = "2024-01-01 12:00:00,22,55,1000"
        result = task_with_defaults.execute(csv_data)
        
        assert result is not None
        senml = json.loads(result)
        assert senml['bt'] == "2024-01-01 12:00:00"
    
    def test_entry_structure(self, task_with_schema):
        """Test that entries have correct structure."""
        csv_data = "2024-01-01 12:00:00,25.5,60,1013"
        result = task_with_schema.execute(csv_data)
        
        senml = json.loads(result)
        entry = senml['e'][0]
        
        assert 'n' in entry  # Name
        assert 'v' in entry  # Value
        assert 'u' in entry  # Unit
        assert entry['n'] == 'temp'
        assert entry['v'] == '25.5'
        assert entry['u'] == 'C'
    
    def test_multiple_entries(self, task_with_schema):
        """Test conversion with multiple entries."""
        csv_data = "2024-01-01 12:00:00,25.5,60,1013"
        result = task_with_schema.execute(csv_data)
        
        senml = json.loads(result)
        entries = senml['e']
        
        assert len(entries) == 3
        assert entries[0]['n'] == 'temp'
        assert entries[1]['n'] == 'humidity'
        assert entries[2]['n'] == 'pressure'


class TestDataTypes:
    """Test handling of different data types."""
    
    def test_numeric_values(self, tmp_path):
        """Test conversion of numeric values."""
        schema = tmp_path / "numeric.txt"
        schema.write_text(
            "timestamp,value\n"
            ",m\n"
            ",v\n"
        )
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        result = task.execute("2024-01-01,123.45")
        senml = json.loads(result)
        
        assert senml['e'][0]['v'] == '123.45'
        assert senml['e'][0]['n'] == 'value'
    
    def test_string_values(self, tmp_path):
        """Test conversion of string values."""
        schema = tmp_path / "string.txt"
        schema.write_text(
            "timestamp,label\n"
            ",\n"
            ",s\n"
        )
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        result = task.execute("2024-01-01,test_label")
        senml = json.loads(result)
        
        assert senml['e'][0]['s'] == 'test_label'
    
    def test_mixed_types(self, tmp_path):
        """Test conversion with mixed data types."""
        schema = tmp_path / "mixed.txt"
        schema.write_text(
            "timestamp,value,name\n"
            ",m,\n"
            ",v,s\n"
        )
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        result = task.execute("2024-01-01,42.0,sensor_A")
        senml = json.loads(result)
        
        assert senml['e'][0]['v'] == '42.0'
        assert senml['e'][1]['s'] == 'sensor_A'


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_input(self, task_with_schema):
        """Test with empty input."""
        result = task_with_schema.execute("")
        assert result is None
    
    def test_whitespace_only(self, task_with_schema):
        """Test with whitespace-only input."""
        result = task_with_schema.execute("   ")
        assert result is None
    
    def test_fewer_values_than_fields(self, task_with_schema):
        """Test with fewer values than schema fields."""
        csv_data = "2024-01-01,25.5"  # Missing humidity and pressure
        result = task_with_schema.execute(csv_data)
        
        assert result is not None
        senml = json.loads(result)
        assert len(senml['e']) == 1  # Only temp
    
    def test_more_values_than_fields(self, task_with_schema):
        """Test with more values than schema fields."""
        csv_data = "2024-01-01,25.5,60,1013,extra1,extra2"
        result = task_with_schema.execute(csv_data)
        
        assert result is not None
        senml = json.loads(result)
        assert len(senml['e']) == 3  # Only defined fields
    
    def test_missing_timestamp(self, tmp_path):
        """Test with schema that has no timestamp field."""
        schema = tmp_path / "no_timestamp.txt"
        schema.write_text(
            "value1,value2\n"
            "u1,u2\n"
            "v,v\n"
        )
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        result = task.execute("10,20")
        senml = json.loads(result)
        
        # Should have empty bt or first field as bt
        assert 'bt' in senml
        assert len(senml['e']) >= 1


class TestUseMsgField:
    """Test USE_MSG_FIELD configuration."""
    
    def test_use_sample_data(self, schema_file):
        """Test using sample data (useMsgField = -1)."""
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': schema_file,
            'PARSE.CSV_SENML_USE_MSG_FIELD': '-1'
        }
        task.setup()
        
        # Any input should be ignored, sample data used
        result = task.execute("ignored,data,here")
        assert result is not None
        
        senml = json.loads(result)
        # Sample data has specific timestamp
        assert '2013-01-14' in senml['bt']
    
    def test_use_provided_data(self, schema_file):
        """Test using provided data (useMsgField = 0)."""
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': schema_file,
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        result = task.execute("2024-01-01,25,50,1000")
        senml = json.loads(result)
        
        assert senml['bt'] == "2024-01-01"


class TestHelperMethods:
    """Test helper methods."""
    
    def test_get_schema_info(self, task_with_schema):
        """Test get_schema_info method."""
        info = task_with_schema.get_schema_info()
        
        assert 'field_count' in info
        assert 'timestamp_field' in info
        assert 'fields' in info
        assert 'use_msg_field' in info
        
        assert info['field_count'] == 4
        assert isinstance(info['fields'], list)
    
    def test_get_field_names(self, task_with_schema):
        """Test get_field_names method."""
        names = task_with_schema.get_field_names()
        
        assert 'temp' in names
        assert 'humidity' in names
        assert 'pressure' in names
        assert 'timestamp' not in names  # Timestamp excluded
    
    def test_get_field_names_excludes_timestamp(self, task_with_defaults):
        """Test that get_field_names excludes timestamp."""
        names = task_with_defaults.get_field_names()
        
        info = task_with_defaults.get_schema_info()
        # Should have one less than total (timestamp excluded)
        assert len(names) == info['field_count'] - 1


class TestThreadSafety:
    """Test thread-safe setup."""
    
    def test_multiple_setups(self, schema_file):
        """Test that setup can be called multiple times safely."""
        task1 = CsvToSenMLParse()
        task1.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': schema_file,
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task1.setup()
        
        task2 = CsvToSenMLParse()
        task2.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': schema_file,
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task2.setup()
        
        # Both should have same schema
        assert task1.get_schema_info() == task2.get_schema_info()


class TestStateManagement:
    """Test state management and cleanup."""
    
    def test_tear_down(self, task_with_schema):
        """Test that tear_down works without errors."""
        task_with_schema.execute("2024-01-01,25,60,1000")
        task_with_schema.tear_down()
        # Should complete without error
    
    def test_multiple_conversions(self, task_with_schema):
        """Test multiple conversions in sequence."""
        data1 = "2024-01-01,25,60,1000"
        data2 = "2024-01-02,22,55,1010"
        data3 = "2024-01-03,28,65,995"
        
        result1 = task_with_schema.execute(data1)
        result2 = task_with_schema.execute(data2)
        result3 = task_with_schema.execute(data3)
        
        senml1 = json.loads(result1)
        senml2 = json.loads(result2)
        senml3 = json.loads(result3)
        
        assert senml1['bt'] == "2024-01-01"
        assert senml2['bt'] == "2024-01-02"
        assert senml3['bt'] == "2024-01-03"


class TestRealWorldScenarios:
    """Test realistic IoT data scenarios."""
    
    def test_weather_station(self, tmp_path):
        """Test weather station data conversion."""
        schema = tmp_path / "weather.txt"
        schema.write_text(
            "timestamp,temperature,humidity,pressure,wind_speed\n"
            ",C,%,hPa,m/s\n"
            ",v,v,v,v\n"
        )
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        result = task.execute("2024-01-01 12:00:00,22.5,65,1013.25,3.5")
        senml = json.loads(result)
        
        assert senml['bt'] == "2024-01-01 12:00:00"
        assert len(senml['e']) == 4
        
        # Check temperature entry
        temp_entry = next(e for e in senml['e'] if e['n'] == 'temperature')
        assert temp_entry['v'] == '22.5'
        assert temp_entry['u'] == 'C'
    
    def test_smart_home_sensors(self, tmp_path):
        """Test smart home multi-sensor data."""
        schema = tmp_path / "smart_home.txt"
        schema.write_text(
            "timestamp,room,occupancy,temp,light_level\n"
            ",,persons,C,lux\n"
            ",s,v,v,v\n"
        )
        
        task = CsvToSenMLParse()
        task.config = {
            'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH': str(schema),
            'PARSE.CSV_SENML_USE_MSG_FIELD': '0'
        }
        task.setup()
        
        result = task.execute("2024-01-01,living_room,2,21.5,450")
        senml = json.loads(result)
        
        assert len(senml['e']) == 4
        
        # Check room (string type)
        room_entry = next(e for e in senml['e'] if e['n'] == 'room')
        assert room_entry['s'] == 'living_room'
