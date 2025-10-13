"""
Block Window Average Task - Windowed Aggregation.

This task accumulates values in fixed-size windows and emits the average
when the window is full. It's useful for reducing data volume while preserving
trends, and supports multiple sensors with independent windows.

Based on: Java RIoTBench BlockWindowAverage.java
"""

import threading
from collections import defaultdict
from typing import Any, ClassVar, Dict, List, Optional

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import StatefulTask


@register_task("block_window_average")
class BlockWindowAverage(StatefulTask):
    """
    Block window average aggregation.
    
    Accumulates values in fixed-size windows and emits average when
    window is full. Supports multiple sensors with independent windows.
    Useful for reducing data volume while preserving trends.
    
    Configuration:
        AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE: Number of values per window
        AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD: Field index (0=single value, >0=CSV field)
        AGGREGATE.BLOCK_WINDOW_AVERAGE.SENSOR_ID_FIELD: Field index for sensor ID (0=use default)
    
    Returns:
        Average value (float) when window is full
        None when window is not yet full (no output)
    
    Example:
        >>> task = BlockWindowAverage()
        >>> task.config = {
        ...     "AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE": 3,
        ...     "AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD": 2,
        ...     "AGGREGATE.BLOCK_WINDOW_AVERAGE.SENSOR_ID_FIELD": 1,
        ... }
        >>> task.setup()
        >>> # Window accumulation (no output until full)
        >>> task.execute("sensor_001,25.0")  # Returns None (1/3)
        >>> task.execute("sensor_001,26.0")  # Returns None (2/3)
        >>> task.execute("sensor_001,27.0")  # Returns 26.0 (window full!)
    """
    
    # Class variables (shared configuration)
    _window_size: ClassVar[int] = 10
    _use_msg_field: ClassVar[int] = 0
    _sensor_id_field: ClassVar[int] = 0
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def setup(self) -> None:
        """
        Setup block window configuration (thread-safe).
        
        Loads configuration parameters. Each task instance maintains
        separate window state for different sensors.
        """
        super().setup()
        
        with self._setup_lock:
            if not self._setup_done:
                # Load configuration (shared across instances)
                self.__class__._window_size = int(
                    self.config.get('AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE', 10)
                )
                
                self.__class__._use_msg_field = int(
                    self.config.get('AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD', 0)
                )
                
                self.__class__._sensor_id_field = int(
                    self.config.get('AGGREGATE.BLOCK_WINDOW_AVERAGE.SENSOR_ID_FIELD', 0)
                )
                
                self._logger.info(
                    f"Block window average configured: "
                    f"window_size={self._window_size}, "
                    f"use_field={self._use_msg_field}, "
                    f"sensor_id_field={self._sensor_id_field}"
                )
                
                self.__class__._setup_done = True
        
        # Instance state (unique per task instance)
        # Each sensor has its own window
        self.windows: Dict[str, List[float]] = defaultdict(list)
        
        self._logger.debug("Block window average instance initialized")
    
    def do_task(self, input_data: Any) -> Optional[float]:
        """
        Accumulate value and emit average when window full.
        
        Args:
            input_data: Input string (CSV format or single value)
        
        Returns:
            Average value (float) when window is full
            None when window is not yet full
        
        Raises:
            ValueError: If value cannot be extracted
        """
        # Parse input
        try:
            fields = str(input_data).strip().split(',')
            
            # Extract sensor ID
            if self._sensor_id_field > 0:
                if self._sensor_id_field - 1 >= len(fields):
                    self._logger.warning(
                        f"Sensor ID field {self._sensor_id_field} out of range "
                        f"(only {len(fields)} fields available)"
                    )
                    return float('-inf')
                sensor_id = fields[self._sensor_id_field - 1].strip()
            else:
                sensor_id = "default"
            
            # Extract value
            if self._use_msg_field > 0:
                if self._use_msg_field - 1 >= len(fields):
                    self._logger.warning(
                        f"Value field {self._use_msg_field} out of range "
                        f"(only {len(fields)} fields available)"
                    )
                    return float('-inf')
                value = float(fields[self._use_msg_field - 1].strip())
            elif len(fields) == 1:
                # Single value
                value = float(fields[0].strip())
            else:
                # Multiple fields, no field specified - use last field
                value = float(fields[-1].strip())
        
        except (ValueError, IndexError) as e:
            self._logger.error(f"Failed to extract value: {e}")
            return float('-inf')
        
        # Add to window
        self.windows[sensor_id].append(value)
        
        # Check if window is full
        if len(self.windows[sensor_id]) >= self._window_size:
            # Calculate average
            window_values = self.windows[sensor_id]
            avg = sum(window_values) / len(window_values)
            
            # Reset window
            self.windows[sensor_id].clear()
            
            self._logger.debug(
                f"Window full for {sensor_id}: "
                f"{len(window_values)} values, avg={avg:.3f}"
            )
            
            return avg
        else:
            # Window not full yet, no output
            self._logger.debug(
                f"Accumulating for {sensor_id}: "
                f"{len(self.windows[sensor_id])}/{self._window_size}"
            )
            return None
    
    def tear_down(self) -> None:
        """Cleanup resources and reset windows."""
        super().tear_down()
        # Clear all windows
        self.windows.clear()
    
    def get_window_state(self) -> Dict[str, int]:
        """
        Get current window state for all sensors.
        
        Returns:
            Dictionary mapping sensor_id to current window size
        """
        return {sensor_id: len(window) for sensor_id, window in self.windows.items()}
