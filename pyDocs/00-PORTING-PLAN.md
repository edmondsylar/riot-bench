# PyRIoTBench: Python Porting Plan

**Date**: October 9, 2025  
**Status**: Planning Phase  
**Version**: 1.0  

---

## 📋 Executive Summary

This document outlines the comprehensive strategy for porting **RIoTBench** from Java/Apache Storm to Python, creating **PyRIoTBench** - a modern, cloud-native IoT benchmark suite. The goal is to preserve the excellent modular architecture while modernizing the implementation and expanding platform support.

### Key Objectives
1. ✅ **Preserve Portability**: Maintain clean separation between benchmark logic and platform-specific code
2. ✅ **Improve Architecture**: Leverage Python's features for better abstraction and extensibility
3. ✅ **Expand Platforms**: Support Apache Flink, Apache Beam, Ray, and standalone execution
4. ✅ **Modernize Stack**: Use contemporary Python libraries and cloud-native patterns
5. ✅ **Maintain Compatibility**: Ensure benchmark results are comparable with Java version

---

## 🎯 Part 1: Architecture Analysis

### 1.1 What Makes RIoTBench Portable? (Critical to Preserve)

#### ✅ **Core Abstraction: Task Interface**
```java
// Java Interface
public interface ITask<T,U> {
    public void setup(Logger l_, Properties p_);
    public Float doTask(Map<String, T> map);
    public U getLastResult();
    public float tearDown();
}
```

**Why This Works:**
- **Platform Agnostic**: No Storm/Flink/Beam dependencies
- **Simple Contract**: 4-method lifecycle (setup → doTask → getLastResult → tearDown)
- **Timing Built-in**: `AbstractTask` handles instrumentation transparently
- **Flexible Return**: `Float` for status + generic `U` for complex results

**Key Insight**: Tasks are pure computation units with **zero platform knowledge**

---

#### ✅ **Adapter Pattern: Platform Integration**
```java
// Storm Bolt wraps Task
public abstract class BaseTaskBolt extends BaseRichBolt {
    protected ITask task;
    
    public void execute(Tuple input) {
        String rowString = input.getStringByField("RowString");
        HashMap<String, String> map = new HashMap<>();
        map.put(AbstractTask.DEFAULT_KEY, rowString);
        Float res = task.doTask(map);  // Platform-agnostic call
        if(res != null) collector.emit(new Values(rowString, msgId, res));
    }
    
    abstract protected ITask getTaskInstance();
}
```

**Why This Works:**
- **Clear Separation**: Bolt handles Storm specifics (tuples, emit, ack)
- **Task is Oblivious**: Task only sees `Map<String, String>` input
- **Factory Pattern**: Subclasses provide concrete task instances
- **One Adapter per Platform**: Same task runs on any platform

**Key Insight**: Platform adapters translate framework concepts → simple Map → Task

---

#### ✅ **State Management Pattern**
```java
public class BlockWindowAverage extends AbstractTask<String,Float> {
    // Static: Shared across all instances (configuration)
    private static final Object SETUP_LOCK = new Object();
    private static boolean doneSetup = false;
    private static float aggCountWindowSize = 0;
    
    // Instance: Per-task state (computation)
    private float aggCount;
    private float aggSum;
    private float avgRes;
    
    public void setup(Logger l_, Properties p_) {
        super.setup(l_, p_);
        synchronized (SETUP_LOCK) {
            if(!doneSetup) {  // One-time initialization
                aggCountWindowSize = Integer.parseInt(p_.getProperty("..."));
                doneSetup = true;
            }
        }
    }
}
```

**Why This Works:**
- **Configuration Immutable**: Loaded once, shared safely
- **State Local**: Each task instance manages own computation state
- **Thread-Safe**: Synchronization for static initialization
- **Window Logic**: State accumulates across `doTask()` calls

**Key Insight**: Clear distinction between configuration (static) vs computation state (instance)

---

#### ✅ **Configuration System**
```properties
# tasks.properties - Centralized configuration
PARSE.SENML_ENABLED=TRUE
FILTER.BLOOM_FILTER.MODEL_PATH=/path/to/model
AGGREGATE.BLOCK_COUNT.WINDOW_SIZE=100
CLASSIFICATION.DTC.MODEL_PATH=/path/to/model.model
```

**Why This Works:**
- **Externalized**: No hardcoded values in task code
- **Hierarchical**: Namespace-based organization (PARSE.X, FILTER.Y)
- **Platform-Independent**: Same properties file for any platform
- **Runtime Flexibility**: Easy to override for experiments

**Key Insight**: Properties-based configuration decouples tasks from environment

---

### 1.2 Architecture Strengths to Preserve

| Feature | Java Implementation | Must Preserve | Improvement Opportunity |
|---------|-------------------|---------------|------------------------|
| **Task Abstraction** | `ITask` interface | ✅ Yes - Core portability | Make more Pythonic (Protocol/ABC) |
| **Adapter Pattern** | `BaseTaskBolt` wraps task | ✅ Yes - Platform independence | Create adapters for Flink/Beam/Ray |
| **Timing Instrumentation** | Built into `AbstractTask` | ✅ Yes - Consistent metrics | Add async/profiling support |
| **State Management** | Static + instance vars | ✅ Yes - Statefulness pattern | Use Python dataclasses/attrs |
| **Configuration** | `.properties` file | ✅ Yes - Externalization | Support YAML/TOML + env vars |
| **Factory Pattern** | `MicroTopologyFactory` | ✅ Yes - Dynamic task creation | Use Python registry pattern |
| **Modular Structure** | Maven modules | ✅ Yes - Separation of concerns | Python packages |

---

