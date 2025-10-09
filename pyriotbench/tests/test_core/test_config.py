"""
Tests for configuration management.

Tests cover:
- Pydantic model validation
- YAML loading
- Properties loading
- Environment variable loading
- Path expansion
- Flat dict conversion
- Configuration serialization
"""

import pytest
import os
import tempfile
from pathlib import Path
from typing import Any

from pyriotbench.core.config import (
    BenchmarkConfig,
    PlatformConfig,
    TaskConfig,
    PlatformType,
    LogLevel,
    load_config,
)


# Fixtures

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_yaml_config(temp_dir):
    """Create a sample YAML config file."""
    config_path = temp_dir / "config.yaml"
    config_content = """
name: test_benchmark
input_file: data/input.txt
output_file: data/output.txt
log_level: DEBUG

platform_config:
  platform: beam
  parallelism: 4
  beam_runner: DirectRunner

tasks:
  - task_name: bloom_filter
    enabled: true
    config_params:
      size: 10000
  - task_name: average
    enabled: false
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_properties_config(temp_dir):
    """Create a sample .properties config file."""
    config_path = temp_dir / "config.properties"
    config_content = """# Test configuration
name=test_benchmark
input_file=data/input.txt
output_file=data/output.txt
log_level=INFO

platform_config.platform=standalone
platform_config.parallelism=2

tasks.0.task_name=bloom_filter
tasks.0.enabled=true
tasks.1.task_name=average
tasks.1.enabled=false
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_input_file(temp_dir):
    """Create a sample input file."""
    input_file = temp_dir / "input.txt"
    input_file.write_text("test data\n")
    return input_file


# Test TaskConfig

def test_task_config_creation():
    """Test creating a TaskConfig."""
    config = TaskConfig(
        task_name="bloom_filter",
        enabled=True,
        config_params={"size": 10000}
    )
    
    assert config.task_name == "bloom_filter"
    assert config.enabled is True
    assert config.config_params["size"] == 10000


def test_task_config_defaults():
    """Test TaskConfig default values."""
    config = TaskConfig(task_name="test")
    
    assert config.enabled is True
    assert config.config_params == {}


def test_task_config_empty_name_fails():
    """Test that empty task name raises error."""
    with pytest.raises(ValueError, match="cannot be empty"):
        TaskConfig(task_name="")


def test_task_config_extra_fields():
    """Test that TaskConfig allows extra fields."""
    config = TaskConfig(
        task_name="test",
        custom_field="custom_value"
    )
    
    assert config.task_name == "test"
    # Pydantic v2 allows extra fields with extra="allow"


# Test PlatformConfig

def test_platform_config_defaults():
    """Test PlatformConfig default values."""
    config = PlatformConfig()
    
    assert config.platform == PlatformType.STANDALONE
    assert config.parallelism == 1
    assert config.beam_runner == "DirectRunner"


def test_platform_config_beam():
    """Test Beam platform configuration."""
    config = PlatformConfig(
        platform=PlatformType.BEAM,
        parallelism=4,
        beam_runner="DataflowRunner",
        beam_options={"project": "my-project"}
    )
    
    assert config.platform == PlatformType.BEAM
    assert config.parallelism == 4
    assert config.beam_runner == "DataflowRunner"
    assert config.beam_options["project"] == "my-project"


def test_platform_config_parallelism_validation():
    """Test that parallelism must be >= 1."""
    with pytest.raises(ValueError):
        PlatformConfig(parallelism=0)
    
    with pytest.raises(ValueError):
        PlatformConfig(parallelism=-1)


# Test BenchmarkConfig

def test_benchmark_config_minimal(sample_input_file):
    """Test minimal BenchmarkConfig."""
    config = BenchmarkConfig(input_file=sample_input_file)
    
    assert config.input_file == sample_input_file
    assert config.output_file is None
    assert config.name == "benchmark"
    assert config.log_level == LogLevel.INFO


