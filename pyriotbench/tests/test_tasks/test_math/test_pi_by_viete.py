"""
Tests for PiByViete task - π calculation using Viète's formula.
"""

import math
import pytest
from pyriotbench.core.registry import TaskRegistry
from pyriotbench.tasks.math.pi_by_viete import PiByViete


@pytest.fixture
def pi_task():
    """Create a PiByViete task with default configuration."""
    task = PiByViete()
    task.config = {
        'MATH.PI_VIETE.ITERS': 1600  # Default iterations
    }
    task.setup()
    return task


@pytest.fixture
def low_precision_task():
    """Create task with fewer iterations for testing."""
    task = PiByViete()
    task.config = {
        'MATH.PI_VIETE.ITERS': 10  # Very few iterations (low precision)
    }
    task.setup()
    return task


class TestPiByVieteBasics:
    """Test basic functionality and setup."""
    
    def test_task_registration(self):
        """Test that task is properly registered."""
        assert TaskRegistry.is_registered('pi_by_viete')
        task_class = TaskRegistry.get('pi_by_viete')
        assert task_class == PiByViete
    
    def test_setup(self, pi_task):
        """Test task setup with configuration."""
        assert pi_task._iterations == 1600
    
    def test_setup_custom_iterations(self):
        """Test setup with custom iteration count."""
        task = PiByViete()
        task.config = {'MATH.PI_VIETE.ITERS': 500}
        task.setup()
        assert task._iterations == 500


class TestPiCalculation:
    """Test π calculation accuracy."""
    
    def test_calculate_pi_default(self, pi_task):
        """Test π calculation with default iterations."""
        result = pi_task.execute('dummy')
        
        assert result is not None
        assert isinstance(result, float)
        
        # Should be close to actual π
        actual_pi = math.pi
        assert abs(result - actual_pi) < 0.0001  # Within 0.01% error
    
    def test_calculate_pi_high_precision(self):
        """Test π calculation with many iterations."""
        task = PiByViete()
        task.config = {'MATH.PI_VIETE.ITERS': 2000}
        task.setup()
        
        result = task.execute('ignored')
        actual_pi = math.pi
        
        # Should be very accurate
        assert abs(result - actual_pi) < 0.00001
    
    def test_calculate_pi_low_precision(self, low_precision_task):
        """Test π calculation with few iterations."""
        result = low_precision_task.execute('test')
        
        # Should still be somewhat close to π
        assert 3.0 <= result <= 3.3  # Rough approximation
    
    def test_input_ignored(self, pi_task):
        """Test that input data is ignored."""
        result1 = pi_task.execute('input1')
        result2 = pi_task.execute('input2')
        result3 = pi_task.execute('')
        
        # All should return same π value
        assert result1 == result2 == result3
    
    def test_consistency(self, pi_task):
        """Test that multiple calls return same result."""
        results = [pi_task.execute('test') for _ in range(5)]
        
        # All results should be identical
        assert len(set(results)) == 1
    
    def test_convergence_with_iterations(self):
        """Test that more iterations give better accuracy."""
        actual_pi = math.pi
        errors = []
        
        for iters in [10, 50, 100, 500, 1000]:
            task = PiByViete()
            task.config = {'MATH.PI_VIETE.ITERS': iters}
            task.setup()
            result = task.execute('test')
            error = abs(result - actual_pi)
            errors.append(error)
        
        # Errors should generally decrease (with some exceptions due to algorithm)
        # At minimum, last error should be less than first
        assert errors[-1] < errors[0]


class TestVieteAlgorithm:
    """Test the Viète formula implementation."""
    
    def test_static_method(self):
        """Test the static calculation method."""
        result = PiByViete._calculate_pi_viete(1600)
        
        assert isinstance(result, float)
        assert abs(result - math.pi) < 0.0001
    
    def test_minimal_iterations(self):
        """Test with minimal iterations."""
        result = PiByViete._calculate_pi_viete(2)
        
        # Should give some approximation of π
        assert 2.5 <= result <= 3.5
    
    def test_different_iteration_counts(self):
        """Test various iteration counts."""
        for n in [5, 10, 50, 100, 500, 1000, 1600]:
            result = PiByViete._calculate_pi_viete(n)
            assert 3.0 <= result <= 3.2  # Should be in reasonable range