### 1.3 Architecture Weaknesses to Improve

#### ❌ **Problem 1: Manual Bolt Creation**
```java
// Current: Manual creation for each task
public static class BloomFilterCheckBolt extends BaseTaskBolt {
    public BloomFilterCheckBolt(Properties p_) { super(p_); }
    @Override
    protected ITask getTaskInstance() { return new BloomFilterCheck(); }
}
```

**Improvement**: Generic adapter + registry
```python
# Proposed: One adapter, dynamic task loading
class TaskBolt(BaseTaskBolt):
    def __init__(self, task_class: Type[ITask], properties: dict):
        self.task = task_class()
        self.properties = properties
```

---

#### ❌ **Problem 2: Hardcoded Platform (Storm)**
```java
// Current: Tightly coupled to Storm
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Tuple;
```

**Improvement**: Multiple platform support
```python
# Proposed: Platform plugins
from pyriotbench.platforms import FlinkAdapter, BeamAdapter, RayAdapter

adapter = FlinkAdapter(task=MyTask(), config=config)
adapter = BeamAdapter(task=MyTask(), config=config)
adapter = RayAdapter(task=MyTask(), config=config)
```

---

#### ❌ **Problem 3: Limited Observability**
```java
// Current: Basic timing only
sw.getTime()/counter  // Average execution time
```

**Improvement**: Rich metrics and tracing
```python
# Proposed: OpenTelemetry integration
@traced_task
class MyTask(BaseTask):
    @measure_latency
    @count_invocations
    def do_task(self, data: Dict) -> float:
        # Automatic metrics: latency, throughput, errors
        pass
```

---

#### ❌ **Problem 4: Java-Specific ML Libraries**
```java
// Current: Weka (Java only)
import weka.classifiers.trees.J48;
import weka.core.Instances;
```

**Improvement**: Python ML ecosystem
```python
# Proposed: scikit-learn, PyTorch, TensorFlow
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LinearRegression
```

---

#### ❌ **Problem 5: Limited Async Support**
```java
// Current: Synchronous I/O
public Float doTaskLogic(Map map) {
    byte[] blob = cloudBlobClient.downloadBlob(...);  // Blocking
    return 1.0f;
}
```

**Improvement**: Async I/O for better performance
```python
# Proposed: AsyncIO support
async def do_task_logic(self, data: Dict) -> float:
    blob = await azure_client.download_blob_async(...)  # Non-blocking
    return 1.0
```

---

## 🎯 Part 2: Python Framework Evaluation

### 2.1 Platform Options

| Platform | Maturity | Python Support | Community | Portability | Recommendation |
|----------|----------|----------------|-----------|-------------|----------------|
| **Apache Flink** | ⭐⭐⭐⭐⭐ | PyFlink (native) | Large | High | **Primary** |
| **Apache Beam** | ⭐⭐⭐⭐⭐ | Python SDK | Large | Very High | **Primary** |
| **Ray** | ⭐⭐⭐⭐ | Native Python | Growing | Medium | **Secondary** |
| **Dask Streaming** | ⭐⭐⭐ | Native Python | Medium | Low | **Exploratory** |
| **Standalone** | N/A | Pure Python | N/A | Very High | **Testing/Dev** |

---

### 2.2 Recommended Primary Platform: Apache Beam

**Why Beam?**
1. ✅ **True Portability**: Run on Flink, Spark, Dataflow, Direct runner
2. ✅ **Python-First**: Mature Python SDK with excellent docs
3. ✅ **Unified Model**: Batch + Streaming with same API
4. ✅ **Cloud-Native**: Best integration with GCP, AWS, Azure
5. ✅ **Type Safety**: Optional type hints for pipeline validation

**Beam Architecture Fit**:
```python
# Beam's natural abstraction aligns with RIoTBench
class TaskDoFn(beam.DoFn):
    def __init__(self, task_class: Type[ITask], config: dict):
        self.task = task_class()
        self.config = config
    
    def setup(self):
        self.task.setup(logger, self.config)
    
    def process(self, element):
        result = self.task.do_task(element)
        if result is not None:
            yield result
    
    def teardown(self):
        self.task.tear_down()
```

**Beam Advantages for Benchmarking**:
- **Portable Execution**: Test locally (DirectRunner), deploy to Flink/Dataflow
- **Built-in Metrics**: Counters, distributions, gauges
- **Window/State Support**: Natural fit for windowed aggregations
- **Testing Framework**: Unit test pipelines easily

---

### 2.3 Secondary Platform: Apache Flink (PyFlink)

**Why Flink as Secondary?**
1. ✅ **Storm's Successor**: Natural migration path
2. ✅ **Performance**: Often fastest for streaming workloads
3. ✅ **State Management**: Most sophisticated state handling
4. ✅ **Event Time**: Best support for out-of-order events

**PyFlink Architecture Fit**:
```python
# PyFlink MapFunction wraps task
class TaskMapFunction(MapFunction):
    def __init__(self, task_class: Type[ITask], config: dict):
        self.task = task_class()
        self.config = config
    
    def open(self, runtime_context):
        self.task.setup(logger, self.config)
    
    def map(self, value):
        return self.task.do_task(value)
```

---

### 2.4 Standalone Mode (For Development/Testing)

**Why Standalone?**
1. ✅ **Fast Iteration**: No cluster setup required
2. ✅ **Unit Testing**: Test tasks in isolation
3. ✅ **Debugging**: Standard Python debugging tools
4. ✅ **CI/CD**: Fast automated testing

