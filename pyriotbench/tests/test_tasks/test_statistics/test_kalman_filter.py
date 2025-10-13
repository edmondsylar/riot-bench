"""
Tests for KalmanFilterTask.

Tests cover:
- Task registration
- Setup and initialization
- State persistence across calls
- Noise reduction effectiveness
- Convergence behavior
- Field extraction
- Random mode
- Error handling
"""

import pytest

from pyriotbench.core.registry import TaskRegistry
from pyriotbench.tasks.statistics.kalman_filter import KalmanFilterTask


class TestKalmanFilterRegistration:
    """Test task registration and discovery."""
    
    def test_task_is_registered(self):
        """Test that KalmanFilterTask is registered."""
        assert TaskRegistry.is_registered("kalman_filter")
    
    def test_can_get_task_class(self):
        """Test retrieving task class from registry."""
        task_cls = TaskRegistry.get("kalman_filter")
        assert task_cls is KalmanFilterTask
    
    def test_can_create_task_instance(self):
        """Test creating task instance."""
        task = TaskRegistry.create("kalman_filter")
        assert isinstance(task, KalmanFilterTask)


class TestKalmanFilterSetup:
    """Test setup and initialization."""
    
    def test_setup_loads_config(self, kalman_config):
        """Test that setup loads configuration."""
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = kalman_config
        task.setup()
        
        assert KalmanFilterTask._q_process_noise == 0.1
        assert KalmanFilterTask._r_sensor_noise == 0.1
        assert task.p0_prior_error_cov == 1.0
        assert task.x0_previous_est == 0.0
    
    def test_setup_with_defaults(self):
        """Test setup with default configuration."""
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = {}
        task.setup()
        
        # Should use defaults
        assert KalmanFilterTask._q_process_noise == 0.1
        assert KalmanFilterTask._r_sensor_noise == 0.1
        assert task.p0_prior_error_cov == 1.0
    
    def test_setup_with_custom_values(self):
        """Test setup with custom parameter values."""
        # Reset state
        KalmanFilterTask._setup_done = False
        
        config = {
            'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.05,
            'STATISTICS.KALMAN_FILTER.SENSOR_NOISE': 0.2,
            'STATISTICS.KALMAN_FILTER.ESTIMATED_ERROR': 2.0,
        }
        
        task = KalmanFilterTask()
        task.config = config
        task.setup()
        
        assert KalmanFilterTask._q_process_noise == 0.05
        assert KalmanFilterTask._r_sensor_noise == 0.2
        assert task.p0_prior_error_cov == 2.0


class TestKalmanFilterStatePersistence:
    """Test that state persists across calls."""
    
    def test_state_updates_after_each_call(self, kalman_config):
        """Test that state is updated after processing measurement."""
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = kalman_config
        task.setup()
        
        initial_p0 = task.p0_prior_error_cov
        initial_x0 = task.x0_previous_est
        
        # Process measurement
        result = task.do_task("10.0")
        
        # State should have changed
        assert task.p0_prior_error_cov != initial_p0
        assert task.x0_previous_est != initial_x0
        assert result != 0.0
    
    def test_sequential_measurements(self, kalman_config):
        """Test processing sequence of measurements."""
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = kalman_config
        task.setup()
        
        measurements = [10.5, 10.2, 10.8, 10.1, 10.4]
        estimates = []
        
        for measurement in measurements:
            estimate = task.do_task(str(measurement))
            estimates.append(estimate)
        
        # Should have 5 estimates
        assert len(estimates) == 5
        
        # All estimates should be valid
        assert all(isinstance(e, float) and e != float('-inf') for e in estimates)
        
        # Estimates should be different (state is changing)
        assert len(set(estimates)) == 5
    
    def test_independent_instances_have_separate_state(self, kalman_config):
        """Test that different instances maintain separate state."""
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task1 = KalmanFilterTask()
        task1.config = kalman_config
        task1.setup()
        
        task2 = KalmanFilterTask()
        task2.config = kalman_config
        task2.setup()
        
        # Process different measurements
        result1 = task1.do_task("10.0")
        result2 = task2.do_task("20.0")
        
        # Results should be different
        assert result1 != result2
        
        # States should be independent
        assert task1.x0_previous_est != task2.x0_previous_est


