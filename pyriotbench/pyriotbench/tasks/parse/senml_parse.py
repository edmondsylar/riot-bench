"""SenML Parse task - parse Sensor Markup Language (SenML) JSON format.

This module implements parsing for the SenML data format used in IoT benchmarks.
SenML is a standard JSON format for representing sensor measurements.

**SenML Format**:
```
timestamp,{"e":[{"u":"unit","n":"name","sv":"string_value"},{"v":"value","u":"unit","n":"name"}],"bt":"base_time"}
```

**Example Input** (CSV line):
```
1358101800000,{"e":[{"u":"string","n":"taxi_id","sv":"ABC123"},{"v":"40.7","u":"lat","n":"latitude"}],"bt":1358101800000}
```

**Output** (Parsed dict):
```python
{
    "timestamp": 1358101800000,
    "base_time": 1358101800000,
    "measurements": [
        {"unit": "string", "name": "taxi_id", "string_value": "ABC123"},
        {"value": 40.7, "unit": "lat", "name": "latitude"}
    ]
}
```
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pyriotbench.core import BaseTask, register_task


@register_task("senml_parse")
class SenMLParseTask(BaseTask):
    """
    Parse SenML (Sensor Markup Language) JSON format from CSV input.
    
    SenML is a standard format for representing sensor measurements in JSON.
    This task parses CSV lines containing timestamp + SenML JSON payload.
    
    **Input Format**:
    - CSV string: "timestamp,{senml_json}"
    - timestamp: Unix milliseconds
    - senml_json: JSON object with 'e' (entries) and 'bt' (base time)
    
    **Output**:
    - Parsed dictionary with structured sensor measurements
    - Extracts timestamp, base_time, and measurements array
    - Handles both numeric values ('v') and string values ('sv')
    
    **Use Cases**:
    - IoT sensor data ingestion
    - Time-series data preprocessing
    - Multi-sensor data parsing
    - Real-time stream parsing
    
    **Example**:
    ```python
    task = SenMLParseTask()
    task.setup()
    
    # Input: CSV line with SenML JSON
    input_line = '1234567890,{"e":[{"v":"23.5","u":"celsius","n":"temp"}],"bt":"1234567890"}'
    
    # Parse
    result = task.execute(input_line)
    
    # Output: Structured dict
    print(result["measurements"][0]["name"])  # "temp"
    print(result["measurements"][0]["value"])  # "23.5"
    
    task.tear_down()
    ```
    
    **Performance**:
    - Typical execution: 50-200μs per record
    - Depends on JSON complexity and number of measurements
    - Minimal memory footprint
    """
    
    def setup(self) -> None:
        """
        Setup the SenML Parse task.
        
        No special configuration needed - uses Python's built-in JSON parser.
        """
        super().setup()
        self._logger.info("SenMLParseTask initialized - ready to parse sensor data")
        self._parse_count = 0
        self._error_count = 0
    
    def do_task(self, input_data: Any) -> Dict[str, Any]:
        """
        Parse SenML JSON format from CSV input line.
        
        **Input Formats Accepted**:
        1. CSV string: "timestamp,{json}"
        2. Dict with 'value' key containing CSV string
        3. Already parsed dict (pass-through)
        
        Args:
            input_data: CSV line string or dict
            
        Returns:
            Parsed dictionary with:
            - timestamp: Unix milliseconds (int)
            - base_time: Base timestamp from SenML (int)
            - measurements: List of measurement dicts
            
        Raises:
            ValueError: If input format is invalid
            json.JSONDecodeError: If JSON is malformed
            
        Examples:
            >>> task = SenMLParseTask()
            >>> task.setup()
            >>> 
            >>> # CSV string input
            >>> result = task.do_task('123,{"e":[{"v":"1.0","n":"x"}],"bt":"123"}')
            >>> result["timestamp"]
            123
            >>> 
            >>> # Dict input with 'value' key
            >>> result = task.do_task({"value": '456,{"e":[],"bt":"456"}'})
            >>> result["timestamp"]
            456
        """
        # Handle different input formats
        if isinstance(input_data, dict):
            # Already parsed or dict with 'value' key
            if "timestamp" in input_data and "measurements" in input_data:
                # Already parsed, return as-is
                return input_data
            
            # Extract CSV string from 'value' key
            if "value" in input_data:
                input_data = input_data["value"]
            else:
                raise ValueError(
                    "Dict input must have 'value' key or be already parsed "
                    "(with 'timestamp' and 'measurements' keys)"
                )
        
        # Convert to string if needed
        if not isinstance(input_data, str):
            input_data = str(input_data)
        
        # Parse CSV line: "timestamp,{json}"
        parts = input_data.split(",", 1)
        
        if len(parts) != 2:
            raise ValueError(
                f"Invalid SenML CSV format. Expected 'timestamp,{{json}}', got: {input_data[:100]}"
            )
        
        timestamp_str, json_str = parts
        
        # Parse timestamp
        try:
            timestamp = int(timestamp_str.strip())
        except ValueError as e:
            raise ValueError(f"Invalid timestamp: {timestamp_str}") from e
        
        # Parse JSON payload
        try:
            senml_data = json.loads(json_str.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {json_str[:100]}...") from e
        
        # Extract SenML fields
        base_time = senml_data.get("bt")
        if base_time is not None:
            # Convert base_time to int if it's a string
            if isinstance(base_time, str):
                try:
                    base_time = int(base_time)
                except ValueError:
                    base_time = timestamp
            elif not isinstance(base_time, int):
                base_time = timestamp
        else:
            base_time = timestamp
        
        entries = senml_data.get("e", [])
        
        # Parse measurements
        measurements = []
        for entry in entries:
            measurement = {
                "name": entry.get("n", ""),
                "unit": entry.get("u", ""),
            }
            
            # Handle numeric value
            if "v" in entry:
                measurement["value"] = entry["v"]
            
            # Handle string value
            if "sv" in entry:
                measurement["string_value"] = entry["sv"]
            
            # Handle boolean value
            if "bv" in entry:
                measurement["boolean_value"] = entry["bv"]
            
            # Add time offset if present
            if "t" in entry:
                measurement["time_offset"] = entry["t"]
            
            measurements.append(measurement)
        
        self._parse_count += 1
        
        return {
            "timestamp": timestamp,
            "base_time": base_time,
            "measurements": measurements,
            "raw_entry_count": len(entries),
        }
    
    def tear_down(self) -> None:
        """
        Cleanup and log parsing statistics.
        """
        super().tear_down()
        self._logger.info(
            f"SenMLParseTask complete - parsed {self._parse_count} records, "
            f"{self._error_count} errors"
        )