**Implementation**:
```python
# Simple in-process execution for testing
class StandaloneRunner:
    def __init__(self, task: ITask, config: dict):
        self.task = task
        self.config = config
    
    def run(self, input_file: str):
        self.task.setup(logger, self.config)
        with open(input_file) as f:
            for line in f:
                result = self.task.do_task({"D": line.strip()})
                print(result)
        self.task.tear_down()
```

---

## 🎯 Part 3: Proposed Python Architecture

### 3.1 Module Structure

```
pyriotbench/
├── core/                       # Platform-agnostic core
│   ├── __init__.py
│   ├── task.py                # ITask protocol, BaseTask
│   ├── registry.py            # Task registry/factory
│   ├── config.py              # Configuration management
│   ├── metrics.py             # Timing & instrumentation
│   └── types.py               # Common type definitions
│
├── tasks/                      # 26 benchmark implementations
│   ├── __init__.py
│   ├── parse/
│   │   ├── __init__.py
│   │   ├── annotate.py        # ANN
│   │   ├── csv_to_senml.py    # C2S
│   │   ├── senml_parse.py     # SML
│   │   └── xml_parse.py       # XML
│   ├── filter/
│   │   ├── __init__.py
│   │   ├── bloom_filter.py    # BLF
│   │   └── range_filter.py    # RGF
│   ├── statistics/
│   │   ├── __init__.py
│   │   ├── accumulator.py     # ACC
│   │   ├── average.py         # AVG
│   │   ├── distinct_count.py  # DAC
│   │   ├── kalman_filter.py   # KAL
│   │   ├── interpolation.py   # INP
│   │   └── second_moment.py   # SOM
│   ├── predict/
│   │   ├── __init__.py
│   │   ├── decision_tree_classify.py  # DTC
│   │   ├── decision_tree_train.py     # DTT
│   │   ├── linear_regression_predict.py  # MLR
│   │   ├── linear_regression_train.py    # MLT
│   │   └── sliding_linear_regression.py  # SLR
│   ├── io/
│   │   ├── __init__.py
│   │   ├── azure_blob.py      # ABD, ABU
│   │   ├── azure_table.py     # ATI, ATR
│   │   └── mqtt.py            # MQP, MQS
│   └── visualize/
│       ├── __init__.py
│       └── plot.py            # PLT
│
├── platforms/                  # Platform adapters
│   ├── __init__.py
│   ├── base.py                # Base adapter interface
│   ├── beam/
│   │   ├── __init__.py
│   │   ├── adapter.py         # Beam DoFn wrapper
│   │   ├── runner.py          # Pipeline builder
│   │   └── options.py         # Beam-specific config
│   ├── flink/
│   │   ├── __init__.py
│   │   ├── adapter.py         # PyFlink MapFunction
│   │   ├── runner.py          # Job builder
│   │   └── options.py         # Flink-specific config
│   ├── ray/
│   │   ├── __init__.py
│   │   ├── adapter.py         # Ray actor wrapper
│   │   └── runner.py          # Ray pipeline
│   └── standalone/
│       ├── __init__.py
│       └── runner.py          # Simple in-process runner
│
├── applications/               # 4 application benchmarks
│   ├── __init__.py
│   ├── etl.py                 # ETL topology
│   ├── stats.py               # STATS topology
│   ├── train.py               # TRAIN topology
│   └── predict.py             # PRED topology
│
├── datasets/                   # Dataset utilities
│   ├── __init__.py
│   ├── loader.py              # Data loading
│   ├── generator.py           # Synthetic data
│   └── schemas.py             # Data schemas
│
├── utils/                      # Shared utilities
│   ├── __init__.py
│   ├── logging.py             # Logging setup
│   ├── serialization.py       # Data serialization
│   └── ml_models.py           # ML model utilities
│
└── cli/                        # Command-line interface
    ├── __init__.py
    └── main.py                # Entry point
```

---

### 3.2 Core Task Abstraction (Python)

```python
# pyriotbench/core/task.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar, Protocol
from dataclasses import dataclass, field
import time
import logging

T = TypeVar('T')  # Input type
U = TypeVar('U')  # Output type

# Protocol-based interface (Python 3.8+)
class ITask(Protocol[T, U]):
    """
    Platform-agnostic task interface.
    All benchmark tasks must implement this protocol.
    """
    
    def setup(self, logger: logging.Logger, config: Dict[str, Any]) -> None:
        """
        Initialize task with logger and configuration.
        Called once before processing begins.
        
        Args:
            logger: Logger instance for task output
            config: Configuration dictionary (from properties/YAML)
        """
        ...
    
    def do_task(self, data: Dict[str, T]) -> Optional[float]:
        """
        Process a single data element.
        
        Args:
            data: Input data as dictionary (key "D" for default input)
        
        Returns:
            float: Status/result value (None = no output, -inf = error)
        """
        ...
    
    def get_last_result(self) -> Optional[U]:
        """
        Retrieve complex result from last do_task() call.
        Used when return value is more than a float.
        
        Returns:
            Optional result object (task-specific type)
        """
        ...
    
    def tear_down(self) -> float:
        """
        Cleanup and return performance metrics.
        Called once after all processing completes.
        
        Returns:
            float: Average execution time per call (seconds)
        """
        ...


@dataclass
class TaskMetrics:
    """Task execution metrics"""
    total_time: float = 0.0
    call_count: int = 0
    error_count: int = 0
    
    @property
    def avg_time(self) -> float:
        return self.total_time / self.call_count if self.call_count > 0 else 0.0


class BaseTask(ABC, Generic[T, U]):
    """
    Abstract base task with built-in timing and metrics.
    Implements template method pattern like Java AbstractTask.
    """
    
    DEFAULT_KEY = "D"
    
    def __init__(self):
        self.logger: Optional[logging.Logger] = None
        self.config: Dict[str, Any] = {}
        self._metrics = TaskMetrics()
        self._last_result: Optional[U] = None
    
    def setup(self, logger: logging.Logger, config: Dict[str, Any]) -> None:
        """Setup with timing initialization"""
        self.logger = logger
        self.config = config
        self._metrics = TaskMetrics()
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
            self._metrics.total_time += elapsed
            self._metrics.call_count += 1
            assert result is None or result >= 0, "Result must be non-negative or None"
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            self._metrics.total_time += elapsed
            self._metrics.call_count += 1
            self._metrics.error_count += 1
            self.logger.error(f"Error in {self.__class__.__name__}: {e}")
            return float('-inf')  # Signal error
    
    @abstractmethod
    def do_task_logic(self, data: Dict[str, T]) -> Optional[float]:
        """
        Child classes implement actual task logic here.
        No timing code needed - handled by do_task().
        """
        pass
    
    def get_last_result(self) -> Optional[U]:
        """Retrieve last complex result"""
        return self._last_result
    
    def _set_last_result(self, result: U) -> U:
        """Set complex result (for child classes)"""
        self._last_result = result
        return result
    
    def tear_down(self) -> float:
        """Cleanup and return average execution time"""
        self.logger.debug(f"{self.__class__.__name__} teardown: "
                         f"{self._metrics.call_count} calls, "
                         f"{self._metrics.avg_time:.6f}s avg")
        return self._metrics.avg_time


# Example: Simple task implementation
class NoOperationTask(BaseTask[str, None]):
    """No-op task for testing/baseline"""
    
    def setup(self, logger: logging.Logger, config: Dict[str, Any]) -> None:
        super().setup(logger, config)
        # Task-specific setup here
    
    def do_task_logic(self, data: Dict[str, str]) -> Optional[float]:
        # No operation - just return success
        return 0.0
```

