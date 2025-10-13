"""
DistinctApproxCount Task - Approximate cardinality estimation using Durand-Flajolet algorithm.

This task estimates the number of distinct items in a data stream using the
Durand-Flajolet probabilistic counting algorithm. It uses logarithmic space
complexity O(log log n) where n is the cardinality.

Algorithm Overview:
1. Hash each item to get a bit pattern
2. Use first k bits to select one of m=2^k buckets
3. Count trailing zeros in remaining bits (the "rank")
4. Keep max rank seen for each bucket
5. Estimate cardinality: E = α * m * 2^(average_rank)

References:
- [1] "Loglog Counting of Large Cardinalities", Durand and Flajolet
      http://algo.inria.fr/flajolet/Publications/DuFl03-LNCS.pdf
- [2] "Mining of Massive Datasets", Leskovec et al, Sec 4.4.2

Configuration:
    AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS: Number of bits k for 2^k buckets (default: 10)
        - Higher k = more accuracy but more memory
        - k=10 gives 1024 buckets, good balance of accuracy vs memory
        - Should not exceed 31 (to avoid int overflow)
    AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD: CSV field to use (default: 0)
        - 0: Use entire message
        - Positive integer: Extract that field from CSV (1-indexed)
        - Negative: Use random value (for testing)

Example:
    >>> from pyriotbench.tasks.aggregate import DistinctApproxCount
    >>> task = DistinctApproxCount()
    >>> config = {
    ...     'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 10,
    ...     'AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD': 0
    ... }
    >>> task.setup(logger, config)
    >>> # Process stream
    >>> estimate1 = task.execute('item1')  # Returns current estimate
    >>> estimate2 = task.execute('item2')  # Estimate increases
    >>> estimate3 = task.execute('item1')  # Duplicate, estimate stays similar
"""

import hashlib
import random
import threading
from typing import ClassVar, Optional

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import StatefulTask