def test_benchmark_config_full(sample_input_file):
    """Test full BenchmarkConfig with all fields."""
    config = BenchmarkConfig(
        name="my_benchmark",
        input_file=sample_input_file,
        output_file=Path("output.txt"),
        platform_config=PlatformConfig(platform=PlatformType.BEAM),
        tasks=[
            TaskConfig(task_name="task1"),
            TaskConfig(task_name="task2", enabled=False)
        ],
        log_level=LogLevel.DEBUG,
        metrics_enabled=True
    )
    
    assert config.name == "my_benchmark"
    assert config.platform_config.platform == PlatformType.BEAM
    assert len(config.tasks) == 2
    assert config.log_level == LogLevel.DEBUG


def test_benchmark_config_path_expansion(tmp_path):
    """Test that paths are expanded (~ and env vars)."""
    # Set environment variable
    os.environ["TEST_DIR"] = str(tmp_path)
    
    # Create test file
    input_file = tmp_path / "input.txt"
    input_file.write_text("test")
    
    config = BenchmarkConfig(
        input_file="$TEST_DIR/input.txt",
        output_file="$TEST_DIR/output.txt"
    )
    
    assert config.input_file == tmp_path / "input.txt"
    assert config.output_file == tmp_path / "output.txt"
    
    # Cleanup
    del os.environ["TEST_DIR"]


# Test YAML Loading

def test_load_from_yaml(sample_yaml_config, temp_dir):
    """Test loading configuration from YAML."""
    # Create input file referenced in config
    (temp_dir / "data").mkdir()
    (temp_dir / "data" / "input.txt").write_text("test")
    
    config = BenchmarkConfig.from_yaml(sample_yaml_config)
    
    assert config.name == "test_benchmark"
    assert config.log_level == LogLevel.DEBUG
    assert config.platform_config.platform == PlatformType.BEAM
    assert config.platform_config.parallelism == 4
    assert len(config.tasks) == 2
    assert config.tasks[0].task_name == "bloom_filter"
    assert config.tasks[0].enabled is True
    assert config.tasks[1].enabled is False


def test_load_from_yaml_nonexistent_file():
    """Test loading from non-existent YAML file."""
    with pytest.raises(FileNotFoundError):
        BenchmarkConfig.from_yaml("nonexistent.yaml")