**Key Improvements Over Java**:
1. ✅ **Type Hints**: Better IDE support and type checking
2. ✅ **Dataclasses**: Cleaner metrics structure
3. ✅ **Protocol**: Duck typing for flexibility
4. ✅ **Property**: Elegant metrics access
5. ✅ **Context Managers**: Could add `with task:` support

---

### 3.3 Platform Adapter Pattern (Python)

```python
# pyriotbench/platforms/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pyriotbench.core.task import ITask

class BasePlatformAdapter(ABC):
    """
    Base class for platform-specific adapters.
    Translates platform concepts to task interface.
    """
    
    def __init__(self, task_class: Type[ITask], config: Dict[str, Any]):
        self.task_class = task_class
        self.config = config
        self.task: Optional[ITask] = None
    
    @abstractmethod
    def initialize(self) -> None:
        """Platform-specific initialization"""
        pass
    
    @abstractmethod
    def process_element(self, element: Any) -> Any:
        """
        Process one element through the task.
        Platform provides element in native format,
        adapter converts to Dict for task.
        """
        pass
    
    @abstractmethod
    def finalize(self) -> None:
        """Platform-specific cleanup"""
        pass


# pyriotbench/platforms/beam/adapter.py
import apache_beam as beam
from apache_beam.metrics import Metrics
from typing import Dict, Type, Iterable
from pyriotbench.core.task import ITask
import logging

class TaskDoFn(beam.DoFn):
    """
    Apache Beam DoFn that wraps a RIoTBench task.
    Handles setup/teardown lifecycle and metrics.
    """
    
    def __init__(self, task_class: Type[ITask], config: Dict[str, Any]):
        self.task_class = task_class
        self.config = config
        self.task: Optional[ITask] = None
        
        # Beam metrics
        self.processed_counter = Metrics.counter(
            self.__class__, f'{task_class.__name__}_processed'
        )
        self.error_counter = Metrics.counter(
            self.__class__, f'{task_class.__name__}_errors'
        )
        self.latency_dist = Metrics.distribution(
            self.__class__, f'{task_class.__name__}_latency_ms'
        )
    
    def setup(self):
        """Called once per worker - initialize task"""
        import time
        logger = logging.getLogger('pyriotbench')
        self.task = self.task_class()
        self.task.setup(logger, self.config)
    
    def process(self, element: str) -> Iterable[Dict[str, Any]]:
        """Process one element"""
        import time
        start = time.perf_counter()
        
        # Convert element to task input format
        data = {"D": element}
        result = self.task.do_task(data)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.latency_dist.update(int(elapsed_ms))
        
        if result is not None:
            if result != float('-inf'):
                self.processed_counter.inc()
                # Yield result with metadata
                yield {
                    'input': element,
                    'result': result,
                    'task': self.task_class.__name__,
                    'latency_ms': elapsed_ms
                }
            else:
                self.error_counter.inc()
                # Could yield to dead-letter queue here
    
    def teardown(self):
        """Called once per worker - cleanup"""
        if self.task:
            avg_time = self.task.tear_down()
            logging.info(f"Task {self.task_class.__name__} avg time: {avg_time:.6f}s")


# pyriotbench/platforms/flink/adapter.py
from pyflink.datastream import MapFunction
from typing import Dict, Type
from pyriotbench.core.task import ITask
import logging

class TaskMapFunction(MapFunction):
    """
    PyFlink MapFunction that wraps a RIoTBench task.
    """
    
    def __init__(self, task_class: Type[ITask], config: Dict[str, Any]):
        self.task_class = task_class
        self.config = config
        self.task: Optional[ITask] = None
    
    def open(self, runtime_context):
        """Flink initialization - called once per task"""
        logger = logging.getLogger('pyriotbench')
        self.task = self.task_class()
        self.task.setup(logger, self.config)
    
    def map(self, value: str) -> Dict[str, Any]:
        """Process one element"""
        data = {"D": value}
        result = self.task.do_task(data)
        
        if result is not None and result != float('-inf'):
            return {
                'input': value,
                'result': result,
                'task': self.task_class.__name__
            }
        return None
    
    def close(self):
        """Flink cleanup"""
        if self.task:
            self.task.tear_down()


# pyriotbench/platforms/standalone/runner.py
from typing import Type, Dict, Any, Iterator
from pyriotbench.core.task import ITask
import logging

class StandaloneRunner:
    """
    Simple in-process task runner for testing/development.
    No distributed framework required.
    """
    
    def __init__(self, task_class: Type[ITask], config: Dict[str, Any]):
        self.task_class = task_class
        self.config = config
        self.logger = logging.getLogger('pyriotbench')
    
    def run(self, input_source: Iterator[str]) -> Iterator[Dict[str, Any]]:
        """
        Run task on input iterator.
        
        Args:
            input_source: Iterator of input strings (e.g., file lines)
        
        Yields:
            Result dictionaries
        """
        # Setup
        task = self.task_class()
        task.setup(self.logger, self.config)
        
        # Process
        for element in input_source:
            data = {"D": element}
            result = task.do_task(data)
            
            if result is not None and result != float('-inf'):
                yield {
                    'input': element,
                    'result': result,
                    'task': self.task_class.__name__
                }
        
        # Teardown
        avg_time = task.tear_down()
        self.logger.info(f"Average execution time: {avg_time:.6f}s")
```

