"""
Configuration management for PyRIoTBench.

This module provides type-safe configuration using Pydantic models with support for:
- YAML files (primary format)
- .properties files (backward compatibility with Java RIoTBench)
- Environment variables (for deployment/CI)
- Programmatic configuration (for testing)

The configuration system uses Pydantic v2 for:
- Type validation
- Automatic type coercion
- Helpful error messages
- JSON schema generation
- Nested model support

Architecture:
    TaskConfig      → Configuration for individual tasks
    PlatformConfig  → Platform-specific settings (Beam, Flink, etc.)
    BenchmarkConfig → Overall benchmark configuration
    ConfigLoader    → Loads from various sources

Example:
    # From YAML
    config = BenchmarkConfig.from_yaml("config.yaml")
    
    # From properties (Java compat)
    config = BenchmarkConfig.from_properties("config.properties")
    
    # From environment
    config = BenchmarkConfig.from_env()
    
    # Programmatic
    config = BenchmarkConfig(
        input_file="data.txt",
        output_file="results.txt",
        platform="standalone"
    )
"""

from pathlib import Path
from typing import Any, Dict, Optional, List, Union
import os
import yaml
import logging
from enum import Enum

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)

logger = logging.getLogger(__name__)


class PlatformType(str, Enum):
    """Supported execution platforms."""
    STANDALONE = "standalone"
    BEAM = "beam"
    FLINK = "flink"
    RAY = "ray"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TaskConfig(BaseModel):
    """
    Configuration for an individual benchmark task.
    
    This is the base configuration that all tasks can use.
    Tasks can extend this with their own specific fields.
    
    Attributes:
        task_name: Name of the task (must be registered)
        enabled: Whether to run this task
        config_params: Task-specific parameters (flexible dict)
    """
    
    model_config = ConfigDict(extra="allow")  # Allow extra fields for task-specific config
    
    task_name: str = Field(
        ...,
        description="Name of the task (must be registered in TaskRegistry)"
    )
    enabled: bool = Field(
        default=True,
        description="Whether to run this task in the pipeline"
    )
    config_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific configuration parameters"
    )
    
    @field_validator("task_name")
    @classmethod
    def task_name_not_empty(cls, v: str) -> str:
        """Validate task name is not empty."""
        if not v or not v.strip():
            raise ValueError("task_name cannot be empty")
        return v.strip()


class PlatformConfig(BaseModel):
    """
    Platform-specific configuration.
    
    Different platforms (Beam, Flink, Ray) have different configuration needs.
    This model captures common platform settings.
    
    Attributes:
        platform: Which platform to use
        parallelism: Number of parallel workers
        beam_runner: Beam-specific runner (DirectRunner, DataflowRunner, etc.)
        flink_checkpoint_interval: Flink checkpoint interval in ms
        ray_num_cpus: Ray CPU allocation
        extra_options: Platform-specific extra options
    """
    
    model_config = ConfigDict(extra="allow")
    
    platform: PlatformType = Field(
        default=PlatformType.STANDALONE,
        description="Execution platform"
    )
    parallelism: int = Field(
        default=1,
        ge=1,
        description="Number of parallel workers"
    )
    
    # Beam-specific
    beam_runner: Optional[str] = Field(
        default="DirectRunner",
        description="Apache Beam runner (DirectRunner, DataflowRunner, FlinkRunner, etc.)"
    )
    beam_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional Beam pipeline options"
    )
    
    # Flink-specific
    flink_checkpoint_interval: Optional[int] = Field(
        default=None,
        ge=0,
        description="Flink checkpoint interval in milliseconds"
    )
    
    # Ray-specific
    ray_num_cpus: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of CPUs for Ray cluster"
    )
    ray_num_gpus: Optional[int] = Field(
        default=0,
        ge=0,
        description="Number of GPUs for Ray cluster"
    )
    
    extra_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Platform-specific extra options"
    )


