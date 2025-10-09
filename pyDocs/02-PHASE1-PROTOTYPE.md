# PyRIoTBench: Phase 1 Prototype Guide

**Goal**: Proof of Concept - Validate core abstractions work  
**Timeline**: Week 1-2  
**Deliverable**: Working NoOpTask + 1 real benchmark

---

## 📁 Project Structure

```
pyriotbench/
├── pyproject.toml              # Project metadata & dependencies
├── README.md                   # Quick start guide
├── .gitignore                  
│
├── pyriotbench/                # Main package
│   ├── __init__.py
│   │
│   ├── core/                   # Core abstractions (PRIORITY 1)
│   │   ├── __init__.py
│   │   ├── task.py             # ITask protocol, BaseTask
│   │   ├── registry.py         # TaskRegistry
│   │   ├── config.py           # Configuration management
│   │   └── metrics.py          # TaskMetrics dataclass
│   │
│   ├── tasks/                  # Benchmark implementations
│   │   ├── __init__.py
│   │   ├── noop.py             # NoOperationTask (test)
│   │   └── parse/
│   │       ├── __init__.py
│   │       └── senml_parse.py  # First real benchmark
│   │
│   ├── platforms/              # Platform adapters
│   │   ├── __init__.py
│   │   └── standalone/
│   │       ├── __init__.py
│   │       └── runner.py       # Simple file-based runner
│   │
│   └── cli/                    # Command-line interface
│       ├── __init__.py
│       └── main.py             # Entry point
│
├── tests/                      # Unit tests
│   ├── __init__.py
│   ├── test_core/
│   │   ├── test_task.py
│   │   ├── test_registry.py
│   │   └── test_config.py
│   ├── test_tasks/
│   │   ├── test_noop.py
│   │   └── test_senml_parse.py
│   └── fixtures/
│       ├── config.yaml
│       ├── sample_data.txt
│       └── sample_senml.json
│
├── examples/                   # Usage examples
│   ├── 01_simple_task.py
│   ├── 02_senml_parsing.py
│   └── config/
│       └── example.yaml
│
└── docs/                       # Documentation
    └── api/                    # API docs (Sphinx)
```

---

## 🔧 Phase 1: Implementation Checklist

### Step 1: Project Setup (Day 1)

```bash
# Create project directory
mkdir pyriotbench
cd pyriotbench

# Initialize git
git init
git add .gitignore README.md

# Create Python package structure
mkdir -p pyriotbench/core
mkdir -p pyriotbench/tasks/parse
mkdir -p pyriotbench/platforms/standalone
mkdir -p pyriotbench/cli
mkdir -p tests/test_core
mkdir -p tests/test_tasks
mkdir -p tests/fixtures
mkdir -p examples/config

# Create __init__.py files
find pyriotbench -type d -exec touch {}/__init__.py \;
find tests -type d -exec touch {}/__init__.py \;
```

**pyproject.toml**:
```toml
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pyriotbench"
version = "0.1.0"
description = "Python port of RIoTBench - IoT streaming benchmark suite"
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
readme = "README.md"
requires-python = ">=3.10"
license = {text = "Apache-2.0"}
keywords = ["benchmark", "iot", "streaming", "flink", "beam"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]

dependencies = [
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "attrs>=23.0",
    "click>=8.1",  # CLI
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "black>=23.7",
    "ruff>=0.0.285",
    "mypy>=1.5",
]
beam = [
    "apache-beam[gcp]>=2.50",
]
flink = [
    "apache-flink>=1.17",
]
ml = [
    "scikit-learn>=1.3",
    "numpy>=1.24",
    "scipy>=1.11",
]
azure = [
    "azure-storage-blob>=12.17",
    "azure-data-tables>=12.4",
]
mqtt = [
    "paho-mqtt>=1.6",
]
all = [
    "pyriotbench[dev,beam,flink,ml,azure,mqtt]",
]

[project.scripts]
pyriotbench = "pyriotbench.cli.main:cli"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
addopts = "-v --cov=pyriotbench --cov-report=html --cov-report=term"

[tool.black]
line-length = 100
target-version = ['py310', 'py311']

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "W", "I", "N"]

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
```

---

### Step 2: Core Abstractions (Day 2-3)

**File: `pyriotbench/core/task.py`**