**Key Improvements**:
1. ✅ **One Adapter per Platform**: No manual bolt creation
2. ✅ **Metrics Built-in**: Beam counters, Flink metrics
3. ✅ **Type Safety**: Type hints throughout
4. ✅ **Testability**: Standalone runner for easy testing

---

### 3.4 Task Registry & Factory

```python
# pyriotbench/core/registry.py
from typing import Dict, Type, Optional
from pyriotbench.core.task import ITask

class TaskRegistry:
    """
    Central registry for all benchmark tasks.
    Enables dynamic task loading and discovery.
    """
    
    _tasks: Dict[str, Type[ITask]] = {}
    
    @classmethod
    def register(cls, name: str, task_class: Type[ITask]) -> None:
        """Register a task class"""
        cls._tasks[name] = task_class
    
    @classmethod
    def get(cls, name: str) -> Type[ITask]:
        """Get task class by name"""
        if name not in cls._tasks:
            raise ValueError(f"Unknown task: {name}")
        return cls._tasks[name]
    
    @classmethod
    def list_tasks(cls) -> Dict[str, Type[ITask]]:
        """List all registered tasks"""
        return cls._tasks.copy()


# Decorator for automatic registration
def register_task(name: str):
    """Decorator to auto-register task classes"""
    def decorator(cls: Type[ITask]) -> Type[ITask]:
        TaskRegistry.register(name, cls)
        return cls
    return decorator


# Usage in task implementations
from pyriotbench.core.registry import register_task
from pyriotbench.core.task import BaseTask

@register_task("bloom_filter")
class BloomFilterCheck(BaseTask[str, float]):
    def do_task_logic(self, data: Dict[str, str]) -> Optional[float]:
        # Implementation
        pass

@register_task("average")
class BlockWindowAverage(BaseTask[str, float]):
    def do_task_logic(self, data: Dict[str, str]) -> Optional[float]:
        # Implementation
        pass

# Now tasks can be loaded dynamically
task_class = TaskRegistry.get("bloom_filter")
task = task_class()
```

---

### 3.5 Configuration System

```python
# pyriotbench/core/config.py
from typing import Any, Dict, Optional
from pathlib import Path
import yaml
import os
from dataclasses import dataclass, field

@dataclass
class TaskConfig:
    """Configuration for task execution"""
    # Parse configuration
    parse_senml_enabled: bool = True
    
    # Filter configuration
    filter_bloom_model_path: Optional[str] = None
    filter_range_min: float = 0.0
    filter_range_max: float = 100.0
    
    # Aggregate configuration
    aggregate_window_size: int = 100
    aggregate_use_field: int = 0
    
    # Classification configuration
    classification_model_path: Optional[str] = None
    classification_train_freq: int = 100
    
    # I/O configuration
    azure_account_name: Optional[str] = None
    azure_account_key: Optional[str] = None
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    
    # Custom properties (for extension)
    custom: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_properties_file(cls, path: str) -> 'TaskConfig':
        """Load from Java .properties file (backward compat)"""
        config = cls()
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip().lower().replace('.', '_')
                        value = value.strip()
                        
                        # Try to parse as number/boolean
                        if value.lower() == 'true':
                            value = True
                        elif value.lower() == 'false':
                            value = False
                        else:
                            try:
                                value = int(value)
                            except ValueError:
                                try:
                                    value = float(value)
                                except ValueError:
                                    pass  # Keep as string
                        
                        config.custom[key] = value
        return config
    
    @classmethod
    def from_yaml(cls, path: str) -> 'TaskConfig':
        """Load from YAML file (modern approach)"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> 'TaskConfig':
        """Load from environment variables"""
        config = cls()
        # Map env vars to config fields
        config.azure_account_name = os.getenv('AZURE_ACCOUNT_NAME')
        config.azure_account_key = os.getenv('AZURE_ACCOUNT_KEY')
        config.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        # ... more mappings
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for task.setup()"""
        result = {
            'PARSE.SENML_ENABLED': self.parse_senml_enabled,
            'FILTER.BLOOM_FILTER.MODEL_PATH': self.filter_bloom_model_path,
            'AGGREGATE.BLOCK_COUNT.WINDOW_SIZE': self.aggregate_window_size,
            # ... all mappings
        }
        result.update(self.custom)
        return result


# Example YAML config (modern approach)
"""
# config.yaml
parse_senml_enabled: true

filter_bloom_model_path: /path/to/model
filter_range_min: 0.0
filter_range_max: 100.0

aggregate_window_size: 100
aggregate_use_field: 5

classification_model_path: /path/to/model.pkl
classification_train_freq: 100

azure_account_name: ${AZURE_ACCOUNT_NAME}
azure_account_key: ${AZURE_ACCOUNT_KEY}

mqtt_broker: mqtt.example.com
mqtt_port: 1883
"""
```