class TestErrorMetrics:
    """Test error calculation utilities."""
    
    def test_get_pi_exact(self):
        """Test getting exact π value."""
        exact = PiByViete.get_pi_exact()
        assert exact == math.pi
    
    def test_calculate_error_perfect(self):
        """Test error calculation with exact π."""
        metrics = PiByViete.calculate_error(math.pi)
        
        assert metrics['calculated'] == math.pi
        assert metrics['actual'] == math.pi
        assert metrics['absolute_error'] == 0.0
        assert metrics['relative_error'] == 0.0
        assert metrics['percent_error'] == 0.0
    
    def test_calculate_error_approximation(self, pi_task):
        """Test error calculation with approximation."""
        result = pi_task.execute('test')
        metrics = PiByViete.calculate_error(result)
        
        assert metrics['calculated'] == result
        assert metrics['actual'] == math.pi
        assert metrics['absolute_error'] > 0
        assert metrics['relative_error'] > 0
        assert metrics['percent_error'] > 0
        assert metrics['absolute_error'] < 0.001  # Should be quite accurate
    
    def test_calculate_error_rough_approximation(self):
        """Test error calculation with rough approximation."""
        rough_pi = 3.14
        metrics = PiByViete.calculate_error(rough_pi)
        
        assert metrics['absolute_error'] > 0.001
        assert metrics['percent_error'] < 1.0  # Less than 1% error


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_iterations_rejected(self):
        """Test that zero iterations is rejected."""
        task = PiByViete()
        task.config = {'MATH.PI_VIETE.ITERS': 0}
        
        with pytest.raises(ValueError, match="must be > 0"):
            task.setup()
    
    def test_negative_iterations_rejected(self):
        """Test that negative iterations is rejected."""
        task = PiByViete()
        task.config = {'MATH.PI_VIETE.ITERS': -10}
        
        with pytest.raises(ValueError, match="must be > 0"):
            task.setup()
    
    def test_empty_input(self, pi_task):
        """Test with empty input string."""
        result = pi_task.execute('')
        assert result is not None
        assert abs(result - math.pi) < 0.0001
    
    def test_very_long_input(self, pi_task):
        """Test with very long input (still ignored)."""
        long_input = 'x' * 10000
        result = pi_task.execute(long_input)
        assert result is not None
        assert abs(result - math.pi) < 0.0001


class TestStateManagement:
    """Test state management and cleanup."""
    
    def test_tear_down(self, pi_task):
        """Test that tear_down works without errors."""
        pi_task.execute('test')
        pi_task.tear_down()
        # Should complete without error
    
    def test_multiple_setups(self):
        """Test that setup can be called multiple times."""
        task = PiByViete()
        
        task.config = {'MATH.PI_VIETE.ITERS': 100}
        task.setup()
        assert task._iterations == 100
        
        task.config = {'MATH.PI_VIETE.ITERS': 200}
        task.setup()
        assert task._iterations == 200  # Should be updated


class TestConfiguration:
    """Test configuration handling."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        task = PiByViete()
        task.config = {}
        task.setup()
        
        assert task._iterations == 1600  # Default
    
    def test_custom_configuration(self):
        """Test custom configuration."""
        task = PiByViete()
        task.config = {'MATH.PI_VIETE.ITERS': 800}
        task.setup()
        
        assert task._iterations == 800
    
    def test_string_iterations_converted(self):
        """Test that string iteration values are converted to int."""
        task = PiByViete()
        task.config = {'MATH.PI_VIETE.ITERS': '1000'}
        task.setup()
        
        assert task._iterations == 1000
        assert isinstance(task._iterations, int)


class TestAccuracyBenchmarks:
    """Test accuracy with known iteration counts."""
    
    def test_accuracy_100_iterations(self):
        """Test accuracy with 100 iterations."""
        result = PiByViete._calculate_pi_viete(100)
        error = abs(result - math.pi)
        
        # Should have reasonable accuracy
        assert error < 0.001
    
    def test_accuracy_1000_iterations(self):
        """Test accuracy with 1000 iterations."""
        result = PiByViete._calculate_pi_viete(1000)
        error = abs(result - math.pi)
        
        # Should have good accuracy
        assert error < 0.0001
    
    def test_accuracy_2000_iterations(self):
        """Test accuracy with 2000 iterations."""
        result = PiByViete._calculate_pi_viete(2000)
        error = abs(result - math.pi)
        
        # Should have very good accuracy
        assert error < 0.00001
    
    def test_relative_error_small(self, pi_task):
        """Test that relative error is small with default settings."""
        result = pi_task.execute('test')
        metrics = PiByViete.calculate_error(result)
        
        # Relative error should be less than 0.01%
        assert metrics['percent_error'] < 0.01
