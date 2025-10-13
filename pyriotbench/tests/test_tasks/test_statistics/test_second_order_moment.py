"""
Tests for SecondOrderMoment task.
"""

import pytest
from pyriotbench.tasks.statistics.second_order_moment import SecondOrderMoment


@pytest.fixture
def moment_task():
    """Create second order moment task with default config."""
    task = SecondOrderMoment()
    task.config = {
        'STATISTICS.MOMENT.USE_MSG_FIELD': 0,
        'STATISTICS.MOMENT.MAX_HASHMAPSIZE': 100,
    }
    task.setup()
    return task


@pytest.fixture
def small_capacity_task():
    """Create task with small capacity for testing replacement."""
    task = SecondOrderMoment()
    task.config = {
        'STATISTICS.MOMENT.USE_MSG_FIELD': 0,
        'STATISTICS.MOMENT.MAX_HASHMAPSIZE': 5,
    }
    task.setup()
    return task


class TestSecondOrderMomentBasics:
    """Test basic second order moment functionality."""
    
    def test_task_registration(self):
        """Test second_order_moment is registered."""
        from pyriotbench.core.registry import TaskRegistry
        assert TaskRegistry.is_registered('second_order_moment')
        task = TaskRegistry.create('second_order_moment')
        task.config = {}
        assert isinstance(task, SecondOrderMoment)
    
    def test_setup(self, moment_task):
        """Test setup configures parameters."""
        assert moment_task._use_msg_field == 0
        assert moment_task._max_map_size == 100
        assert moment_task.counter == 0
        assert len(moment_task.item_to_index) == 0
    
    def test_initial_state(self, moment_task):
        """Test initial state before any data."""
        stats = moment_task.get_stats()
        assert stats['counter'] == 0
        assert stats['unique_items'] == 0
        assert stats['moment'] == 0.0