---

## 🎯 Part 4: Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Core abstraction layer + standalone runner

#### Tasks:
- [ ] **1.1** Setup Python project structure
  - Create package layout (`pyriotbench/`)
  - Setup `pyproject.toml` with dependencies
  - Configure linting (ruff/black), type checking (mypy)
  
- [ ] **1.2** Implement core abstractions
  - `ITask` protocol
  - `BaseTask` abstract class with timing
  - `TaskMetrics` dataclass
  
- [ ] **1.3** Configuration system
  - `TaskConfig` class
  - Support `.properties`, YAML, env vars
  - Backward compatibility with Java config
  
- [ ] **1.4** Task registry
  - `TaskRegistry` singleton
  - `@register_task` decorator
  - Dynamic task loading
  
- [ ] **1.5** Standalone runner
  - `StandaloneRunner` class
  - File input/output
  - Basic logging/metrics

#### Deliverables:
```bash
pyriotbench/
├── core/
│   ├── task.py          ✅ ITask, BaseTask
│   ├── registry.py      ✅ TaskRegistry
│   ├── config.py        ✅ TaskConfig
│   └── metrics.py       ✅ TaskMetrics
└── platforms/
    └── standalone/
        └── runner.py    ✅ StandaloneRunner
```

#### Success Criteria:
- [ ] Can create and run a `NoOperationTask`
- [ ] Configuration loads from YAML/properties
- [ ] Registry can register/retrieve tasks
- [ ] Standalone runner processes a file

---

### Phase 2: Core Benchmarks (Weeks 3-4)

**Goal**: Implement 5 representative benchmarks (one per category)

#### Tasks:
- [ ] **2.1** Parse: SenML Parsing (SML)
  - Port from Java `SenMLParse.java`
  - Use `json` standard library
  - Add tests with TAXI dataset sample
  
- [ ] **2.2** Filter: Bloom Filter (BLF)
  - Port from Java `BloomFilterCheck.java`
  - Use `pybloom-live` or `guava` equivalent
  - Load pre-trained models
  
- [ ] **2.3** Statistics: Block Window Average (AVG)
  - Port from Java `BlockWindowAverage.java`
  - Implement windowing logic
  - Test state management
  
- [ ] **2.4** Predict: Decision Tree Classify (DTC)
  - Port from Java `DecisionTreeClassify.java`
  - Use `scikit-learn` instead of Weka
  - Load pre-trained sklearn models
  
- [ ] **2.5** I/O: Azure Blob Download (ABD)
  - Port from Java `AzureBlobDownloadTask.java`
  - Use `azure-storage-blob` Python SDK
  - Add async version

#### Deliverables:
```bash
pyriotbench/tasks/
├── parse/senml_parse.py         ✅
├── filter/bloom_filter.py       ✅
├── statistics/average.py        ✅
├── predict/decision_tree_classify.py  ✅
└── io/azure_blob.py             ✅
```

#### Success Criteria:
- [ ] All 5 tasks pass unit tests
- [ ] Standalone runner executes all 5 tasks
- [ ] Results match Java version (within 5% for timing)
- [ ] Models load correctly (Bloom, DT)

---

### Phase 3: Apache Beam Integration (Weeks 5-6)

**Goal**: Beam adapter + first application benchmark

#### Tasks:
- [ ] **3.1** Beam adapter implementation
  - `TaskDoFn` class
  - Setup/teardown lifecycle
  - Beam metrics integration
  
- [ ] **3.2** Beam runner/builder
  - Pipeline construction utilities
  - Input sources (file, Kafka, Pub/Sub)
  - Output sinks
  
- [ ] **3.3** ETL application benchmark
  - Port `ETLTopology.java`
  - 8-stage pipeline: Parse → Annotate → Filter → Interpolate → Join → Annotate → Average → Blob Upload
  - TAXI dataset
  
- [ ] **3.4** Testing & validation
  - Compare with Java Storm ETL results
  - Validate throughput/latency
  - Test on DirectRunner and Dataflow

#### Deliverables:
```bash
pyriotbench/
├── platforms/beam/
│   ├── adapter.py       ✅ TaskDoFn
│   ├── runner.py        ✅ Pipeline builder
│   └── options.py       ✅ Beam options
└── applications/
    └── etl.py           ✅ ETL benchmark
```

#### Success Criteria:
- [ ] ETL runs on DirectRunner
- [ ] ETL runs on Dataflow
- [ ] Throughput within 20% of Java/Storm
- [ ] All 8 stages process correctly

---

### Phase 4: Expand Benchmarks (Weeks 7-10)

**Goal**: Complete all 26 micro-benchmarks

#### Breakdown:
- **Week 7**: Parse (ANN, C2S, XML) + Filter (RGF)
- **Week 8**: Statistics (ACC, DAC, KAL, INP, SOM)
- **Week 9**: Predict (DTT, MLR, MLT, SLR)
- **Week 10**: I/O (ABU, ATI, ATR, MQP, MQS) + Visualize (PLT)