```python
"""Core task abstractions - the foundation of portability."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Protocol, TypeVar
import time
import logging

T = TypeVar('T')  # Input type
U = TypeVar('U')  # Output type

class ITask(Protocol[T, U]):
    """
    Platform-agnostic task protocol.
    All benchmarks implement this interface.
    """
    
    def setup(self, logger: logging.Logger, config: Dict[str, Any]) -> None:
        """Initialize task with logger and configuration."""
        ...
    
    def do_task(self, data: Dict[str, T]) -> Optional[float]:
        """
        Process a single data element.
        
        Returns:
            float: Status/result (None=skip, -inf=error, >=0=success)
        """
        ...
    
    def get_last_result(self) -> Optional[U]:
        """Retrieve complex result from last do_task call."""
        ...
    
    def tear_down(self) -> float:
        """
        Cleanup and return performance metrics.
        
        Returns:
            float: Average execution time per call (seconds)
        """
        ...


class BaseTask(ABC, Generic[T, U]):
    """
    Abstract base task with built-in timing and metrics.
    Implements template method pattern.
    """
    
    DEFAULT_KEY = "D"
    
    def __init__(self):
        self.logger: Optional[logging.Logger] = None
        self.config: Dict[str, Any] = {}
        self._total_time: float = 0.0
        self._call_count: int = 0
        self._error_count: int = 0
        self._last_result: Optional[U] = None
    
    def setup(self, logger: logging.Logger, config: Dict[str, Any]) -> None:
        """Setup with timing initialization."""
        self.logger = logger
        self.config = config
        self._total_time = 0.0
        self._call_count = 0
        self._error_count = 0
        self.logger.debug(f"{self.__class__.__name__} setup complete")
    
    def do_task(self, data: Dict[str, T]) -> Optional[float]:
        """
        Template method with timing instrumentation.
        Calls child class do_task_logic() and wraps with metrics.
        """
        start_time = time.perf_counter()
        try:
            result = self.do_task_logic(data)
            elapsed = time.perf_counter() - start_time
            self._total_time += elapsed
            self._call_count += 1
            
            if result is not None:
                assert result >= 0 or result == float('-inf'), \
                    f"Result must be non-negative, None, or -inf, got {result}"
            return result
            
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            self._total_time += elapsed
            self._call_count += 1
            self._error_count += 1
            self.logger.error(f"Error in {self.__class__.__name__}: {e}", exc_info=True)
            return float('-inf')  # Signal error
    
    @abstractmethod
    def do_task_logic(self, data: Dict[str, T]) -> Optional[float]:
        """Child classes implement actual task logic here."""
        pass
    
    def get_last_result(self) -> Optional[U]:
        """Retrieve last complex result."""
        return self._last_result
    
    def _set_last_result(self, result: U) -> U:
        """Set complex result (for child classes)."""
        self._last_result = result
        return result
    
    def tear_down(self) -> float:
        """Cleanup and return average execution time."""
        avg_time = self._total_time / self._call_count if self._call_count > 0 else 0.0
        self.logger.info(
            f"{self.__class__.__name__} teardown: "
            f"{self._call_count} calls, {avg_time:.6f}s avg, {self._error_count} errors"
        )
        return avg_time
    
    @property
    def metrics(self) -> Dict[str, Any]:
        """Get current metrics as dictionary."""
        return {
            'total_time': self._total_time,
            'call_count': self._call_count,
            'error_count': self._error_count,
            'avg_time': self._total_time / self._call_count if self._call_count > 0 else 0.0,
        }
```

**Test: `tests/test_core/test_task.py`**

```python
import logging
import pytest
from pyriotbench.core.task import BaseTask

class DummyTask(BaseTask[str, None]):
    """Test task that doubles a number."""
    
    def do_task_logic(self, data):
        value = float(data.get(self.DEFAULT_KEY, "0"))
        return value * 2

def test_base_task_lifecycle():
    """Test setup -> process -> teardown lifecycle."""
    logger = logging.getLogger('test')
    config = {}
    task = DummyTask()
    
    # Setup
    task.setup(logger, config)
    assert task.logger == logger
    assert task.config == config
    
    # Process
    result = task.do_task({"D": "5.0"})
    assert result == 10.0
    assert task._call_count == 1
    
    # Teardown
    avg_time = task.tear_down()
    assert avg_time >= 0.0

def test_base_task_timing():
    """Test that timing is recorded."""
    task = DummyTask()
    task.setup(logging.getLogger('test'), {})
    
    # Process multiple times
    for i in range(10):
        task.do_task({"D": str(i)})
    
    assert task._call_count == 10
    assert task._total_time > 0.0
    
    metrics = task.metrics
    assert metrics['call_count'] == 10
    assert metrics['avg_time'] > 0.0

def test_base_task_error_handling():
    """Test error handling."""
    class ErrorTask(BaseTask):
        def do_task_logic(self, data):
            raise ValueError("Test error")
    
    task = ErrorTask()
    task.setup(logging.getLogger('test'), {})
    
    result = task.do_task({"D": "test"})
    assert result == float('-inf')
    assert task._error_count == 1
```

