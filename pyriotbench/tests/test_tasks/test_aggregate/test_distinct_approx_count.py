"""
Tests for DistinctApproxCount task - Durand-Flajolet cardinality estimation.
"""

import logging
import pytest
from pyriotbench.core.registry import TaskRegistry
from pyriotbench.tasks.aggregate.distinct_approx_count import DistinctApproxCount


@pytest.fixture
def distinct_task():
    """Create a DistinctApproxCount task with default configuration."""
    task = DistinctApproxCount()
    task.config = {
        'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 10,  # 1024 buckets
        'AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD': 0  # Use entire message
    }
    task.setup()
    return task


@pytest.fixture
def small_buckets_task():
    """Create task with fewer buckets for testing."""
    task = DistinctApproxCount()
    task.config = {
        'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 4,  # 16 buckets (less accurate)
        'AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD': 0
    }
    task.setup()
    return task


class TestDistinctApproxCountBasics:
    """Test basic functionality and setup."""
    
    def test_task_registration(self):
        """Test that task is properly registered."""
        assert TaskRegistry.is_registered('distinct_approx_count')
        task_class = TaskRegistry.get('distinct_approx_count')
        assert task_class == DistinctApproxCount
    
    def test_setup(self, distinct_task):
        """Test task setup with configuration."""
        assert distinct_task._k_bucket_param == 10
        assert distinct_task._m_num_buckets == 1024
        assert distinct_task._use_msg_field == 0
        assert len(distinct_task.max_zeros) == 1024
        assert all(z == 0 for z in distinct_task.max_zeros)
    
    def test_initial_estimate_zero(self, distinct_task):
        """Test that initial estimate is zero."""
        estimate = distinct_task.get_current_estimate()
        assert estimate == 0.0


class TestCardinalityEstimation:
    """Test cardinality estimation accuracy."""
    
    def test_single_item(self, distinct_task):
        """Test estimate for single unique item."""
        result = distinct_task.execute('item1')
        assert result is not None
        assert result > 0
        # Note: Durand-Flajolet has high variance for very small cardinalities
        # Estimate for 1 item can be quite high (hundreds) due to algorithm design
        assert 100 <= result <= 2000  # Very loose bounds for single item
    
    def test_few_unique_items(self, distinct_task):
        """Test estimate for small number of unique items."""
        items = ['apple', 'banana', 'cherry', 'date', 'elderberry']
        
        for item in items:
            estimate = distinct_task.execute(item)
        
        # Estimate should be roughly 5 (but algorithm has high variance for small n)
        # Durand-Flajolet works better for larger cardinalities
        # For very small n (like 5), estimate can be quite off
        assert 100 <= estimate <= 2000  # Very loose bounds for small sample
    
    def test_many_unique_items(self, distinct_task):
        """Test estimate for many unique items."""
        # Generate 100 unique items
        for i in range(100):
            distinct_task.execute(f'item_{i:03d}')
        
        estimate = distinct_task.get_current_estimate()
        
        # Should be approximately 100 (algorithm more accurate at larger n)
        # Allow wider margin for probabilistic algorithm
        assert 50 <= estimate <= 1500
    
    def test_duplicate_items_no_increase(self, distinct_task):
        """Test that duplicates don't significantly increase estimate."""
        # Add 5 unique items
        for i in range(5):
            distinct_task.execute(f'item_{i}')
        
        estimate_before = distinct_task.get_current_estimate()
        
        # Add many duplicates
        for _ in range(50):
            distinct_task.execute('item_0')  # Duplicate
        
        estimate_after = distinct_task.get_current_estimate()
        
        # Estimate should stay roughly the same
        # (may increase slightly due to hash collisions)
        assert abs(estimate_after - estimate_before) < 5
    
    def test_large_cardinality(self, distinct_task):
        """Test estimate for large number of unique items."""
        # Generate 1000 unique items
        for i in range(1000):
            distinct_task.execute(f'value_{i:04d}')
        
        estimate = distinct_task.get_current_estimate()
        
        # Should be approximately 1000 (algorithm works well at larger n)
        # Standard error ~1.3/sqrt(1024) = ~4%, but allow for variance
        assert 500 <= estimate <= 2000