#### Success Criteria:
- [ ] All 26 benchmarks implemented
- [ ] All pass unit tests
- [ ] All run in standalone mode
- [ ] All work with Beam adapter

---

### Phase 5: Additional Platforms (Weeks 11-12)

**Goal**: PyFlink and Ray adapters

#### Tasks:
- [ ] **5.1** PyFlink adapter
  - `TaskMapFunction` class
  - Flink job builder
  - State management for windowed operations
  
- [ ] **5.2** Ray adapter
  - Ray actor wrapper for tasks
  - Ray pipeline construction
  - Distributed execution

#### Success Criteria:
- [ ] ETL runs on PyFlink
- [ ] ETL runs on Ray
- [ ] Performance comparable to Beam

---

### Phase 6: Application Benchmarks (Weeks 13-14)

**Goal**: Complete STATS, TRAIN, PRED applications

#### Tasks:
- [ ] **6.1** STATS application
  - Parallel statistics computation
  - Multiple aggregation windows
  
- [ ] **6.2** TRAIN application
  - Batch model training
  - Model checkpointing
  
- [ ] **6.3** PRED application
  - Real-time prediction pipeline
  - Model loading/serving

#### Success Criteria:
- [ ] All 4 applications work on Beam
- [ ] Results match Java versions
- [ ] Documentation complete

---

### Phase 7: Polish & Documentation (Weeks 15-16)

**Goal**: Production-ready release

#### Tasks:
- [ ] **7.1** Performance tuning
  - Profile hot paths
  - Optimize data serialization
  - Add caching where appropriate
  
- [ ] **7.2** Testing & CI/CD
  - Comprehensive unit tests
  - Integration tests
  - Performance regression tests
  - GitHub Actions CI
  
- [ ] **7.3** Documentation
  - API documentation (Sphinx)
  - User guide (getting started, examples)
  - Migration guide (Java → Python)
  - Performance comparison report
  
- [ ] **7.4** Packaging
  - PyPI package
  - Docker images
  - Helm charts for Kubernetes

---

## 🎯 Part 5: Key Design Decisions

### 5.1 State Management Strategy

**Challenge**: Python GIL + multithreading vs Java's model

**Decision**: Use instance-based state (like Java), but add options:

```python
# Option 1: Instance state (like Java - default)
class BlockWindowAverage(BaseTask):
    def __init__(self):
        super().__init__()
        self.window_sum = 0.0
        self.window_count = 0

# Option 2: External state (for distributed)
from pyriotbench.state import StateManager

class BlockWindowAverage(BaseTask):
    def setup(self, logger, config):
        super().setup(logger, config)
        self.state = StateManager.get_state("window_state")
    
    def do_task_logic(self, data):
        self.state.update("sum", lambda x: x + value)
        self.state.update("count", lambda x: x + 1)
```

**Rationale**: Start simple (instance), add distributed state later

---

### 5.2 ML Library Choice

**Challenge**: Weka (Java) → ? (Python)

**Decision**: Use scikit-learn as primary, support PyTorch/TensorFlow

```python
# scikit-learn for classical ML (most tasks)
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LinearRegression

# Option for deep learning (future)
import torch
from transformers import AutoModel
```

**Rationale**: 
- scikit-learn matches Weka functionality
- Broader ecosystem for advanced models
- Easy model serialization (pickle/joblib)

---

### 5.3 Async I/O Support

**Challenge**: Java blocking I/O → Python async

**Decision**: Support both sync and async versions

```python
# Synchronous (default)
class AzureBlobDownload(BaseTask):
    def do_task_logic(self, data):
        blob = self.client.download_blob(data['blob_name'])
        return 1.0

# Asynchronous (opt-in)
class AzureBlobDownloadAsync(BaseTask):
    async def do_task_logic_async(self, data):
        blob = await self.client.download_blob_async(data['blob_name'])
        return 1.0
```

**Rationale**: Async optional, not required for initial version

---

### 5.4 Serialization Format

**Challenge**: Java objects → Python objects across network

**Decision**: Use Protocol Buffers or JSON (configurable)

```python
# JSON (human-readable, debugging)
data = {"sensor_id": "s1", "value": 42.0}

# Protobuf (performance, production)
message = SensorData(sensor_id="s1", value=42.0)
```

**Rationale**: JSON first for simplicity, Protobuf for performance

---

### 5.5 Metrics & Observability

**Challenge**: Basic timing → modern observability

**Decision**: Integrate OpenTelemetry

```python
from opentelemetry import trace, metrics

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

class BaseTask:
    @tracer.start_as_current_span("do_task")
    def do_task(self, data):
        with meter.record_latency("task_duration"):
            return self.do_task_logic(data)
```

**Rationale**: Standard observability, works with all platforms

---

## 🎯 Part 6: Risk Mitigation

### Risk 1: Performance Degradation

**Risk**: Python slower than Java

**Mitigation**:
- ✅ Use NumPy/Pandas for heavy computation
- ✅ Profile and optimize hot paths
- ✅ Consider Cython for critical sections
- ✅ Benchmark early and often

**Acceptance**: 20-30% slower acceptable if portable

---

### Risk 2: ML Model Compatibility

**Risk**: Weka models not usable in Python

**Mitigation**:
- ✅ Re-train models with scikit-learn on same data
- ✅ Validate predictions match Java version
- ✅ Document conversion process
- ✅ Provide pre-trained sklearn models

---

### Risk 3: Platform API Changes

**Risk**: Beam/Flink APIs change over time

**Mitigation**:
- ✅ Pin dependencies in `pyproject.toml`
- ✅ Comprehensive adapter tests
- ✅ Version compatibility matrix
- ✅ Abstract away platform specifics