---

### Step 3: Task Registry (Day 3)

**File: `pyriotbench/core/registry.py`**

```python
"""Task registry for dynamic task loading."""
from typing import Dict, Type
from pyriotbench.core.task import ITask

class TaskRegistry:
    """Central registry for all benchmark tasks."""
    
    _tasks: Dict[str, Type[ITask]] = {}
    
    @classmethod
    def register(cls, name: str, task_class: Type[ITask]) -> None:
        """Register a task class."""
        if name in cls._tasks:
            raise ValueError(f"Task '{name}' already registered")
        cls._tasks[name] = task_class
    
    @classmethod
    def get(cls, name: str) -> Type[ITask]:
        """Get task class by name."""
        if name not in cls._tasks:
            raise ValueError(f"Unknown task: '{name}'. Available: {list(cls._tasks.keys())}")
        return cls._tasks[name]
    
    @classmethod
    def list_tasks(cls) -> Dict[str, Type[ITask]]:
        """List all registered tasks."""
        return cls._tasks.copy()
    
    @classmethod
    def clear(cls) -> None:
        """Clear registry (for testing)."""
        cls._tasks.clear()


def register_task(name: str):
    """Decorator to auto-register task classes."""
    def decorator(cls: Type[ITask]) -> Type[ITask]:
        TaskRegistry.register(name, cls)
        return cls
    return decorator
```

---

### Step 4: Simple Benchmarks (Day 4)

**File: `pyriotbench/tasks/noop.py`**

```python
"""No-operation task for baseline measurements."""
from typing import Dict, Optional
from pyriotbench.core.task import BaseTask
from pyriotbench.core.registry import register_task

@register_task("noop")
class NoOperationTask(BaseTask[str, None]):
    """
    No-op task that does nothing.
    Used for baseline performance measurement.
    """
    
    def do_task_logic(self, data: Dict[str, str]) -> Optional[float]:
        """Do nothing, return success."""
        return 0.0
```

**File: `pyriotbench/tasks/parse/senml_parse.py`**

```python
"""SenML JSON parsing task."""
import json
from typing import Dict, Optional
from pyriotbench.core.task import BaseTask
from pyriotbench.core.registry import register_task

@register_task("senml_parse")
class SenMLParse(BaseTask[str, Dict]):
    """
    Parse SenML (Sensor Markup Language) JSON messages.
    
    Input: JSON string
    Output: Parsed dictionary
    """
    
    def do_task_logic(self, data: Dict[str, str]) -> Optional[float]:
        """Parse SenML JSON."""
        input_str = data.get(self.DEFAULT_KEY, "")
        
        try:
            # Parse JSON
            parsed = json.loads(input_str)
            
            # Validate SenML structure
            if not isinstance(parsed, dict) or 'e' not in parsed:
                self.logger.warning(f"Invalid SenML structure: {input_str[:100]}")
                return float('-inf')
            
            # Extract sensor data
            events = parsed.get('e', [])
            if not events:
                return None  # No data to process
            
            # Store parsed result for downstream tasks
            self._set_last_result(parsed)
            
            return float(len(events))  # Return number of events parsed
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            return float('-inf')
```

**Test: `tests/test_tasks/test_senml_parse.py`**

```python
import logging
import pytest
from pyriotbench.tasks.parse.senml_parse import SenMLParse

def test_senml_parse_valid():
    """Test parsing valid SenML."""
    task = SenMLParse()
    task.setup(logging.getLogger('test'), {})
    
    senml_data = '{"bn": "sensor1", "e": [{"n": "temp", "v": 23.5}]}'
    result = task.do_task({"D": senml_data})
    
    assert result == 1.0  # One event parsed
    parsed = task.get_last_result()
    assert parsed is not None
    assert 'e' in parsed
    assert len(parsed['e']) == 1

def test_senml_parse_invalid():
    """Test parsing invalid JSON."""
    task = SenMLParse()
    task.setup(logging.getLogger('test'), {})
    
    result = task.do_task({"D": "not json"})
    assert result == float('-inf')
```

---

### Step 5: Standalone Runner (Day 5)

**File: `pyriotbench/platforms/standalone/runner.py`**

