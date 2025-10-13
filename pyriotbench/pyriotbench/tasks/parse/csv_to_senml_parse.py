"""
CSV to SenML Parse Task - Convert CSV data to SenML JSON format.

This task converts comma-separated values (CSV) into SenML (Sensor Measurement Lists)
JSON format, which is a standard IoT data interchange format defined by RFC 8428.

The task reads a schema file that defines:
- Column names (field identifiers)
- Units (e.g., 'm', 'C', 'kg')
- Data types ('v' for numeric values, 's' for strings)

Example CSV input:
    "timestamp,temp,humidity,pressure"
    "2024-01-01 12:00:00,25.5,60,1013"

Example SenML output:
    {
        "bt": "2024-01-01 12:00:00",
        "e": [
            {"n": "temp", "v": "25.5", "u": "C"},
            {"n": "humidity", "v": "60", "u": "%"},
            {"n": "pressure", "v": "1013", "u": "hPa"}
        ]
    }

Configuration:
    PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH: Path to schema file (3 lines: columns, units, types)
    PARSE.CSV_SENML_USE_MSG_FIELD: Field index to use (-1 for sample data, 0+ for specific field)

Benchmark Characteristics:
    - Category: Parse
    - Complexity: Medium (schema loading, string parsing, JSON construction)
    - State: Stateful (schema loaded once in setup)
    - Dependencies: json (stdlib)
    - Memory: O(n) where n is number of fields
"""

import json
import csv
from typing import ClassVar, Optional, Dict, List, Tuple
from threading import Lock
from pathlib import Path

from pyriotbench.core.task import StatefulTask
from pyriotbench.core.registry import register_task


