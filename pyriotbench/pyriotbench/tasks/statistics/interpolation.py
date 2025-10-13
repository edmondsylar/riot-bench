"""
Interpolation Task - Linear Interpolation for Missing Sensor Values.

This task performs linear interpolation to fill in missing ('null') sensor readings
based on a window of recent values. It's essential for maintaining data continuity
in IoT streams where sensors occasionally fail to report values.

Based on: Java RIoTBench Interpolation.java
"""

import threading
from collections import defaultdict, deque
from typing import Any, ClassVar, Dict, List, Optional, Set

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import StatefulTask


@register_task("interpolation")
class Interpolation(StatefulTask):
    """
    Linear interpolation for missing sensor values.
    
    Maintains a sliding window of recent values for each sensor+obstype combination.
    When a 'null' value is encountered, computes the average of values in the window
    as an interpolated estimate. Supports multiple observation types per sensor.
    
    Configuration:
        STATISTICS.INTERPOLATION.USE_MSG_FIELD: Comma-separated list of observation
            types to interpolate (e.g., "TEMP,HUM,PRESSURE")
        STATISTICS.INTERPOLATION.WINDOW_SIZE: Number of values to keep in history
            for interpolation (default: 5)
    
    Input Format:
        Dictionary with keys:
        - SENSORID: Sensor identifier
        - <OBSTYPE>: Observation type keys (TEMP, HUM, etc.) with values
        - Multiple obstypes can be present in single input dict
    
    Returns:
        Float: Interpolated value if input was 'null'
        Float: Original value if input was valid
        None: If obstype not in USE_MSG_FIELD or no history available
    
    Example:
        >>> task = Interpolation()
        >>> task.config = {
        ...     'STATISTICS.INTERPOLATION.USE_MSG_FIELD': 'TEMP,HUM',
        ...     'STATISTICS.INTERPOLATION.WINDOW_SIZE': 3,
        ... }
        >>> task.setup()
        >>> # Build history
        >>> task.execute({'SENSORID': 's1', 'TEMP': '25.0'})  # 25.0
        >>> task.execute({'SENSORID': 's1', 'TEMP': '26.0'})  # 26.0
        >>> task.execute({'SENSORID': 's1', 'TEMP': '27.0'})  # 27.0
        >>> # Missing value - interpolate
        >>> task.execute({'SENSORID': 's1', 'TEMP': 'null'})  # 26.0 (average)
    """
    
    # Class variables (shared configuration)
    _use_msg_field: ClassVar[Set[str]] = set()
    _window_size: ClassVar[int] = 5
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def setup(self) -> None:
        """
        Setup interpolation configuration (thread-safe).
        
        Loads configuration parameters. Each task instance maintains
        separate window state for different sensor+obstype combinations.
        """
        super().setup()
        
        with self._setup_lock:
            # Always reload configuration to avoid test contamination
            # Parse observation types to interpolate
            use_msg_field_str = self.config.get(
                'STATISTICS.INTERPOLATION.USE_MSG_FIELD', ''
            )
            if use_msg_field_str:
                self.__class__._use_msg_field = set(
                    field.strip() 
                    for field in use_msg_field_str.split(',') 
                    if field.strip()
                )
            else:
                self.__class__._use_msg_field = set()
            
            self.__class__._window_size = int(
                self.config.get('STATISTICS.INTERPOLATION.WINDOW_SIZE', 5)
            )
            
            if not self._setup_done:
                self._logger.info(
                    f"Interpolation configured: "
                    f"fields={self._use_msg_field}, "
                    f"window_size={self._window_size}"
                )
                
                self.__class__._setup_done = True
        
        # Instance state (unique per task instance)
        # Map: sensor_id+obstype -> deque of recent values
        self.values_map: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._window_size)
        )
        
        self._logger.debug("Interpolation instance initialized")
    
    def do_task(self, input_data: Any) -> Optional[float]:
        """
        Interpolate missing values using window history.
        
        Args:
            input_data: Dictionary with SENSORID and observation type keys
        
        Returns:
            Interpolated value (float) if input was 'null' and history exists
            Original value (float) if input was valid number
            None if no valid processing occurred
        
        Raises:
            ValueError: If input format is invalid
        """
        try:
            # Convert to dict if needed
            if not isinstance(input_data, dict):
                self._logger.warning("Input must be a dictionary")
                return None
            
            data_dict = dict(input_data)
            
            # Extract sensor ID
            sensor_id = data_dict.get('SENSORID', '')
            if not sensor_id:
                self._logger.warning("Missing SENSORID field")
                return None
            
            # Special case: window size 0 means no interpolation needed
            if self._window_size == 0:
                self._logger.debug("Window size is 0, interpolation disabled")
                return None
            
            # Process each observation type in the input
            result = None
            for obs_type in list(data_dict.keys()):
                # Skip non-observation fields
                if obs_type in ('SENSORID', 'META', 'TS'):
                    continue
                
                # Only process observation types we're configured for
                if obs_type not in self._use_msg_field:
                    continue
                
                obs_value = str(data_dict.get(obs_type, ''))
                
                # Create composite key: sensor_id + obs_type
                key = f"{sensor_id}{obs_type}"
                
                # Check if value is missing (null)
                if obs_value.lower() == 'null' or not obs_value:
                    # Need interpolation
                    if key in self.values_map and len(self.values_map[key]) > 0:
                        # Calculate average of window values
                        values = list(self.values_map[key])
                        interpolated = sum(values) / len(values)
                        
                        self._logger.debug(
                            f"Interpolated {obs_type} for {sensor_id}: "
                            f"{interpolated:.3f} (from {len(values)} values)"
                        )
                        
                        result = interpolated
                    else:
                        # No history yet, cannot interpolate
                        self._logger.debug(
                            f"Cannot interpolate {obs_type} for {sensor_id}: "
                            f"no history"
                        )
                        result = None
                else:
                    # Valid value - add to window
                    try:
                        value = float(obs_value)
                        self.values_map[key].append(value)
                        
                        self._logger.debug(
                            f"Added {obs_type}={value:.3f} for {sensor_id} "
                            f"(window size: {len(self.values_map[key])})"
                        )
                        
                        result = value
                    except ValueError as e:
                        self._logger.error(
                            f"Cannot parse {obs_type} value '{obs_value}': {e}"
                        )
                        result = None
            
            return result
        
        except Exception as e:
            self._logger.error(f"Exception in interpolation do_task: {e}")
            return None
    
    def tear_down(self) -> None:
        """Cleanup resources and reset window state."""
        super().tear_down()
        self.values_map.clear()
    
    def get_window_state(self) -> Dict[str, int]:
        """
        Get current window state for all sensor+obstype combinations.
        
        Returns:
            Dictionary mapping composite keys to current window sizes
        """
        return {key: len(window) for key, window in self.values_map.items()}
    
    def get_window_values(self, sensor_id: str, obs_type: str) -> List[float]:
        """
        Get current window values for a specific sensor+obstype.
        
        Args:
            sensor_id: Sensor identifier
            obs_type: Observation type
        
        Returns:
            List of values in the window (may be empty)
        """
        key = f"{sensor_id}{obs_type}"
        return list(self.values_map.get(key, []))
