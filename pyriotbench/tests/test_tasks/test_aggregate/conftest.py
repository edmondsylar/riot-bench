"""
Pytest fixtures for Block Window Average tests.

Provides test data and configuration fixtures for block window aggregation tests.
"""

import pytest
from pyriotbench.tasks.aggregate.block_window_average import BlockWindowAverage


@pytest.fixture(autouse=True)
def reset_class_state():
    """Reset class state before each test to avoid cross-test contamination."""
    BlockWindowAverage._setup_done = False
    yield
    # Cleanup after test
    BlockWindowAverage._setup_done = False


@pytest.fixture
def window_config():
    """Basic window configuration (window size 3)."""
    return {
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 3,
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD': 0,
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.SENSOR_ID_FIELD': 0,
    }


@pytest.fixture
def multi_field_config():
    """Configuration for CSV input with field extraction."""
    return {
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 5,
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD': 2,  # Extract 2nd field
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.SENSOR_ID_FIELD': 0,
    }


@pytest.fixture
def multi_sensor_config():
    """Configuration for multi-sensor windowing."""
    return {
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 3,
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD': 2,  # Value in 2nd field
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.SENSOR_ID_FIELD': 1,  # Sensor ID in 1st field
    }


@pytest.fixture
def sensor_data():
    """Sample sensor readings for testing."""
    return [
        "sensor_001,25.0",
        "sensor_001,26.0",
        "sensor_001,27.0",
        "sensor_002,30.0",
        "sensor_002,31.0",
        "sensor_002,32.0",
    ]


@pytest.fixture
def temperature_stream():
    """Realistic temperature sensor stream."""
    return [
        "22.5",  # °C
        "23.1",
        "22.8",
        "23.4",
        "22.9",
        "23.2",
        "23.0",
        "22.7",
        "23.3",
    ]
