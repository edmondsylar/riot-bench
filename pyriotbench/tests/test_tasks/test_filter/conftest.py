"""Pytest configuration for filter task tests."""

import pickle
import tempfile
from pathlib import Path

import pytest
from pybloom_live import BloomFilter


@pytest.fixture
def bloom_filter_model():
    """Create a temporary bloom filter model file for testing."""
    # Create bloom filter with known values
    bf = BloomFilter(capacity=1000, error_rate=0.001)
    
    # Add test values
    test_values = [
        "sensor_001",
        "sensor_002", 
        "sensor_003",
        "temperature",
        "humidity",
        "pressure",
        "12345",
        "67890",
    ]
    
    for value in test_values:
        bf.add(value)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
        pickle.dump(bf, f)
        temp_path = Path(f.name)
    
    yield temp_path, test_values
    
    # Cleanup
    temp_path.unlink()


@pytest.fixture
def bloom_filter_config(bloom_filter_model):
    """Configuration for bloom filter task."""
    model_path, test_values = bloom_filter_model
    
    return {
        'FILTER.BLOOM_FILTER.MODEL_PATH': str(model_path),
        'FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD': 0,  # Random mode
        'FILTER.BLOOM_FILTER_CHECK.TESTING_RANGE': 100,
    }, test_values


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing field extraction."""
    return [
        "sensor_001,42.5,normal",
        "sensor_002,38.1,warning",
        "sensor_003,51.0,critical",
        "unknown_sensor,25.0,normal",
    ]