class TestKalmanFilterNoiseReduction:
    """Test noise reduction effectiveness."""
    
    def test_reduces_noise_from_signal(self, kalman_config, noisy_signal):
        """Test that Kalman filter reduces noise."""
        measurements, true_value = noisy_signal
        
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = kalman_config
        task.setup()
        
        estimates = []
        for measurement in measurements:
            estimate = task.do_task(str(measurement))
            estimates.append(estimate)
        
        # Calculate errors
        measurement_errors = [abs(m - true_value) for m in measurements]
        estimate_errors = [abs(e - true_value) for e in estimates[-10:]]  # Last 10 (after convergence)
        
        avg_measurement_error = sum(measurement_errors) / len(measurement_errors)
        avg_estimate_error = sum(estimate_errors) / len(estimate_errors)
        
        # Filtered estimates should have lower error than raw measurements
        assert avg_estimate_error < avg_measurement_error
    
    def test_converges_to_true_value(self, kalman_config):
        """Test that filter converges to true value."""
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = kalman_config
        task.setup()
        
        true_value = 15.0
        # Add noise: true_value +/- 2.0
        import random
        random.seed(123)
        measurements = [true_value + random.uniform(-2.0, 2.0) for _ in range(30)]
        
        estimates = []
        for measurement in measurements:
            estimate = task.do_task(str(measurement))
            estimates.append(estimate)
        
        # Final estimate should be close to true value
        final_estimate = estimates[-1]
        assert abs(final_estimate - true_value) < 1.0  # Within 1.0 of true value


class TestKalmanFilterFieldExtraction:
    """Test CSV field extraction."""
    
    def test_extract_from_csv_field(self, kalman_config):
        """Test extracting measurement from CSV field."""
        config = kalman_config.copy()
        config['STATISTICS.KALMAN_FILTER.USE_MSG_FIELD'] = 2  # Second field
        
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = config
        task.setup()
        
        result = task.do_task("sensor_001,42.5,normal")
        
        # Should process successfully
        assert result != float('-inf')
        assert isinstance(result, float)
    
    def test_field_index_out_of_range(self, kalman_config):
        """Test field index out of range returns error."""
        config = kalman_config.copy()
        config['STATISTICS.KALMAN_FILTER.USE_MSG_FIELD'] = 10
        
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = config
        task.setup()
        
        result = task.do_task("sensor_001,42.5")
        assert result == float('-inf')


class TestKalmanFilterRandomMode:
    """Test random value generation mode."""
    
    def test_random_mode(self, kalman_config):
        """Test random mode generates values around 10.0."""
        config = kalman_config.copy()
        config['STATISTICS.KALMAN_FILTER.USE_MSG_FIELD'] = -1  # Random mode
        
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = config
        task.setup()
        
        # Run multiple times
        results = []
        for _ in range(20):
            result = task.do_task("ignored")
            results.append(result)
        
        # All results should be valid
        assert all(isinstance(r, float) and r != float('-inf') for r in results)
        
        # After convergence, should be around 10.0 (the random range center)
        final_estimates = results[-5:]  # Last 5
        avg_final = sum(final_estimates) / len(final_estimates)
        assert 8.0 < avg_final < 12.0  # Should be near 10.0


class TestKalmanFilterExecution:
    """Test full execution with timing."""
    
    def test_execute_records_timing(self, kalman_config):
        """Test that execute records timing metrics."""
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = kalman_config
        task.setup()
        
        result_value = task.execute("10.5")
        result = task.get_last_result()
        
        assert isinstance(result_value, float)
        assert result_value != float('-inf')
        assert result.value == result_value
        assert result.execution_time_ms > 0
        assert result.success is True
    
    def test_execute_with_error(self, kalman_config):
        """Test execute with invalid input."""
        config = kalman_config.copy()
        config['STATISTICS.KALMAN_FILTER.USE_MSG_FIELD'] = 10
        
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = config
        task.setup()
        
        result_value = task.execute("short")
        result = task.get_last_result()
        
        assert result_value == float('-inf')
        assert result.value == float('-inf')


class TestKalmanFilterTearDown:
    """Test teardown and cleanup."""
    
    def test_tear_down_resets_state(self, kalman_config):
        """Test that tear_down resets instance state."""
        # Reset state
        KalmanFilterTask._setup_done = False
        
        task = KalmanFilterTask()
        task.config = kalman_config
        task.setup()
        
        # Process some measurements
        task.do_task("10.0")
        task.do_task("11.0")
        
        # State should be non-zero
        assert task.x0_previous_est != 0.0
        
        # Tear down
        task.tear_down()
        
        # State should be reset
        assert task.x0_previous_est == 0.0
        assert task.p0_prior_error_cov == 1.0