def test_load_from_yaml_invalid():
    """Test loading invalid YAML."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: content: [")
        temp_file = f.name
    
    try:
        with pytest.raises(ValueError, match="Invalid YAML"):
            BenchmarkConfig.from_yaml(temp_file)
    finally:
        os.unlink(temp_file)


# Test Properties Loading

def test_load_from_properties(sample_properties_config, temp_dir):
    """Test loading configuration from .properties file."""
    # Create input file
    (temp_dir / "data").mkdir()
    (temp_dir / "data" / "input.txt").write_text("test")
    
    config = BenchmarkConfig.from_properties(sample_properties_config)
    
    assert config.name == "test_benchmark"
    assert config.platform_config.platform == PlatformType.STANDALONE
    assert config.platform_config.parallelism == 2
    assert len(config.tasks) == 2
    assert config.tasks[0].task_name == "bloom_filter"


def test_load_from_properties_nonexistent():
    """Test loading from non-existent properties file."""
    with pytest.raises(FileNotFoundError):
        BenchmarkConfig.from_properties("nonexistent.properties")


# Test Environment Variables

def test_load_from_env(sample_input_file):
    """Test loading configuration from environment variables."""
    # Set environment variables
    os.environ["PYRIOTBENCH_NAME"] = "env_benchmark"
    os.environ["PYRIOTBENCH_INPUT_FILE"] = str(sample_input_file)
    os.environ["PYRIOTBENCH_LOG_LEVEL"] = "DEBUG"
    os.environ["PYRIOTBENCH_PLATFORM_CONFIG__PLATFORM"] = "beam"
    os.environ["PYRIOTBENCH_PLATFORM_CONFIG__PARALLELISM"] = "8"
    
    try:
        config = BenchmarkConfig.from_env()
        
        assert config.name == "env_benchmark"
        assert config.input_file == sample_input_file
        assert config.log_level == LogLevel.DEBUG
        assert config.platform_config.platform == PlatformType.BEAM
        assert config.platform_config.parallelism == 8
    
    finally:
        # Cleanup
        for key in list(os.environ.keys()):
            if key.startswith("PYRIOTBENCH_"):
                del os.environ[key]


# Test Flat Dict Conversion

def test_to_flat_dict(sample_input_file):
    """Test converting config to flat dictionary."""
    config = BenchmarkConfig(
        name="test",
        input_file=sample_input_file,
        platform_config=PlatformConfig(parallelism=4)
    )
    
    flat = config.to_flat_dict()
    
    assert flat["name"] == "test"
    assert flat["platform_config.parallelism"] == 4
    assert flat["platform_config.platform"] == "standalone"


def test_to_flat_dict_with_tasks(sample_input_file):
    """Test flat dict with task list."""
    config = BenchmarkConfig(
        input_file=sample_input_file,
        tasks=[
            TaskConfig(task_name="task1"),
            TaskConfig(task_name="task2")
        ]
    )
    
    flat = config.to_flat_dict()
    
    assert "tasks" in flat
    # Tasks is a list in flat dict


# Test YAML Saving

def test_to_yaml(sample_input_file, temp_dir):
    """Test saving configuration to YAML."""
    config = BenchmarkConfig(
        name="test",
        input_file=sample_input_file,
        platform_config=PlatformConfig(parallelism=4)
    )
    
    output_path = temp_dir / "output_config.yaml"
    config.to_yaml(output_path)
    
    assert output_path.exists()
    
    # Load it back
    loaded = BenchmarkConfig.from_yaml(output_path)
    assert loaded.name == "test"
    assert loaded.platform_config.parallelism == 4


# Test Auto-Detection

def test_load_config_yaml(sample_yaml_config, temp_dir):
    """Test load_config auto-detects YAML."""
    (temp_dir / "data").mkdir()
    (temp_dir / "data" / "input.txt").write_text("test")
    
    config = load_config(sample_yaml_config)
    
    assert config.name == "test_benchmark"


def test_load_config_properties(sample_properties_config, temp_dir):
    """Test load_config auto-detects properties."""
    (temp_dir / "data").mkdir()
    (temp_dir / "data" / "input.txt").write_text("test")
    
    config = load_config(sample_properties_config)
    
    assert config.name == "test_benchmark"


# Test Validation

def test_config_validation_strict_mode(sample_input_file):
    """Test that extra fields are rejected at top level."""
    with pytest.raises(ValueError):
        BenchmarkConfig(
            input_file=sample_input_file,
            invalid_field="should_fail"
        )


def test_task_config_params_flexible():
    """Test that config_params accepts any fields."""
    config = TaskConfig(
        task_name="test",
        config_params={
            "custom1": 123,
            "custom2": "value",
            "nested": {"key": "value"}
        }
    )
    
    assert config.config_params["custom1"] == 123
    assert config.config_params["nested"]["key"] == "value"


# Edge Cases

def test_empty_yaml(temp_dir):
    """Test loading empty YAML file."""
    empty_yaml = temp_dir / "empty.yaml"
    empty_yaml.write_text("")
    
    # Should fail because input_file is required
    with pytest.raises(ValueError):
        BenchmarkConfig.from_yaml(empty_yaml)


def test_config_with_no_tasks(sample_input_file):
    """Test config with empty task list."""
    config = BenchmarkConfig(
        input_file=sample_input_file,
        tasks=[]
    )
    
    assert config.tasks == []


def test_unflatten_dict_nested():
    """Test unflattening nested dictionary."""
    flat = {
        "a.b.c": 1,
        "a.b.d": 2,
        "a.e": 3,
        "f": 4
    }
    
    nested = BenchmarkConfig._unflatten_dict(flat)
    
    assert nested["a"]["b"]["c"] == 1
    assert nested["a"]["b"]["d"] == 2
    assert nested["a"]["e"] == 3
    assert nested["f"] == 4