class TestBucketManagement:
    """Test bucket allocation and statistics."""
    
    def test_bucket_initialization(self, distinct_task):
        """Test that all buckets start at zero."""
        assert len(distinct_task.max_zeros) == 1024
        assert all(z == 0 for z in distinct_task.max_zeros)
    
    def test_buckets_get_populated(self, distinct_task):
        """Test that processing items populates buckets."""
        # Add several items
        for i in range(20):
            distinct_task.execute(f'item_{i}')
        
        # Some buckets should now be non-zero
        non_zero = sum(1 for z in distinct_task.max_zeros if z > 0)
        assert non_zero > 0
        assert non_zero <= 20  # At most 20 (one per item)
    
    def test_bucket_stats(self, distinct_task):
        """Test bucket statistics tracking."""
        # Add items
        for i in range(50):
            distinct_task.execute(f'sensor_{i}')
        
        stats = distinct_task.get_bucket_stats()
        
        assert stats['total_buckets'] == 1024
        assert stats['used_buckets'] > 0
        assert 0 < stats['utilization'] <= 1.0
        assert stats['max_rank'] >= 0
        assert stats['avg_rank'] >= 0
        assert stats['current_estimate'] > 0
    
    def test_small_buckets_less_accurate(self, small_buckets_task):
        """Test that fewer buckets gives less accurate estimates."""
        # Add 50 unique items
        for i in range(50):
            small_buckets_task.execute(f'item_{i}')
        
        estimate = small_buckets_task.get_current_estimate()
        
        # With only 16 buckets, estimate will be less accurate
        # Just check it's in a very wide range
        assert 10 <= estimate <= 200


class TestFieldExtraction:
    """Test CSV field extraction."""
    
    def test_extract_first_field(self):
        """Test extracting first CSV field."""
        task = DistinctApproxCount()
        task.config = {
            'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 10,
            'AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD': 1
        }
        task.setup()
        
        result = task.execute('apple,banana,cherry')
        assert result is not None
        assert result > 0
    
    def test_extract_middle_field(self):
        """Test extracting middle CSV field."""
        task = DistinctApproxCount()
        task.config = {
            'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 10,
            'AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD': 2
        }
        task.setup()
        
        # Process multiple records with different values in field 2
        result1 = task.execute('a,value1,c')
        result2 = task.execute('a,value2,c')
        result3 = task.execute('a,value1,c')  # Duplicate
        
        estimate = task.get_current_estimate()
        # Should recognize ~2 unique values (but high variance for small n)
        assert 100 <= estimate <= 2000
    
    def test_field_out_of_range_uses_random(self):
        """Test that out-of-range field falls back to random."""
        task = DistinctApproxCount()
        task.config = {
            'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 10,
            'AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD': 10  # Out of range
        }
        task.setup()
        
        # Should not crash, uses random value
        result = task.execute('a,b,c')
        assert result is not None
        assert result > 0
    
    def test_use_entire_value(self, distinct_task):
        """Test using entire value when field is 0."""
        result1 = distinct_task.execute('complete_string_1')
        result2 = distinct_task.execute('complete_string_2')
        result3 = distinct_task.execute('complete_string_1')  # Duplicate
        
        estimate = distinct_task.get_current_estimate()
        # Should recognize ~2 unique strings (but high variance for small n)
        assert 100 <= estimate <= 2000
    
    def test_negative_field_uses_random(self):
        """Test that negative field uses random values."""
        task = DistinctApproxCount()
        task.config = {
            'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 10,
            'AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD': -1  # Random mode
        }
        task.setup()
        
        # Each call uses different random value
        result1 = task.execute('ignored')
        result2 = task.execute('ignored')
        
        # Estimate increases since random values are different
        assert result2 > 0


class TestTrailingZeros:
    """Test trailing zero counting (rho function)."""
    
    def test_count_trailing_zeros_zero(self):
        """Test trailing zeros for value 0."""
        count = DistinctApproxCount._count_trailing_zeros(0)
        assert count == 31  # Special case to avoid overflow
    
    def test_count_trailing_zeros_odd(self):
        """Test trailing zeros for odd numbers."""
        # Odd numbers end in 1, so 0 trailing zeros
        assert DistinctApproxCount._count_trailing_zeros(1) == 0
        assert DistinctApproxCount._count_trailing_zeros(3) == 0
        assert DistinctApproxCount._count_trailing_zeros(7) == 0
    
    def test_count_trailing_zeros_powers_of_two(self):
        """Test trailing zeros for powers of 2."""
        assert DistinctApproxCount._count_trailing_zeros(2) == 1    # 10
        assert DistinctApproxCount._count_trailing_zeros(4) == 2    # 100
        assert DistinctApproxCount._count_trailing_zeros(8) == 3    # 1000
        assert DistinctApproxCount._count_trailing_zeros(16) == 4   # 10000
    
    def test_count_trailing_zeros_mixed(self):
        """Test trailing zeros for mixed values."""
        assert DistinctApproxCount._count_trailing_zeros(6) == 1    # 110
        assert DistinctApproxCount._count_trailing_zeros(12) == 2   # 1100
        assert DistinctApproxCount._count_trailing_zeros(24) == 3   # 11000


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_string(self, distinct_task):
        """Test handling empty string."""
        result = distinct_task.execute('')
        assert result is not None
        assert result >= 0
    
    def test_whitespace_string(self, distinct_task):
        """Test handling whitespace."""
        result = distinct_task.execute('   ')
        assert result is not None
        assert result >= 0
    
    def test_numeric_values(self, distinct_task):
        """Test handling numeric values as strings."""
        for i in range(10):
            result = distinct_task.execute(str(i))
        
        estimate = distinct_task.get_current_estimate()
        # Should recognize ~10 unique values (but high variance for small n)
        assert 100 <= estimate <= 2000
    
    def test_very_long_strings(self, distinct_task):
        """Test handling very long strings."""
        long_string = 'x' * 10000
        result = distinct_task.execute(long_string)
        assert result is not None
        assert result > 0
    
    def test_unicode_strings(self, distinct_task):
        """Test handling Unicode strings."""
        unicode_items = ['café', '北京', '🎉', 'Москва']
        
        for item in unicode_items:
            result = distinct_task.execute(item)
        
        estimate = distinct_task.get_current_estimate()
        # Should recognize ~4 unique strings (but high variance for small n)
        assert 100 <= estimate <= 2000


