"""
Bloom Filter Check Task - Probabilistic Set Membership Testing.

This task loads a pre-trained Bloom filter and checks if input values
are likely members of the set. Bloom filters are space-efficient probabilistic
data structures that can test whether an element is a member of a set.

Based on: Java RIoTBench BloomFilterCheck.java
"""

import logging
import pickle
import random
import threading
from pathlib import Path
from typing import Any, ClassVar, Optional

from pybloom_live import BloomFilter

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import BaseTask


@register_task("bloom_filter_check")
class BloomFilterCheck(BaseTask):
    """
    Bloom filter membership check task.
    
    Loads a pre-trained Bloom filter and checks if input values
    are likely members of the set. Uses probabilistic data structure
    for memory-efficient set membership testing.
    
    Configuration:
        FILTER.BLOOM_FILTER.MODEL_PATH: Path to serialized bloom filter
        FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD: Field index (0=random, >0=field)
        FILTER.BLOOM_FILTER_CHECK.TESTING_RANGE: Range for random value generation
    
    Returns:
        1.0 if element is (probably) in the set
        0.0 if element is definitely not in the set
    
    Example:
        >>> task = BloomFilterCheck()
        >>> task.config = {"FILTER.BLOOM_FILTER.MODEL_PATH": "filter.pkl"}
        >>> task.setup()
        >>> result = task.execute("sensor123,42.5,normal")
        >>> print(result.value)  # 1.0 or 0.0
    """
    
    # Class variables (shared across all instances)
    _bloom_filter: ClassVar[Optional[BloomFilter]] = None
    _use_msg_field: ClassVar[int] = 0
    _testing_range: ClassVar[int] = 20000000
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def setup(self) -> None:
        """
        Setup bloom filter (thread-safe, executed once).
        
        Loads the bloom filter model from disk. Uses thread-safe
        initialization to ensure the model is loaded only once
        even when running with multiple threads.
        """
        super().setup()
        
        with self._setup_lock:
            if not self._setup_done:
                # Load configuration
                model_path_str = self.config.get('FILTER.BLOOM_FILTER.MODEL_PATH')
                if not model_path_str:
                    raise ValueError("FILTER.BLOOM_FILTER.MODEL_PATH not configured")
                
                model_path = Path(model_path_str).expanduser()
                
                self.__class__._use_msg_field = int(
                    self.config.get('FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD', 0)
                )
                
                self.__class__._testing_range = int(
                    self.config.get('FILTER.BLOOM_FILTER_CHECK.TESTING_RANGE', 20000000)
                )
                
                # Load bloom filter from pickle file
                try:
                    with open(model_path, 'rb') as f:
                        self.__class__._bloom_filter = pickle.load(f)
                    
                    self._logger.info(
                        f"Loaded bloom filter from {model_path} "
                        f"(use_field={self._use_msg_field}, "
                        f"testing_range={self._testing_range})"
                    )
                except FileNotFoundError:
                    raise FileNotFoundError(
                        f"Bloom filter model not found: {model_path}"
                    )
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to load bloom filter from {model_path}: {e}"
                    )
                
                self.__class__._setup_done = True
    
    def do_task(self, input_data: Any) -> float:
        """
        Check if value is in bloom filter.
        
        Args:
            input_data: Input string (CSV format or single value)
        
        Returns:
            1.0 if element is (probably) in the set
            0.0 if element is definitely not in the set
        
        Raises:
            RuntimeError: If bloom filter not loaded
        """
        if self._bloom_filter is None:
            raise RuntimeError("Bloom filter not initialized. Call setup() first.")
        
        # Extract test value
        if self._use_msg_field > 0:
            # Use specific field from CSV
            try:
                fields = str(input_data).split(',')
                if self._use_msg_field - 1 >= len(fields):
                    self._logger.warning(
                        f"Field index {self._use_msg_field} out of range "
                        f"(only {len(fields)} fields available)"
                    )
                    return float('-inf')  # Error sentinel
                
                test_value = fields[self._use_msg_field - 1].strip()
            except Exception as e:
                self._logger.error(f"Failed to extract field: {e}")
                return float('-inf')
        else:
            # Generate random value for testing (0=random mode)
            test_value = str(random.randint(0, self._testing_range - 1))
        
        # Check membership
        try:
            is_member = test_value in self._bloom_filter
            
            self._logger.debug(
                f"Bloom filter check: '{test_value}' -> "
                f"{'MEMBER' if is_member else 'NOT_MEMBER'}"
            )
            
            return 1.0 if is_member else 0.0
            
        except Exception as e:
            self._logger.error(f"Bloom filter check failed: {e}")
            return float('-inf')
    
    def tear_down(self) -> None:
        """Cleanup resources."""
        super().tear_down()
        # Note: We don't clear class variables here as they may be shared
        # across multiple task instances
