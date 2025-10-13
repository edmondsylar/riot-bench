"""
Second Order Moment Task - Variance/Distribution Surprise Detection.

This task implements the Alon-Matias-Szegedy algorithm to estimate the second
order moment of data streams. The second moment measures distribution uniformity -
larger values indicate more non-uniform distributions, useful for anomaly detection.

Based on: Java RIoTBench SecondOrderMoment.java
"""

import threading
from collections import defaultdict
from typing import Any, ClassVar, Dict, Optional
import random

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import StatefulTask


@register_task("second_order_moment")
class SecondOrderMoment(StatefulTask):
    """
    Estimates second order moment (variance) using Alon-Matias-Szegedy algorithm.
    
    The second moment measures distribution uniformity. Higher values indicate
    more non-uniform distributions, useful for detecting anomalies or unusual
    patterns in streaming data. Uses space-efficient algorithm with bounded memory.
    
    Algorithm: Alon-Matias-Szegedy for frequency moment estimation
    - Maintains sparse array of item frequencies
    - When capacity reached, replaces random items
    - Calculates surprise number: Σ(counter * (2 * freq - 1)) / num_items
    
    Configuration:
        STATISTICS.MOMENT.USE_MSG_FIELD: Field index in CSV (0=random, >0=specific field)
        STATISTICS.MOMENT.MAX_HASHMAPSIZE: Maximum items to track (default: 100)
    
    Input Format:
        String (CSV format) or float value
        - If USE_MSG_FIELD > 0: Extract from CSV field
        - If USE_MSG_FIELD = 0: Use entire value or generate random
    
    Returns:
        Float: Surprise number (second order moment estimate)
               Higher values = more non-uniform distribution
    
    Example:
        >>> task = SecondOrderMoment()
        >>> task.config = {
        ...     'STATISTICS.MOMENT.USE_MSG_FIELD': 0,
        ...     'STATISTICS.MOMENT.MAX_HASHMAPSIZE': 100,
        ... }
        >>> task.setup()
        >>> # Process stream of values
        >>> task.execute("25.5")  # Returns moment estimate
        >>> task.execute("25.5")  # Same value again
        >>> task.execute("30.0")  # Different value
        >>> # Moment increases with more diverse values
    """
    
    # Class variables (shared configuration)
    _use_msg_field: ClassVar[int] = 0
    _max_map_size: ClassVar[int] = 100
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def setup(self) -> None:
        """
        Setup second order moment configuration (thread-safe).
        
        Loads configuration parameters. Each task instance maintains
        separate tracking state for frequency estimation.
        """
        super().setup()
        
        with self._setup_lock:
            # Always reload configuration to avoid test contamination
            self.__class__._use_msg_field = int(
                self.config.get('STATISTICS.MOMENT.USE_MSG_FIELD', 0)
            )
            
            self.__class__._max_map_size = int(
                self.config.get('STATISTICS.MOMENT.MAX_HASHMAPSIZE', 100)
            )
            
            if not self._setup_done:
                self._logger.info(
                    f"SecondOrderMoment configured: "
                    f"use_field={self._use_msg_field}, "
                    f"max_size={self._max_map_size}"
                )
                
                self.__class__._setup_done = True
        
        # Instance state (unique per task instance)
        # Map: item value -> index in freq/items arrays
        self.item_to_index: Dict[float, int] = {}
        # Parallel arrays for efficient access
        self.freq: list[int] = [0] * self._max_map_size  # Frequency counts
        self.items: list[float] = [0.0] * self._max_map_size  # Item values
        self.next_avail_index: int = 0  # Next available slot
        self.counter: int = 0  # Total items seen
        
        self._logger.debug("SecondOrderMoment instance initialized")
    
    def do_task(self, input_data: Any) -> Optional[float]:
        """
        Calculate second order moment estimate.
        
        Implements Alon-Matias-Szegedy algorithm:
        1. Extract item value from input
        2. Update frequency tracking (add new or increment existing)
        3. When capacity full, replace random item
        4. Calculate surprise number as second moment estimate
        
        Args:
            input_data: String (CSV) or numeric value
        
        Returns:
            Float: Surprise number (second order moment estimate)
                   Higher values indicate more non-uniform distribution
        
        Raises:
            ValueError: If input cannot be parsed
        """
        try:
            # Extract item value based on configuration
            if self._use_msg_field > 0:
                # Extract from CSV field
                if isinstance(input_data, str):
                    fields = input_data.split(',')
                    if self._use_msg_field - 1 < len(fields):
                        item = float(fields[self._use_msg_field - 1].strip())
                    else:
                        self._logger.warning(
                            f"Field {self._use_msg_field} out of range, using random"
                        )
                        item = random.random()
                else:
                    item = float(input_data)
            elif self._use_msg_field == 0:
                # Use entire value or generate random if string
                if isinstance(input_data, str):
                    try:
                        item = float(input_data.strip())
                    except ValueError:
                        # Non-numeric string, use random
                        item = random.random()
                else:
                    item = float(input_data)
            else:
                # Negative field number - always random
                item = random.random()
            
            # Increment counter
            self.counter += 1
            
            # Update frequency tracking
            self._update_frequency(item)
            
            # Calculate second order moment (surprise number)
            surprise_number = self._calculate_moment()
            
            self._logger.debug(
                f"Item {item:.3f}: counter={self.counter}, "
                f"unique={len(self.item_to_index)}, moment={surprise_number:.2f}"
            )
            
            return surprise_number
        
        except Exception as e:
            self._logger.error(f"Exception in second_order_moment do_task: {e}")
            return None
    
    def _update_frequency(self, item: float) -> None:
        """
        Update frequency tracking for an item.
        
        Implements Alon-Matias-Szegedy update logic:
        - If item exists: increment its frequency
        - If item new and space available: add to end
        - If item new and no space: replace random existing item
        
        Args:
            item: Item value to track
        """
        if item in self.item_to_index:
            # Item already tracked - increment frequency
            item_index = self.item_to_index[item]
            self.freq[item_index] += 1
            
            self._logger.debug(
                f"Incremented {item}: freq={self.freq[item_index]}"
            )
        else:
            # New item
            if len(self.item_to_index) < self._max_map_size:
                # Have spare capacity - add to end
                index = self.next_avail_index
                self.item_to_index[item] = index
                self.freq[index] = 1
                self.items[index] = item
                self.next_avail_index += 1
                
                self._logger.debug(
                    f"Added new item {item} at index {index}"
                )
            else:
                # No spare capacity - replace random item
                # Pick random index to replace
                rnd_index = random.randint(0, self._max_map_size - 1)
                old_item = self.items[rnd_index]
                
                # Remove old item from map
                del self.item_to_index[old_item]
                
                # Add new item
                self.item_to_index[item] = rnd_index
                self.freq[rnd_index] = 1
                self.items[rnd_index] = item
                
                self._logger.debug(
                    f"Replaced item {old_item} with {item} at index {rnd_index}"
                )
    
    def _calculate_moment(self) -> float:
        """
        Calculate second order moment using Alon-Matias-Szegedy formula.
        
        Formula: Σ(counter * (2 * freq_i - 1)) / num_unique_items
        
        This provides an unbiased estimate of the true second moment
        (sum of squared frequencies) while using bounded memory.
        
        Returns:
            Float: Surprise number (second order moment estimate)
        """
        if len(self.item_to_index) == 0:
            return 0.0
        
        surprise_number = 0.0
        
        # Sum over all tracked items
        for item, index in self.item_to_index.items():
            freq = self.freq[index]
            # Alon-Matias-Szegedy formula component
            surprise_number += self.counter * (2 * freq - 1)
        
        # Normalize by number of unique items
        surprise_number = surprise_number / len(self.item_to_index)
        
        return surprise_number
    
    def tear_down(self) -> None:
        """Cleanup resources and reset state."""
        super().tear_down()
        self.item_to_index.clear()
        self.freq = [0] * self._max_map_size
        self.items = [0.0] * self._max_map_size
        self.next_avail_index = 0
        self.counter = 0
    
    def get_tracked_items(self) -> Dict[float, int]:
        """
        Get currently tracked items and their frequencies.
        
        Returns:
            Dictionary mapping item values to their frequencies
        """
        return {
            item: self.freq[index] 
            for item, index in self.item_to_index.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current tracking statistics.
        
        Returns:
            Dictionary with counter, unique items, and moment estimate
        """
        return {
            'counter': self.counter,
            'unique_items': len(self.item_to_index),
            'capacity_used': len(self.item_to_index) / self._max_map_size,
            'moment': self._calculate_moment(),
        }
