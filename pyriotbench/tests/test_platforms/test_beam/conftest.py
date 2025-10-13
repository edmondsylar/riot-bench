"""
Pytest fixtures for Beam tests.

Provides test data and configuration for Beam integration testing.
"""

import tempfile
from pathlib import Path

import pytest

# Import tasks to trigger registration
import pyriotbench.tasks  # noqa: F401


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_input_file(temp_dir):
    """Create a sample input file with sensor data."""
    input_file = temp_dir / "input.txt"
    input_file.write_text("25.0\n26.1\n24.8\n25.5\n26.2\n")
    return input_file


@pytest.fixture
def sample_csv_file(temp_dir):
    """Create a sample CSV file with multi-field data."""
    csv_file = temp_dir / "data.csv"
    csv_file.write_text(
        "timestamp,value,sensor_id\n"
        "2025-01-01T00:00:00,25.0,sensor_001\n"
        "2025-01-01T00:00:01,26.1,sensor_001\n"
        "2025-01-01T00:00:02,24.8,sensor_001\n"
    )
    return csv_file


@pytest.fixture
def kalman_config():
    """Kalman filter configuration."""
    return {
        'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
        'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
        'STATISTICS.KALMAN_FILTER.USE_MSG_FIELD': 0,
    }


@pytest.fixture
def window_config():
    """Block window average configuration."""
    return {
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 3,
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD': 0,
    }