@register_task('csv_to_senml_parse')
class CsvToSenMLParse(StatefulTask):
    """
    Convert CSV data to SenML JSON format.
    
    This task reads a schema file that defines column names, units, and types,
    then converts CSV input into SenML format with proper base time and entries.
    
    SenML Format:
        - bt: Base time (from timestamp field)
        - e: Array of entries, each with:
            - n: Name (field name)
            - v/s: Value (numeric) or string value
            - u: Unit
    
    Attributes:
        _schema_map (ClassVar): Shared schema mapping (field_idx -> (name, unit, type))
        _timestamp_field (ClassVar): Index of timestamp field in schema
        _use_msg_field (ClassVar): Field index to use from input (-1 for sample)
        _sample_data (ClassVar): Sample CSV data for testing
        _setup_lock (ClassVar): Thread-safe setup lock
        _done_setup (ClassVar): Setup completion flag
    """
    
    # Class variables for shared configuration (thread-safe)
    _schema_map: ClassVar[Dict[int, Tuple[str, str, str]]] = {}
    _timestamp_field: ClassVar[int] = 0
    _use_msg_field: ClassVar[int] = -1
    _sample_data: ClassVar[str] = ""
    _setup_lock: ClassVar[Lock] = Lock()
    _done_setup: ClassVar[bool] = False
    
    def setup(self) -> None:
        """
        Load CSV schema from file.
        
        Schema file format (3 lines):
            Line 1: Column names (comma-separated)
            Line 2: Units (comma-separated)
            Line 3: Data types (comma-separated, 'v' for numeric, 's' for string)
        
        Example:
            timestamp,temp,humidity,pressure
            ,C,%,hPa
            ,v,v,v
        
        Raises:
            FileNotFoundError: If schema file doesn't exist
            ValueError: If schema file is malformed
        """
        with self._setup_lock:
            if not self._done_setup:
                try:
                    # Get configuration
                    schema_path = self.config.get(
                        'PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH',
                        ''
                    )
                    self.__class__._use_msg_field = int(
                        self.config.get('PARSE.CSV_SENML_USE_MSG_FIELD', '-1')
                    )
                    
                    if not schema_path:
                        self._logger.warning("No schema file configured, using defaults")
                        self._setup_default_schema()
                        self.__class__._done_setup = True
                        return
                    
                    # Read schema file
                    schema_file = Path(schema_path)
                    if not schema_file.exists():
                        raise FileNotFoundError(f"Schema file not found: {schema_path}")
                    
                    with open(schema_file, 'r') as f:
                        lines = [line.strip() for line in f.readlines()]
                    
                    if len(lines) < 3:
                        raise ValueError(
                            f"Schema file must have 3 lines (columns, units, types), got {len(lines)}"
                        )
                    
                    # Parse schema
                    columns = [col.strip() for col in lines[0].split(',')]
                    units = [unit.strip() for unit in lines[1].split(',')]
                    types = [dtype.strip() for dtype in lines[2].split(',')]
                    
                    if not (len(columns) == len(units) == len(types)):
                        raise ValueError(
                            f"Schema mismatch: columns={len(columns)}, "
                            f"units={len(units)}, types={len(types)}"
                        )
                    
                    # Build schema map
                    new_schema = {}
                    for i, (col, unit, dtype) in enumerate(zip(columns, units, types)):
                        if col == 'timestamp':
                            self.__class__._timestamp_field = i
                        new_schema[i] = (col, unit, dtype)
                    
                    self.__class__._schema_map = new_schema
                    
                    # Set sample data (for benchmarking with useMsgField=-1)
                    # Generate sample data that matches the schema
                    if self._timestamp_field < len(columns):
                        # Use realistic sample data from Java version
                        self.__class__._sample_data = (
                            "2013-01-14 03:57:00,25.5,60,1013"
                        )
                    else:
                        # Fallback sample
                        self.__class__._sample_data = ",".join(
                            ["2024-01-01"] + ["0"] * (len(columns) - 1)
                        )
                    
                    self._logger.info(
                        f"Loaded schema with {len(new_schema)} fields, "
                        f"timestamp at index {self._timestamp_field}"
                    )
                    
                    self.__class__._done_setup = True
                    
                except Exception as e:
                    self._logger.error(f"Failed to load schema: {e}")
                    raise
    
    def _setup_default_schema(self) -> None:
        """Setup a default schema for testing without a file."""
        default_schema = {
            0: ('timestamp', '', ''),
            1: ('temperature', 'C', 'v'),
            2: ('humidity', '%', 'v'),
            3: ('pressure', 'hPa', 'v'),
        }
        self.__class__._schema_map = default_schema
        self.__class__._timestamp_field = 0
        self.__class__._sample_data = "2024-01-01 12:00:00,25.5,60,1013"
        self._logger.info("Using default schema (4 fields)")
    
    def do_task(self, data: str) -> Optional[str]:
        """
        Convert CSV data to SenML JSON format.
        
        Args:
            data: CSV string (comma-separated values) or field:value pairs
        
        Returns:
            JSON string in SenML format with 'bt' (base time) and 'e' (entries)
            None if parsing fails
        
        Example:
            Input: "2024-01-01 12:00:00,25.5,60,1013"
            Output: '{"bt": "2024-01-01 12:00:00", "e": [...]}'
        """
        try:
            # Determine input to use
            if self._use_msg_field == -1:
                # Use sample data for benchmarking
                m = self._sample_data
            else:
                # Use provided data
                m = data.strip() if data else ""
            
            if not m:
                self._logger.warning("Empty input data")
                return None
            
            # Parse CSV values
            values = [val.strip() for val in m.split(',')]
            
            if len(values) < len(self._schema_map):
                self._logger.warning(
                    f"Input has {len(values)} fields, expected {len(self._schema_map)}"
                )
            
            # Build SenML structure
            base_time = values[self._timestamp_field] if self._timestamp_field < len(values) else ""
            entries = []
            
            for i in range(len(self._schema_map)):
                if i == self._timestamp_field:
                    continue  # Skip timestamp in entries
                
                if i >= len(values):
                    break  # No more values
                
                col_name, unit, dtype = self._schema_map[i]
                value = values[i]
                
                # Create entry
                entry = {
                    'n': col_name,
                    unit: value if dtype == 's' else value,  # 'v' for numeric, 's' for string
                    'u': unit
                }
                
                # Use proper key for value based on type
                if dtype == 'v':
                    entry['v'] = value
                elif dtype == 's':
                    entry['s'] = value
                else:
                    entry[dtype] = value  # Allow other types
                
                # Remove duplicate unit key if present
                if unit in entry and unit != 'u':
                    del entry[unit]
                
                entries.append(entry)
            
            # Create final SenML object
            senml = {
                'bt': base_time,
                'e': entries
            }
            
            result = json.dumps(senml)
            self._logger.debug(f"Converted {len(entries)} fields to SenML")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Failed to convert CSV to SenML: {e}")
            return None
    
    def get_schema_info(self) -> Dict[str, any]:
        """
        Get current schema information.
        
        Returns:
            Dictionary with schema details:
                - field_count: Number of fields
                - timestamp_field: Index of timestamp field
                - fields: List of (index, name, unit, type) tuples
        """
        fields = [
            (i, name, unit, dtype)
            for i, (name, unit, dtype) in sorted(self._schema_map.items())
        ]
        
        return {
            'field_count': len(self._schema_map),
            'timestamp_field': self._timestamp_field,
            'fields': fields,
            'use_msg_field': self._use_msg_field
        }
    
    def get_field_names(self) -> List[str]:
        """Get list of field names (excluding timestamp)."""
        return [
            name for i, (name, _, _) in sorted(self._schema_map.items())
            if i != self._timestamp_field
        ]