---

### Risk 4: State Management Complexity

**Risk**: Distributed state harder in Python

**Mitigation**:
- ✅ Start with stateless tasks
- ✅ Use platform's native state (Beam State API, Flink state)
- ✅ Extensive testing of stateful tasks
- ✅ Clear documentation of state guarantees

---

## 🎯 Part 7: Success Metrics

### Functional Metrics
- [ ] All 26 micro-benchmarks pass correctness tests
- [ ] All 4 application benchmarks produce expected outputs
- [ ] Results match Java version (within 10% for deterministic tasks)

### Performance Metrics
- [ ] Throughput: Within 30% of Java/Storm version
- [ ] Latency: p50, p95, p99 comparable
- [ ] Memory: Similar or better than Java

### Portability Metrics
- [ ] Runs on Beam (DirectRunner, DataflowRunner)
- [ ] Runs on PyFlink (Local, Cluster)
- [ ] Runs standalone (for testing)
- [ ] Same task code for all platforms

### Quality Metrics
- [ ] >80% test coverage
- [ ] Type hints on all public APIs
- [ ] Zero high-severity security issues
- [ ] Documentation for all 26 tasks

---

## 🎯 Part 8: Next Steps

### Immediate Actions (This Week)
1. **Review and approve this plan** with stakeholders
2. **Setup GitHub repository** (`pyriotbench`)
3. **Create project skeleton** (Phase 1 structure)
4. **Setup dev environment** (Python 3.10+, dependencies)
5. **Implement `NoOperationTask`** as proof of concept

### First Milestone (Week 2)
- Complete Phase 1 (Foundation)
- Demo: NoOp task running in standalone mode
- Validate: Configuration loading, registry, metrics

### Research Questions to Resolve
1. Which Beam runner for benchmarking? (DirectRunner vs Dataflow)
2. How to handle Weka model conversion? (Automated vs manual)
3. Should we support Kafka as input? (Kafka → Beam → Tasks)
4. Docker-based deployment strategy?

---

## 📊 Appendix A: Technology Stack

| Component | Java (Original) | Python (Proposed) | Notes |
|-----------|----------------|-------------------|-------|
| **Language** | Java 7+ | Python 3.10+ | Type hints, async |
| **Stream Platform** | Apache Storm 1.0.1 | Apache Beam 2.50+ | Primary platform |
| **Secondary Platform** | - | PyFlink 1.17+ | Alternative |
| **ML Library** | Weka 3.6.6 | scikit-learn 1.3+ | Classical ML |
| **Deep Learning** | - | PyTorch 2.0+ (optional) | Future expansion |
| **Cloud Storage** | Azure SDK 4.0 | azure-storage-blob 12.x | Compatible |
| **MQTT** | Paho 1.0.2 | paho-mqtt 1.6+ | Compatible |
| **Bloom Filter** | Guava | pybloom-live | Compatible |
| **Stats** | Commons Math 3.5 | NumPy + SciPy | Richer |
| **Visualization** | XChart | Matplotlib/Plotly | More options |
| **Config** | .properties | YAML + env vars | Modern |
| **Build** | Maven | Poetry/pip | Standard Python |
| **Testing** | JUnit | pytest | Standard Python |
| **CI/CD** | - | GitHub Actions | Automated |
| **Observability** | Log4j | OpenTelemetry | Modern |
| **Type Checking** | Javac | mypy | Static analysis |

---

## 📊 Appendix B: Effort Estimation

| Phase | Duration | Person-Weeks | Critical Path |
|-------|----------|--------------|---------------|
| Phase 1: Foundation | 2 weeks | 2 | ⭐ Yes |
| Phase 2: Core Benchmarks | 2 weeks | 2 | ⭐ Yes |
| Phase 3: Beam Integration | 2 weeks | 2 | ⭐ Yes |
| Phase 4: All Benchmarks | 4 weeks | 4 | No |
| Phase 5: Multi-Platform | 2 weeks | 2 | No |
| Phase 6: Applications | 2 weeks | 2 | No |
| Phase 7: Polish | 2 weeks | 2 | No |
| **Total** | **16 weeks** | **16** | **4 months** |

**Assumptions**:
- 1 full-time developer
- Familiar with Python and streaming systems
- Access to Azure/cloud resources for testing

---

## 📊 Appendix C: File Count Comparison

| Module | Java Files | Python Files (Est.) | Ratio |
|--------|-----------|---------------------|-------|
| Core Abstraction | 5 | 5 | 1:1 |
| Tasks (26) | 26 | 26 | 1:1 |
| Storm Integration | 15 | 0 | N/A |
| Beam Integration | 0 | 10 | New |
| Flink Integration | 0 | 8 | New |
| Applications | 4 | 4 | 1:1 |
| Tests | 20 | 50+ | More tests |
| **Total** | ~70 | ~110 | More modular |

**Note**: More Python files due to:
- Multiple platform adapters (Beam, Flink, Ray, Standalone)
- Richer test coverage
- Separate files for async variants

---

## ✅ Approval Checklist

Before proceeding to implementation:

- [ ] **Architecture approved** - Core abstractions sound?
- [ ] **Technology stack approved** - Libraries appropriate?
- [ ] **Roadmap approved** - Timeline realistic?
- [ ] **Success metrics approved** - Goals achievable?
- [ ] **Resources allocated** - Developer time, cloud budget?
- [ ] **Risks understood** - Mitigation plans acceptable?

---

**Document Status**: Ready for Review  
**Next Review**: After Phase 1 completion  
**Maintained By**: PyRIoTBench Team  
**Version History**:
- v1.0 (2025-10-09): Initial planning document

