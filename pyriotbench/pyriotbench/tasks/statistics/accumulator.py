"""
Accumulator Task - Simple Windowed Accumulation.

This task accumulates values in fixed-size windows and emits all collected
data when the window is full. It's used as a collector for downstream
visualization or analysis tasks that need batches of data.

Based on: Java RIoTBench AccumlatorTask.java
"""

import threading
from collections import defaultdict, deque
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import StatefulTask


@register_task("accumulator")
class Accumulator(StatefulTask):
    """
    Windowed accumulator for collecting batches of sensor data.
    
    Accumulates values in fixed-size windows across multiple sensors
    and observation types. When the window is full, emits all collected
    data and resets. Useful for batching data for visualization or
    downstream processing that works on data batches.
    
    Configuration:
        AGGREGATE.ACCUMULATOR.TUPLE_WINDOW_SIZE: Number of tuples per window
        AGGREGATE.ACCUMULATOR.MULTIVALUE_OBSTYPE: Comma-separated list of 
            observation types that contain multiple values separated by '#'
        AGGREGATE.ACCUMULATOR.META_TIMESTAMP_FIELD: Index of timestamp field 
            in META (0-based)
    
    Input Format:
        Dictionary with keys:
        - SENSORID: Sensor identifier
        - OBSTYPE: Observation type (e.g., "TEMP", "HUM", "SLR")
        - OBSVALUE: Observation value(s), may contain '#' for multi-value
        - META: Comma-separated metadata including timestamp
        - TS: Timestamp (optional, can be extracted from META)
    
    Returns:
        None during accumulation
        Dict[str, Dict[str, List[Tuple[str, str]]]] when window full:
            Nested structure: {sensor_obstype: {meta: [(value, timestamp), ...]}}
    
    Example:
        >>> task = Accumulator()
        >>> task.config = {
        ...     "AGGREGATE.ACCUMULATOR.TUPLE_WINDOW_SIZE": 3,
        ...     "AGGREGATE.ACCUMULATOR.MULTIVALUE_OBSTYPE": "SLR",
        ...     "AGGREGATE.ACCUMULATOR.META_TIMESTAMP_FIELD": 0,
        ... }
        >>> task.setup()
        >>> # Accumulate data
        >>> result = task.execute({
        ...     "SENSORID": "sensor_001",
        ...     "OBSTYPE": "TEMP",
        ...     "OBSVALUE": "25.5",
        ...     "META": "1234567890,location1",
        ... })
        >>> result  # None (1/3)
        >>> # ... after 3 tuples ...
        >>> result  # Returns nested dict with all accumulated data
    """
    
    # Class variables (shared configuration)
    _tuple_window_size: ClassVar[int] = 10
    _multivalue_obstype: ClassVar[List[str]] = []
    _timestamp_field: ClassVar[int] = 0
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def setup(self) -> None:
        """
        Setup accumulator configuration (thread-safe).
        
        Loads configuration parameters. Each task instance maintains
        separate accumulation state.
        """
        super().setup()
        
        with self._setup_lock:
            # Always reload configuration to avoid test contamination
            # Load configuration (shared across instances)
            self.__class__._tuple_window_size = int(
                self.config.get('AGGREGATE.ACCUMULATOR.TUPLE_WINDOW_SIZE', 10)
            )
            
            # Parse multi-value observation types
            multivalue_str = self.config.get(
                'AGGREGATE.ACCUMULATOR.MULTIVALUE_OBSTYPE', ''
            )
            if multivalue_str:
                self.__class__._multivalue_obstype = [
                    s.strip() for s in multivalue_str.split(',') if s.strip()
                ]
            else:
                self.__class__._multivalue_obstype = []
            
            self.__class__._timestamp_field = int(
                self.config.get('AGGREGATE.ACCUMULATOR.META_TIMESTAMP_FIELD', 0)
            )
            
            if not self._setup_done:
                self._logger.info(
                    f"Accumulator configured: "
                    f"window_size={self._tuple_window_size}, "
                    f"multivalue_types={self._multivalue_obstype}, "
                    f"timestamp_field={self._timestamp_field}"
                )
                
                self.__class__._setup_done = True
        
        # Instance state (unique per task instance)
        # Nested structure: {sensor_obstype: {meta: [(value, timestamp), ...]}}
        self.values_map: Dict[str, Dict[str, List[Tuple[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.counter: int = 0
        
        self._logger.debug("Accumulator instance initialized")
    
    def do_task(self, input_data: Any) -> Optional[Dict[str, Dict[str, List[Tuple[str, str]]]]]:
        """
        Accumulate value and emit batch when window full.
        
        Args:
            input_data: Dictionary with SENSORID, OBSTYPE, OBSVALUE, META, TS
        
        Returns:
            None during accumulation
            Dict of accumulated values when window is full
        
        Raises:
            ValueError: If required fields are missing
            KeyError: If input format is invalid
        """
        try:
            # Convert to dict if needed
            if isinstance(input_data, str):
                # Handle string input for compatibility
                self._logger.warning("String input not supported, expected dict")
                return None
            
            data_dict = dict(input_data) if not isinstance(input_data, dict) else input_data
            
            # Extract required fields
            sensor_id = data_dict.get('SENSORID', '')
            obs_type = data_dict.get('OBSTYPE', '')
            obs_value = data_dict.get('OBSVALUE', '')
            meta_values = data_dict.get('META', '')
            timestamp = data_dict.get('TS', '')
            
            if not sensor_id or not obs_type or not obs_value:
                self._logger.warning(
                    f"Missing required fields: SENSORID={sensor_id}, "
                    f"OBSTYPE={obs_type}, OBSVALUE={obs_value}"
                )
                return None
            
            # Parse metadata to extract timestamp and meta key
            meta_fields = meta_values.split(',') if meta_values else []
            
            # Extract timestamp from META if not provided separately
            if not timestamp and meta_fields and len(meta_fields) > self._timestamp_field:
                timestamp = meta_fields[self._timestamp_field].strip()
            elif not timestamp:
                timestamp = ""  # Fallback to empty string
            
            # Use last meta field as the meta key (similar to Java implementation)
            meta_key = meta_fields[-1].strip() if meta_fields else "default"
            
            # Create composite key: sensor_id + obs_type
            composite_key = f"{sensor_id}{obs_type}"
            
            # Handle multi-value observation types (e.g., SLR with '#' separator)
            # Check if obs_type is in the multi-value list
            is_multivalue = obs_type in self._multivalue_obstype
            
            if is_multivalue and '#' in obs_value:
                # Split multiple values
                values = obs_value.split('#')
                for value in values:
                    if value.strip():
                        self.values_map[composite_key][meta_key].append(
                            (value.strip(), timestamp)
                        )
            else:
                # Single value
                self.values_map[composite_key][meta_key].append(
                    (obs_value.strip(), timestamp)
                )
            
            # Increment counter
            self.counter += 1
            
            # Check if window is full
            if self.counter >= self._tuple_window_size:
                # Emit accumulated data
                result = dict(self.values_map)
                
                self._logger.debug(
                    f"Window full: {self.counter} tuples, "
                    f"{len(result)} unique sensor/obstype combinations"
                )
                
                # Reset accumulator
                self.values_map = defaultdict(lambda: defaultdict(list))
                self.counter = 0
                
                return result
            else:
                # Continue accumulating
                self._logger.debug(
                    f"Accumulating: {self.counter}/{self._tuple_window_size} tuples"
                )
                return None
        
        except Exception as e:
            self._logger.error(f"Exception in accumulator do_task: {e}")
            return None
    
    def tear_down(self) -> None:
        """Cleanup resources and reset accumulator state."""
        super().tear_down()
        self.values_map.clear()
        self.counter = 0
    
    def get_current_count(self) -> int:
        """
        Get current tuple count in window.
        
        Returns:
            Number of tuples accumulated so far
        """
        return self.counter
    
    def get_accumulated_keys(self) -> List[str]:
        """
        Get list of sensor/obstype combinations currently accumulated.
        
        Returns:
            List of composite keys (sensor_id + obs_type)
        """
        return list(self.values_map.keys())