```python
"""Simple standalone runner for testing tasks."""
import logging
from pathlib import Path
from typing import Type, Dict, Any, Optional
from pyriotbench.core.task import ITask

class StandaloneRunner:
    """
    Simple in-process task runner.
    No distributed framework - just processes file line by line.
    """
    
    def __init__(self, task_class: Type[ITask], config: Dict[str, Any]):
        self.task_class = task_class
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger('pyriotbench')
    
    def run_file(self, input_path: str, output_path: Optional[str] = None):
        """
        Run task on input file, optionally write results to output file.
        
        Args:
            input_path: Path to input file (one record per line)
            output_path: Optional path to output file
        """
        # Create task instance
        task = self.task_class()
        task.setup(self.logger, self.config)
        
        self.logger.info(f"Processing {input_path} with {task.__class__.__name__}")
        
        # Process file
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        output_file = open(output_path, 'w') if output_path else None
        
        try:
            with open(input_file) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Process through task
                    data = {"D": line}
                    result = task.do_task(data)
                    
                    # Write output
                    if output_file and result is not None and result != float('-inf'):
                        # Get complex result if available
                        complex_result = task.get_last_result()
                        if complex_result:
                            output_file.write(f"{complex_result}\n")
                        else:
                            output_file.write(f"{line}\t{result}\n")
                    
                    if line_num % 1000 == 0:
                        self.logger.info(f"Processed {line_num} lines")
        
        finally:
            if output_file:
                output_file.close()
            
            # Teardown and report metrics
            avg_time = task.tear_down()
            self.logger.info(f"Completed. Average time: {avg_time*1000:.3f}ms per record")
            self.logger.info(f"Metrics: {task.metrics}")

# Example usage
if __name__ == "__main__":
    from pyriotbench.tasks.noop import NoOperationTask
    
    runner = StandaloneRunner(NoOperationTask, {})
    runner.run_file("input.txt", "output.txt")
```

---

### Step 6: CLI Interface (Day 5)

**File: `pyriotbench/cli/main.py`**

```python
"""Command-line interface for pyriotbench."""
import click
import yaml
from pathlib import Path
from pyriotbench.core.registry import TaskRegistry
from pyriotbench.platforms.standalone.runner import StandaloneRunner

# Import tasks to trigger registration
import pyriotbench.tasks.noop
import pyriotbench.tasks.parse.senml_parse

@click.group()
def cli():
    """PyRIoTBench - Python IoT Benchmark Suite"""
    pass

@cli.command()
def list_tasks():
    """List all available tasks."""
    tasks = TaskRegistry.list_tasks()
    click.echo(f"Available tasks ({len(tasks)}):")
    for name, task_class in sorted(tasks.items()):
        click.echo(f"  - {name}: {task_class.__doc__ or 'No description'}")

@cli.command()
@click.argument('task_name')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file (YAML)')
def run(task_name: str, input_file: str, output: str, config: str):
    """Run a benchmark task."""
    # Load config
    if config:
        with open(config) as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}
    
    # Get task class
    try:
        task_class = TaskRegistry.get(task_name)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return 1
    
    # Run task
    runner = StandaloneRunner(task_class, cfg)
    try:
        runner.run_file(input_file, output)
        click.echo("Done!")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1

if __name__ == '__main__':
    cli()
```

---

## 🧪 Testing Strategy

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=pyriotbench --cov-report=html

# Run specific test
pytest tests/test_core/test_task.py::test_base_task_lifecycle

# Type checking
mypy pyriotbench

# Linting
ruff check pyriotbench
black --check pyriotbench
```

---

## 🎯 Success Criteria for Phase 1

- [ ] All core abstractions implemented (`ITask`, `BaseTask`, `TaskRegistry`)
- [ ] `NoOperationTask` works end-to-end
- [ ] `SenMLParse` parses valid JSON
- [ ] Standalone runner processes file successfully
- [ ] CLI commands work (`list-tasks`, `run`)
- [ ] All tests pass (>80% coverage)
- [ ] Type checking passes (mypy strict mode)
- [ ] Documentation complete

---

## 📝 Example Usage

```bash
# List available tasks
pyriotbench list-tasks

# Run NoOp task (baseline)
pyriotbench run noop input.txt --output output.txt

# Run SenML parsing
pyriotbench run senml_parse sample_senml.txt --output parsed.txt --config config.yaml

# With Docker
docker run pyriotbench:latest run noop /data/input.txt
```

---

## 🚀 Next Steps (Phase 2)

After Phase 1 success:
1. Implement 4 more core benchmarks (AVG, BLF, DTC, ABD)
2. Add Beam adapter
3. Performance comparison with Java version
4. Documentation polish

---

**Status**: Ready to implement  
**Blocked By**: None  
**Owner**: Development team