class TestFrequencyTracking:
    """Test frequency tracking logic."""
    
    def test_single_item_once(self, moment_task):
        """Test tracking single item once."""
        result = moment_task.execute("10.0")
        
        assert result is not None
        assert moment_task.counter == 1
        assert len(moment_task.item_to_index) == 1
        
        tracked = moment_task.get_tracked_items()
        assert tracked[10.0] == 1
    
    def test_same_item_multiple_times(self, moment_task):
        """Test same item increases frequency."""
        for _ in range(5):
            moment_task.execute("10.0")
        
        assert moment_task.counter == 5
        assert len(moment_task.item_to_index) == 1
        
        tracked = moment_task.get_tracked_items()
        assert tracked[10.0] == 5
    
    def test_multiple_different_items(self, moment_task):
        """Test tracking multiple different items."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for val in values:
            moment_task.execute(str(val))
        
        assert moment_task.counter == 5
        assert len(moment_task.item_to_index) == 5
        
        tracked = moment_task.get_tracked_items()
        for val in values:
            assert tracked[val] == 1
    
    def test_mixed_frequencies(self, moment_task):
        """Test items with different frequencies."""
        # Add items with varying frequencies
        moment_task.execute("10.0")  # freq=1
        moment_task.execute("20.0")  # freq=1
        moment_task.execute("20.0")  # freq=2
        moment_task.execute("30.0")  # freq=1
        moment_task.execute("20.0")  # freq=3
        
        tracked = moment_task.get_tracked_items()
        assert tracked[10.0] == 1
        assert tracked[20.0] == 3
        assert tracked[30.0] == 1


class TestCapacityManagement:
    """Test capacity management and replacement logic."""
    
    def test_fill_to_capacity(self, small_capacity_task):
        """Test filling exactly to capacity."""
        for i in range(5):
            small_capacity_task.execute(str(float(i)))
        
        assert len(small_capacity_task.item_to_index) == 5
        stats = small_capacity_task.get_stats()
        assert stats['capacity_used'] == 1.0
    
    def test_replacement_when_full(self, small_capacity_task):
        """Test item replacement when capacity reached."""
        # Fill capacity with 5 items
        for i in range(5):
            small_capacity_task.execute(str(float(i)))
        
        # Add 6th item - should replace one
        small_capacity_task.execute("99.0")
        
        # Still 5 items, but one replaced
        assert len(small_capacity_task.item_to_index) == 5
        assert small_capacity_task.counter == 6
        
        # 99.0 should be present
        tracked = small_capacity_task.get_tracked_items()
        assert 99.0 in tracked
    
    def test_multiple_replacements(self, small_capacity_task):
        """Test multiple items trigger replacements."""
        # Fill with 0-4
        for i in range(5):
            small_capacity_task.execute(str(float(i)))
        
        # Add 5 more unique items (will cause replacements)
        for i in range(10, 15):
            small_capacity_task.execute(str(float(i)))
        
        # Should have 5 items (capacity), 10 items seen
        assert len(small_capacity_task.item_to_index) == 5
        assert small_capacity_task.counter == 10


class TestMomentCalculation:
    """Test second order moment calculation."""
    
    def test_uniform_distribution_low_moment(self, moment_task):
        """Test uniform distribution has lower moment."""
        # All items appear once - uniform distribution
        for i in range(10):
            moment_task.execute(str(float(i)))
        
        result = moment_task.execute("100.0")
        
        # Uniform distribution should have relatively low moment
        assert result is not None
        assert result > 0  # Some moment value
    
    def test_skewed_distribution_high_moment(self, moment_task):
        """Test skewed distribution has higher moment."""
        # One item appears many times - highly skewed
        for _ in range(50):
            moment_task.execute("10.0")
        
        # A few other items
        moment_task.execute("20.0")
        moment_task.execute("30.0")
        
        result = moment_task.execute("40.0")
        
        # Skewed distribution should have high moment
        assert result is not None
        assert result > 100  # Should be significantly high
    
    def test_moment_increases_with_duplicates(self, moment_task):
        """Test moment increases as duplicates appear."""
        # First item - baseline
        result1 = moment_task.execute("10.0")
        
        # Add different item
        result2 = moment_task.execute("20.0")
        
        # Repeat first item many times
        for _ in range(10):
            moment_task.execute("10.0")
        
        result3 = moment_task.execute("30.0")
        
        # Moment should increase with skew
        assert result3 > result2
    
    def test_moment_formula_correctness(self):
        """Test moment calculation matches expected formula."""
        task = SecondOrderMoment()
        task.config = {
            'STATISTICS.MOMENT.USE_MSG_FIELD': 0,
            'STATISTICS.MOMENT.MAX_HASHMAPSIZE': 100,
        }
        task.setup()
        
        # Add 3 items: 10.0 (freq=2), 20.0 (freq=1), 30.0 (freq=1)
        task.execute("10.0")
        task.execute("10.0")
        task.execute("20.0")
        result = task.execute("30.0")
        
        # Counter = 4, frequencies = [2, 1, 1]
        # Surprise = (4*(2*2-1) + 4*(2*1-1) + 4*(2*1-1)) / 3
        #          = (4*3 + 4*1 + 4*1) / 3
        #          = (12 + 4 + 4) / 3 = 20 / 3 = 6.666...
        assert abs(result - 6.666666) < 0.01


class TestFieldExtraction:
    """Test field extraction from CSV."""
    
    def test_extract_first_field(self):
        """Test extracting first field from CSV."""
        task = SecondOrderMoment()
        task.config = {
            'STATISTICS.MOMENT.USE_MSG_FIELD': 1,
            'STATISTICS.MOMENT.MAX_HASHMAPSIZE': 100,
        }
        task.setup()
        
        task.execute("25.5,50.0,75.0")
        
        tracked = task.get_tracked_items()
        assert 25.5 in tracked
    
    def test_extract_middle_field(self):
        """Test extracting middle field from CSV."""
        task = SecondOrderMoment()
        task.config = {
            'STATISTICS.MOMENT.USE_MSG_FIELD': 2,
            'STATISTICS.MOMENT.MAX_HASHMAPSIZE': 100,
        }
        task.setup()
        
        task.execute("25.5,50.0,75.0")
        
        tracked = task.get_tracked_items()
        assert 50.0 in tracked
    
    def test_field_out_of_range_uses_random(self):
        """Test field index out of range falls back to random."""
        task = SecondOrderMoment()
        task.config = {
            'STATISTICS.MOMENT.USE_MSG_FIELD': 10,  # Out of range
            'STATISTICS.MOMENT.MAX_HASHMAPSIZE': 100,
        }
        task.setup()
        
        result = task.execute("25.5,50.0")
        
        # Should use random, result should exist
        assert result is not None
        assert len(task.item_to_index) == 1
    
    def test_use_entire_value_numeric(self, moment_task):
        """Test using entire value when numeric string."""
        moment_task.execute("42.5")
        
        tracked = moment_task.get_tracked_items()
        assert 42.5 in tracked
    
    def test_non_numeric_string_uses_random(self, moment_task):
        """Test non-numeric string uses random value."""
        result = moment_task.execute("not_a_number")
        
        # Should generate random value
        assert result is not None
        assert len(moment_task.item_to_index) == 1


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_numeric_input(self, moment_task):
        """Test direct numeric input."""
        result = moment_task.execute(25.5)
        
        assert result is not None
        tracked = moment_task.get_tracked_items()
        assert 25.5 in tracked
    
    def test_zero_value(self, moment_task):
        """Test handling zero values."""
        moment_task.execute("0.0")
        moment_task.execute("0.0")
        
        tracked = moment_task.get_tracked_items()
        assert 0.0 in tracked
        assert tracked[0.0] == 2
    
    def test_negative_values(self, moment_task):
        """Test handling negative values."""
        moment_task.execute("-10.5")
        moment_task.execute("-10.5")
        
        tracked = moment_task.get_tracked_items()
        assert -10.5 in tracked
        assert tracked[-10.5] == 2
    
    def test_large_values(self, moment_task):
        """Test handling large values."""
        moment_task.execute("1000000.0")
        
        tracked = moment_task.get_tracked_items()
        assert 1000000.0 in tracked


class TestStateManagement:
    """Test state management and cleanup."""
    
    def test_tear_down_clears_state(self, moment_task):
        """Test tear_down clears all state."""
        # Add some data
        for i in range(5):
            moment_task.execute(str(float(i)))
        
        assert moment_task.counter > 0
        assert len(moment_task.item_to_index) > 0
        
        # Tear down
        moment_task.tear_down()
        
        assert moment_task.counter == 0
        assert len(moment_task.item_to_index) == 0
        assert moment_task.next_avail_index == 0
    
    def test_get_stats(self, moment_task):
        """Test get_stats returns correct information."""
        # Add data
        moment_task.execute("10.0")
        moment_task.execute("10.0")
        moment_task.execute("20.0")
        
        stats = moment_task.get_stats()
        
        assert stats['counter'] == 3
        assert stats['unique_items'] == 2
        assert 0 < stats['capacity_used'] < 1
        assert stats['moment'] > 0
    
    def test_capacity_used_calculation(self, small_capacity_task):
        """Test capacity_used is calculated correctly."""
        # Add 3 items to capacity of 5
        for i in range(3):
            small_capacity_task.execute(str(float(i)))
        
        stats = small_capacity_task.get_stats()
        assert stats['capacity_used'] == 0.6  # 3/5


class TestConfiguration:
    """Test configuration options."""
    
    def test_custom_max_hashmap_size(self):
        """Test custom max hashmap size."""
        task = SecondOrderMoment()
        task.config = {
            'STATISTICS.MOMENT.USE_MSG_FIELD': 0,
            'STATISTICS.MOMENT.MAX_HASHMAPSIZE': 10,
        }
        task.setup()
        
        assert task._max_map_size == 10
        
        # Fill capacity
        for i in range(15):
            task.execute(str(float(i)))
        
        # Should only have 10 items
        assert len(task.item_to_index) == 10
    
    def test_default_configuration(self):
        """Test default configuration values."""
        task = SecondOrderMoment()
        task.config = {}
        task.setup()
        
        assert task._use_msg_field == 0
        assert task._max_map_size == 100
    
    def test_negative_field_uses_random(self):
        """Test negative field number uses random values."""
        task = SecondOrderMoment()
        task.config = {
            'STATISTICS.MOMENT.USE_MSG_FIELD': -1,
            'STATISTICS.MOMENT.MAX_HASHMAPSIZE': 100,
        }
        task.setup()
        
        result = task.execute("10.0")
        
        # Should use random value, not 10.0
        assert result is not None
        tracked = task.get_tracked_items()
        # Random value was used, so 10.0 shouldn't be tracked
        # (unless by chance random == 10.0, very unlikely)
        assert len(tracked) == 1


class TestAnomalyDetection:
    """Test using moment for anomaly detection scenarios."""
    
    def test_detect_sudden_duplicate_burst(self, moment_task):
        """Test moment increases when duplicates suddenly appear."""
        # Uniform distribution initially
        for i in range(10):
            moment_task.execute(str(float(i)))
        
        moment_before = moment_task.execute("100.0")
        
        # Sudden burst of same value (anomaly)
        for _ in range(20):
            moment_task.execute("0.0")
        
        moment_after = moment_task.execute("101.0")
        
        # Moment should increase significantly
        assert moment_after > moment_before * 2
    
    def test_detect_distribution_shift(self, moment_task):
        """Test moment changes with distribution shift."""
        # Start with uniform
        for i in range(20):
            moment_task.execute(str(float(i)))
        
        baseline = moment_task.execute("100.0")
        
        # Shift to skewed (many duplicates of few values)
        for _ in range(10):
            moment_task.execute("5.0")
        for _ in range(10):
            moment_task.execute("10.0")
        
        shifted = moment_task.execute("101.0")
        
        # Should detect the shift
        assert shifted != baseline
