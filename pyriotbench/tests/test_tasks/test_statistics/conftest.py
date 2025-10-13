"""Pytest configuration for statistics task tests."""

import pytest


@pytest.fixture
def kalman_config():
    """Standard Kalman filter configuration."""
    return {
        'STATISTICS.KALMAN_FILTER.USE_MSG_FIELD': 0,
        'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.1,
        'STATISTICS.KALMAN_FILTER.SENSOR_NOISE': 0.1,
        'STATISTICS.KALMAN_FILTER.ESTIMATED_ERROR': 1.0,
    }


@pytest.fixture
def noisy_signal():
    """Generate a noisy signal for testing (true value = 10.0)."""
    import random
    random.seed(42)  # Reproducible
    
    true_value = 10.0
    noise_stddev = 1.0
    
    # Generate 20 noisy measurements
    measurements = [
        true_value + random.gauss(0, noise_stddev)
        for _ in range(20)
    ]
    
    return measurements, true_value