@register_task('distinct_approx_count')
class DistinctApproxCount(StatefulTask):
    """
    Approximate distinct count using Durand-Flajolet algorithm.
    
    This is a stateful task that maintains bucket state across multiple calls.
    Thread-safe with class-level configuration and instance-level state.
    
    Space Complexity: O(m) where m = 2^k buckets
    Time Complexity: O(1) per item
    Error: Approximately 1.3/sqrt(m) standard error
    
    Attributes:
        _k_bucket_param: Number of bits for bucket selection (class variable)
        _m_num_buckets: Number of buckets = 2^k (class variable)
        _use_msg_field: CSV field index to use (class variable)
        _setup_lock: Thread lock for one-time setup (class variable)
        _setup_done: Flag to ensure setup runs once (class variable)
        max_zeros: Array of max trailing zeros per bucket (instance variable)
    """
    
    # Class variables (shared across all instances, thread-safe)
    _k_bucket_param: ClassVar[int] = 10  # Default: 2^10 = 1024 buckets
    _m_num_buckets: ClassVar[int] = 1024
    _use_msg_field: ClassVar[int] = 0
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    # Durand-Flajolet magic number (statistically derived)
    _ALPHA: ClassVar[float] = 0.79402
    
    def __init__(self):
        """Initialize the task with empty state."""
        super().__init__()
        # Instance variables (per-task state)
        self.max_zeros: list[int] = []
    
    def setup(self) -> None:
        """
        Setup configuration for distinct counting.
        
        Thread-safe initialization of class variables (done once) and
        instance variables (done per task instance).
        """
        super().setup()
        
        # Always reload configuration (prevents test contamination)
        with self._setup_lock:
            # Parse configuration
            k = self.config.get('AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS', 10)
            DistinctApproxCount._k_bucket_param = int(k)
            
            # Validate k parameter (must not overflow int)
            if DistinctApproxCount._k_bucket_param > 31:
                raise ValueError(
                    f"BUCKETS parameter must be <= 31 (got {DistinctApproxCount._k_bucket_param})"
                )
            
            # Calculate number of buckets: m = 2^k
            DistinctApproxCount._m_num_buckets = 1 << DistinctApproxCount._k_bucket_param
            
            # Parse field selection
            field = self.config.get('AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD', 0)
            DistinctApproxCount._use_msg_field = int(field)
            
            DistinctApproxCount._setup_done = True
        
        # Initialize instance state (per-task)
        self.max_zeros = [0] * self._m_num_buckets
        
        self._logger.debug(
            f"DistinctApproxCount setup: k={self._k_bucket_param}, "
            f"m={self._m_num_buckets} buckets, field={self._use_msg_field}"
        )
    
    def do_task(self, data: str) -> Optional[float]:
        """
        Process one item and return current cardinality estimate.
        
        Steps:
        1. Extract item value (from CSV field or use entire message)
        2. Hash item to get bit pattern
        3. Use first k bits to select bucket
        4. Count trailing zeros in remaining bits
        5. Update max trailing zeros for that bucket
        6. Calculate cardinality estimate from all buckets
        
        Args:
            data: Input data (CSV string or plain value)
        
        Returns:
            Current estimate of distinct items seen so far
        """
        # Extract item to count
        item = self._extract_item(data)
        
        # Calculate cardinality estimate
        estimate = self._do_unique_count(item)
        
        return estimate
    
    def _extract_item(self, data: str) -> str:
        """
        Extract the item value from input data.
        
        Args:
            data: Raw input string
        
        Returns:
            Item string to hash and count
        """
        if self._use_msg_field > 0:
            # Extract specific CSV field (1-indexed)
            try:
                fields = data.split(',')
                if self._use_msg_field <= len(fields):
                    return fields[self._use_msg_field - 1].strip()
                else:
                    # Field out of range, use random
                    self._logger.warning(
                        f"Field {self._use_msg_field} out of range "
                        f"(have {len(fields)} fields), using random value"
                    )
                    return str(random.randint(0, 2**31 - 1))
            except (ValueError, IndexError) as e:
                self._logger.error(f"Error extracting field: {e}, using random value")
                return str(random.randint(0, 2**31 - 1))
        elif self._use_msg_field == 0:
            # Use entire message
            return data.strip()
        else:
            # Negative field: use random value (for testing)
            return str(random.randint(0, 2**31 - 1))
    
    def _do_unique_count(self, item: str) -> float:
        """
        Update cardinality estimate with new item.
        
        Implements the Durand-Flajolet algorithm:
        1. Hash item to get x
        2. Use first k bits of x as bucket id j
        3. Count trailing zeros ρ in remaining bits
        4. Update M[j] = max(M[j], ρ)
        5. Return E = α * m * 2^(average(M))
        
        Args:
            item: String item to add to count
        
        Returns:
            Current cardinality estimate
        """
        # Hash the item using SHA1 (like Java implementation)
        hash_bytes = hashlib.sha1(item.encode()).digest()
        
        # Convert to int (use first 4 bytes)
        x_hash_value = int.from_bytes(hash_bytes[:4], byteorder='big', signed=True)
        
        # Extract bucket id: j = first k bits (use mask)
        # m_num_buckets - 1 is a mask with k bits set to 1
        j_bucket_id = x_hash_value & (self._m_num_buckets - 1)
        
        # Count trailing zeros in remaining bits (shift right by k bits first)
        remaining_bits = x_hash_value >> self._k_bucket_param
        trailing_zeros = self._count_trailing_zeros(remaining_bits)
        
        # Update max trailing zeros for this bucket
        self.max_zeros[j_bucket_id] = max(
            self.max_zeros[j_bucket_id],
            trailing_zeros
        )
        
        # Calculate cardinality estimate
        # E = α * m * 2^(average_rank)
        sum_max_zeros = sum(self.max_zeros)
        avg_rank = sum_max_zeros / self._m_num_buckets
        estimate = self._ALPHA * self._m_num_buckets * (2 ** avg_rank)
        
        self._logger.debug(
            f"Item '{item[:20]}...' -> bucket {j_bucket_id}, "
            f"zeros {trailing_zeros}, estimate {estimate:.0f}"
        )
        
        return float(estimate)
    
    @staticmethod
    def _count_trailing_zeros(value: int) -> int:
        """
        Count trailing zeros in binary representation.
        
        This implements the ρ (rho) function from the Durand-Flajolet paper.
        Returns the position of the first 1-bit from the right (LSB).
        
        Args:
            value: Integer value to examine
        
        Returns:
            Number of trailing zeros (rank)
        """
        # Special case: all zeros
        if value == 0:
            return 31  # Avoid overflow, cap at 31
        
        # Count trailing zeros by shifting right
        count = 0
        while ((value >> count) & 1) == 0:
            count += 1
        
        return count
    
    def tear_down(self) -> None:
        """Clean up task state."""
        self.max_zeros = [0] * self._m_num_buckets
        super().tear_down()
    
    def get_current_estimate(self) -> float:
        """
        Get current cardinality estimate without processing new item.
        
        Returns:
            Current estimate of distinct items
        """
        if not self.max_zeros or all(z == 0 for z in self.max_zeros):
            return 0.0
        
        sum_max_zeros = sum(self.max_zeros)
        avg_rank = sum_max_zeros / self._m_num_buckets
        estimate = self._ALPHA * self._m_num_buckets * (2 ** avg_rank)
        
        return float(estimate)
    
    def get_bucket_stats(self) -> dict:
        """
        Get statistics about bucket utilization.
        
        Returns:
            Dictionary with bucket statistics
        """
        non_zero_buckets = sum(1 for z in self.max_zeros if z > 0)
        max_rank = max(self.max_zeros) if self.max_zeros else 0
        avg_rank = sum(self.max_zeros) / len(self.max_zeros) if self.max_zeros else 0
        
        return {
            'total_buckets': self._m_num_buckets,
            'used_buckets': non_zero_buckets,
            'utilization': non_zero_buckets / self._m_num_buckets if self._m_num_buckets > 0 else 0,
            'max_rank': max_rank,
            'avg_rank': avg_rank,
            'current_estimate': self.get_current_estimate()
        }