class BenchmarkConfig(BaseModel):
    """
    Overall benchmark configuration.
    
    This is the main configuration model that encompasses:
    - Input/output settings
    - Platform configuration
    - Task pipeline
    - Logging and metrics
    
    Attributes:
        name: Benchmark name
        input_file: Path to input data file
        output_file: Path to output file
        platform_config: Platform configuration
        tasks: List of tasks to run
        log_level: Logging level
        metrics_enabled: Whether to collect metrics
        metrics_output: Where to write metrics
    """
    
    model_config = ConfigDict(extra="forbid")  # Strict mode for top-level config
    
    # Basic settings
    name: str = Field(
        default="benchmark",
        description="Benchmark name for identification"
    )
    
    # Input/Output
    input_file: Path = Field(
        ...,
        description="Path to input data file"
    )
    output_file: Optional[Path] = Field(
        default=None,
        description="Path to output file (if None, prints to stdout)"
    )
    
    # Platform
    platform_config: PlatformConfig = Field(
        default_factory=PlatformConfig,
        description="Platform-specific configuration"
    )
    
    # Tasks pipeline
    tasks: List[TaskConfig] = Field(
        default_factory=list,
        description="List of tasks to execute in order"
    )
    
    # Logging
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path (if None, logs to console)"
    )
    
    # Metrics
    metrics_enabled: bool = Field(
        default=True,
        description="Whether to collect execution metrics"
    )
    metrics_output: Optional[Path] = Field(
        default=None,
        description="Where to write metrics (if None, includes in logs)"
    )
    
    @field_validator("input_file", mode="before")
    @classmethod
    def expand_input_path(cls, v: Any) -> Path:
        """Expand ~ and environment variables in input path."""
        if isinstance(v, str):
            v = os.path.expanduser(os.path.expandvars(v))
        return Path(v)
    
    @field_validator("output_file", "log_file", "metrics_output", mode="before")
    @classmethod
    def expand_optional_path(cls, v: Any) -> Optional[Path]:
        """Expand ~ and environment variables in optional paths."""
        if v is None:
            return None
        if isinstance(v, str):
            v = os.path.expanduser(os.path.expandvars(v))
        return Path(v)
    
    @model_validator(mode="after")
    def validate_input_exists(self) -> "BenchmarkConfig":
        """Validate that input file exists (optional - can be disabled for testing)."""
        # We don't validate here to allow config creation before files exist
        # Validation happens at runtime in the runner
        return self
    
    def to_flat_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to flat dictionary.
        
        Useful for passing to legacy code or task.setup() methods.
        Nested keys are flattened with dots: platform_config.parallelism → platform.parallelism
        
        Returns:
            Flat dictionary with dot-separated keys
        """
        def flatten(d: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
            items: List[tuple[str, Any]] = []
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten(v, new_key).items())
                elif isinstance(v, BaseModel):
                    items.extend(flatten(v.model_dump(), new_key).items())
                else:
                    items.append((new_key, v))
            return dict(items)
        
        return flatten(self.model_dump())
    
    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "BenchmarkConfig":
        """
        Load configuration from YAML file.
        
        Args:
            path: Path to YAML file
            
        Returns:
            BenchmarkConfig instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid or validation fails
            
        Example:
            config = BenchmarkConfig.from_yaml("config.yaml")
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        logger.info(f"Loading configuration from {path}")
        
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            
            if data is None:
                data = {}
            
            return cls(**data)
        
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load config from {path}: {e}")
    
    @classmethod
    def from_properties(cls, path: Union[str, Path]) -> "BenchmarkConfig":
        """
        Load configuration from .properties file (Java RIoTBench compatibility).
        
        Properties file format:
            name=my_benchmark
            input_file=data.txt
            platform_config.platform=beam
            tasks.0.task_name=bloom_filter
            tasks.0.enabled=true
        
        Nested keys use dots, lists use numeric indices.
        
        Args:
            path: Path to .properties file
            
        Returns:
            BenchmarkConfig instance
            
        Example:
            config = BenchmarkConfig.from_properties("config.properties")
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Properties file not found: {path}")
        
        logger.info(f"Loading configuration from properties file: {path}")
        
        # Parse properties file
        props: Dict[str, str] = {}
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()
        
        # Convert flat props to nested dict
        nested = cls._unflatten_dict(props)
        
        return cls(**nested)
    
    @classmethod
    def from_env(cls, prefix: str = "PYRIOTBENCH_") -> "BenchmarkConfig":
        """
        Load configuration from environment variables.
        
        Environment variables should be prefixed (default: PYRIOTBENCH_)
        and use underscores for nesting:
            PYRIOTBENCH_INPUT_FILE=data.txt
            PYRIOTBENCH_PLATFORM_CONFIG__PLATFORM=beam
            PYRIOTBENCH_LOG_LEVEL=DEBUG
        
        Note: Double underscore (__) for nested dict keys.
        
        Args:
            prefix: Environment variable prefix
            
        Returns:
            BenchmarkConfig instance
            
        Example:
            config = BenchmarkConfig.from_env()
        """
        logger.info(f"Loading configuration from environment (prefix: {prefix})")
        
        # Extract environment variables with prefix
        env_dict: Dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix):].lower()
                # Convert double underscore to dot for nesting
                config_key = config_key.replace("__", ".")
                env_dict[config_key] = value
        
        # Convert flat dict to nested
        nested = cls._unflatten_dict(env_dict)
        
        return cls(**nested)
    
    @staticmethod
    def _unflatten_dict(flat_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert flat dictionary with dot-separated keys to nested dict.
        
        Example:
            {"a.b.c": 1, "a.b.d": 2} → {"a": {"b": {"c": 1, "d": 2}}}
            {"tasks.0.name": "x"} → {"tasks": [{"name": "x"}]}
        """
        nested: Dict[str, Any] = {}
        
        for key, value in flat_dict.items():
            parts = key.split(".")
            current = nested
            
            for i, part in enumerate(parts[:-1]):
                next_part = parts[i + 1]
                
                # Check if next part is a number (list index)
                if next_part.isdigit():
                    # Current part should be a list
                    if part not in current:
                        current[part] = []
                    elif not isinstance(current[part], list):
                        # Conflict: was dict, needs to be list
                        current[part] = []
                    
                    # Ensure list is long enough
                    idx = int(next_part)
                    while len(current[part]) <= idx:
                        current[part].append({})
                    
                    # Move into the list element
                    current = current[part][idx]
                    # Skip the numeric index in next iteration
                    continue
                elif part.isdigit():
                    # Current part is a numeric index, skip (already handled)
                    continue
                else:
                    # Regular nested dict
                    if part not in current:
                        current[part] = {}
                    elif not isinstance(current[part], dict):
                        # Type conflict
                        current[part] = {}
                    current = current[part]
            
            # Set the final value
            final_part = parts[-1]
            if not final_part.isdigit():
                current[final_part] = value
            # If final part is digit, it's already set in the loop
        
        return nested
    
    def to_yaml(self, path: Union[str, Path]) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            path: Path to output YAML file
            
        Example:
            config.to_yaml("config_output.yaml")
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            yaml.dump(
                self.model_dump(mode="json"),
                f,
                default_flow_style=False,
                sort_keys=False
            )
        
        logger.info(f"Configuration saved to {path}")


# Convenience functions
def load_config(path: Union[str, Path]) -> BenchmarkConfig:
    """
    Load configuration from file (auto-detects format).
    
    Detects format based on file extension:
    - .yaml, .yml → YAML
    - .properties, .props → Properties
    
    Args:
        path: Path to config file
        
    Returns:
        BenchmarkConfig instance
    """
    path = Path(path)
    suffix = path.suffix.lower()
    
    if suffix in [".yaml", ".yml"]:
        return BenchmarkConfig.from_yaml(path)
    elif suffix in [".properties", ".props"]:
        return BenchmarkConfig.from_properties(path)
    else:
        # Try YAML by default
        logger.warning(f"Unknown config format '{suffix}', attempting YAML")
        return BenchmarkConfig.from_yaml(path)