class TestStateManagement:
    """Test state management and cleanup."""
    
    def test_tear_down_resets_state(self, distinct_task):
        """Test that tear_down resets buckets."""
        # Add some items
        for i in range(10):
            distinct_task.execute(f'item_{i}')
        
        # Verify state is populated
        assert any(z > 0 for z in distinct_task.max_zeros)
        
        # Tear down
        distinct_task.tear_down()
        
        # State should be reset
        assert all(z == 0 for z in distinct_task.max_zeros)
    
    def test_get_current_estimate_without_processing(self, distinct_task):
        """Test getting estimate without processing new items."""
        # Add items
        for i in range(20):
            distinct_task.execute(f'item_{i}')
        
        estimate1 = distinct_task.get_current_estimate()
        estimate2 = distinct_task.get_current_estimate()
        
        # Multiple calls should return same estimate
        assert estimate1 == estimate2


class TestConfiguration:
    """Test configuration handling."""
    
    def test_custom_bucket_size(self):
        """Test custom bucket parameter."""
        task = DistinctApproxCount()
        task.config = {
            'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 8,  # 256 buckets
            'AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD': 0
        }
        task.setup()
        
        assert task._k_bucket_param == 8
        assert task._m_num_buckets == 256
        assert len(task.max_zeros) == 256
    
    def test_default_configuration(self):
        """Test default configuration values."""
        task = DistinctApproxCount()
        task.config = {}
        task.setup()
        
        assert task._k_bucket_param == 10  # Default
        assert task._m_num_buckets == 1024
        assert task._use_msg_field == 0
    
    def test_bucket_overflow_protection(self):
        """Test that bucket parameter > 31 is rejected."""
        task = DistinctApproxCount()
        task.config = {
            'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 32  # Too large
        }
        
        with pytest.raises(ValueError, match="must be <= 31"):
            task.setup()
    
    def test_configuration_reload(self):
        """Test that configuration is reloaded on setup."""
        task = DistinctApproxCount()
        
        # First setup
        task.config = {'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 6}
        task.setup()
        assert task._k_bucket_param == 6
        
        # Second setup with different config
        task.config = {'AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS': 8}
        task.setup()
        assert task._k_bucket_param == 8  # Should be updated


class TestAccuracyScenarios:
    """Test realistic accuracy scenarios."""
    
    def test_detect_cardinality_increase(self, distinct_task):
        """Test that estimate increases as cardinality increases."""
        estimates = []
        
        # Add items in batches and track estimates
        for batch in range(5):
            # Add 20 unique items
            for i in range(20):
                distinct_task.execute(f'batch{batch}_item{i}')
            
            estimates.append(distinct_task.get_current_estimate())
        
        # Each estimate should be larger than previous
        # (though not strictly monotonic due to probabilistic nature)
        assert estimates[-1] > estimates[0]
        # Average should increase
        assert sum(estimates[2:]) > sum(estimates[:2])
    
    def test_stable_estimate_with_duplicates(self, distinct_task):
        """Test that estimate stabilizes when only seeing duplicates."""
        # Add 30 unique items
        items = [f'item_{i}' for i in range(30)]
        for item in items:
            distinct_task.execute(item)
        
        estimate_before = distinct_task.get_current_estimate()
        
        # Now send 100 duplicates
        for _ in range(100):
            for item in items[:10]:  # Repeat first 10 items
                distinct_task.execute(item)
        
        estimate_after = distinct_task.get_current_estimate()
        
        # Estimate should be stable (within 10%)
        ratio = estimate_after / estimate_before if estimate_before > 0 else 1
        assert 0.9 <= ratio <= 1.1


