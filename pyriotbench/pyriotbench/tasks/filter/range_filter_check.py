"""
RangeFilterCheck Task - Validate sensor values against configured ranges.

This task checks if sensor observation values fall within specified valid ranges.
It's useful for detecting outliers, sensor malfunctions, or out-of-bounds readings.

Configuration Format:
    FILTER.RANGE_FILTER.VALID_RANGE: "field1:min1:max1,field2:min2:max2,..."
    
    Each range specification has three parts separated by colons:
    - field: The observation type/field name (e.g., "TEMP", "HUM")
    - min: Minimum valid value (inclusive)
    - max: Maximum valid value (inclusive)
    
    Multiple ranges are separated by commas.

Examples:
    # Temperature 0-50°C, Humidity 0-100%, Pressure 950-1050 hPa
    "TEMP:0:50,HUM:0:100,PRESSURE:950:1050"
    
    # Single field validation
    "SPEED:0:120"

Behavior:
    - Returns 1.0 if ALL specified fields are within their ranges
    - Returns 0.0 if ANY field is out of range
    - Ignores fields not present in the configuration
    - Logs warnings for malformed values or parsing errors

Usage:
    >>> from pyriotbench.tasks.filter import RangeFilterCheck
    >>> task = RangeFilterCheck()
    >>> task.config = {
    ...     'FILTER.RANGE_FILTER.VALID_RANGE': 'TEMP:15:30,HUM:20:80'
    ... }
    >>> task.setup()
    >>> # Valid reading
    >>> result = task.execute('TEMP:25,HUM:60')  # Returns 1.0
    >>> # Out of range
    >>> result = task.execute('TEMP:35,HUM:60')  # Returns 0.0
"""

import threading
from typing import ClassVar, Dict, Optional, Tuple

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import StatefulTask


@register_task('range_filter_check')
class RangeFilterCheck(StatefulTask):
    """
    Validate sensor values against configured min/max ranges.
    
    This task checks multiple sensor fields against their valid ranges
    and returns 1.0 if all are valid, 0.0 if any are out of range.
    
    Thread-safe with class-level configuration and instance-level state.
    
    Attributes:
        _valid_ranges: Dictionary mapping field names to (min, max) tuples
        _field_list: List of field names to check
        _setup_lock: Thread lock for one-time setup
        _setup_done: Flag to ensure setup runs once
    """
    
    # Class variables (shared across all instances, thread-safe)
    _valid_ranges: ClassVar[Dict[str, Tuple[float, float]]] = {}
    _field_list: ClassVar[list] = []
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def __init__(self):
        """Initialize the task."""
        super().__init__()
    
    def setup(self) -> None:
        """
        Setup configuration for range validation.
        
        Parses the VALID_RANGE configuration string and builds lookup structures.
        Format: "field1:min1:max1,field2:min2:max2,..."
        """
        super().setup()
        
        # Always reload configuration (prevents test contamination)
        with self._setup_lock:
            # Reset state
            RangeFilterCheck._valid_ranges = {}
            RangeFilterCheck._field_list = []
            
            # Parse range configuration
            range_config = self.config.get('FILTER.RANGE_FILTER.VALID_RANGE', '')
            
            if not range_config or not range_config.strip():
                self._logger.warning("No VALID_RANGE configured, filter will always pass")
                RangeFilterCheck._setup_done = True
                return
            
            # Split by comma to get individual range specs
            range_specs = range_config.split(',')
            
            for spec in range_specs:
                spec = spec.strip()
                if not spec:
                    continue
                
                # Split by colon: field:min:max
                parts = spec.split(':')
                
                if len(parts) != 3:
                    self._logger.warning(f"Invalid range entry (expected field:min:max): {spec}")
                    continue
                
                field, min_str, max_str = parts
                field = field.strip()
                
                try:
                    min_val = float(min_str)
                    max_val = float(max_str)
                    
                    if min_val > max_val:
                        self._logger.warning(
                            f"Invalid range for {field}: min ({min_val}) > max ({max_val})"
                        )
                        continue
                    
                    RangeFilterCheck._valid_ranges[field] = (min_val, max_val)
                    RangeFilterCheck._field_list.append(field)
                    
                except ValueError as e:
                    self._logger.warning(
                        f"Error parsing range values for {field}: {min_str}, {max_str} - {e}"
                    )
                    continue
            
            RangeFilterCheck._setup_done = True
        
        self._logger.debug(
            f"RangeFilterCheck setup: {len(self._valid_ranges)} ranges configured - "
            f"{dict(self._valid_ranges)}"
        )
    
    def do_task(self, data: str) -> Optional[float]:
        """
        Check if sensor values are within configured ranges.
        
        Parses the input data as key:value pairs and checks each configured
        field against its valid range.
        
        Args:
            data: Input data as "field1:value1,field2:value2,..."
                  or map-style data
        
        Returns:
            1.0 if all checked fields are within range
            0.0 if any field is out of range
            None on parsing error
        """
        # Parse input data into a map
        data_map = self._parse_input(data)
        
        if not data_map:
            self._logger.debug("No valid data parsed from input")
            return 1.0  # No data to check, pass by default
        
        # Check each configured field
        is_valid = True
        
        for field in self._field_list:
            if field not in data_map:
                # Field not present in data, skip it
                continue
            
            value_str = data_map[field]
            
            try:
                value = float(value_str)
            except ValueError:
                self._logger.warning(
                    f"Cannot parse value '{value_str}' for field {field} as float"
                )
                is_valid = False
                continue
            
            # Get range for this field
            min_val, max_val = self._valid_ranges[field]
            
            # Check if value is in range
            if value < min_val or value > max_val:
                self._logger.debug(
                    f"Value {value} for {field} out of range [{min_val}, {max_val}]"
                )
                is_valid = False
        
        return 1.0 if is_valid else 0.0
    
    def _parse_input(self, data: str) -> Dict[str, str]:
        """
        Parse input string into a field→value map.
        
        Supports formats:
        - "field1:value1,field2:value2" (colon-separated pairs)
        - "value1,value2,value3" (comma-separated values, no field names)
        
        Args:
            data: Input string
        
        Returns:
            Dictionary mapping field names to string values
        """
        data_map = {}
        
        if not data or not data.strip():
            return data_map
        
        # Try to parse as field:value pairs
        pairs = data.split(',')
        
        for pair in pairs:
            pair = pair.strip()
            if not pair:
                continue
            
            if ':' in pair:
                # Format: "field:value"
                parts = pair.split(':', 1)  # Split on first colon only
                if len(parts) == 2:
                    field, value = parts
                    data_map[field.strip()] = value.strip()
            else:
                # No colon, might be a simple value - skip
                pass
        
        return data_map
    
    def tear_down(self) -> None:
        """Clean up task state."""
        super().tear_down()
    
    def get_configured_ranges(self) -> Dict[str, Tuple[float, float]]:
        """
        Get the configured valid ranges.
        
        Returns:
            Dictionary mapping field names to (min, max) tuples
        """
        return dict(self._valid_ranges)
    
    def get_configured_fields(self) -> list:
        """
        Get the list of fields being checked.
        
        Returns:
            List of field names
        """
        return list(self._field_list)
