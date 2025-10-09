# PyRIoTBench: Key Decisions & Rationale

**Purpose**: Document critical architectural decisions for the Python port  
**Format**: Architecture Decision Records (ADRs)

---

## ADR-001: Use Python 3.10+ as Base Language

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Need to choose Python version for the port.

### Decision
Use **Python 3.10+** as the minimum supported version.

### Rationale

**For Python 3.10+**:
- ✅ **Type hints**: Structural pattern matching, better Union syntax (`|`)
- ✅ **Performance**: 10-15% faster than 3.9
- ✅ **Dataclasses**: Better frozen and slots support
- ✅ **asyncio**: Mature async/await patterns
- ✅ **Ecosystem**: All modern libraries support it

**Against Python 3.8/3.9**:
- ❌ Less expressive type hints
- ❌ Missing structural pattern matching
- ❌ Slightly slower

**Against Python 3.11+**:
- ⚠️ Some cloud platforms not yet updated
- ⚠️ Some dependencies may lag

### Consequences
- Clean, modern Python code
- Better performance than older versions
- Some users may need to upgrade Python
- All target platforms (Beam, Flink, Ray) support 3.10+

---

## ADR-002: Apache Beam as Primary Platform

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Need to choose primary streaming platform for benchmarks.

### Decision
Use **Apache Beam** as the primary platform, with PyFlink and Ray as secondary targets.

### Rationale

**For Apache Beam**:
- ✅ **True portability**: Write once, run on Flink/Spark/Dataflow/Direct
- ✅ **Mature Python SDK**: Excellent documentation and examples
- ✅ **Unified model**: Same code for batch and streaming
- ✅ **Cloud-native**: Best GCP/AWS/Azure integration
- ✅ **Community**: Large, active Python community
- ✅ **Type safety**: Optional type hints for pipeline validation
- ✅ **Testing**: Built-in testing framework (DirectRunner)

**Against PyFlink**:
- ⚠️ Flink-specific (not portable to other runners)
- ⚠️ Python SDK less mature than Beam
- ⚠️ Smaller Python community

**Against Ray**:
- ⚠️ Different programming model (actors, not streaming)
- ⚠️ Less focus on pure streaming workloads
- ⚠️ Weaker cloud integrations

**Against Storm**:
- ❌ Legacy (last release 2018, moved to attic)
- ❌ No Python support
- ❌ Superseded by Flink

### Consequences
- Best portability across cloud providers
- Can still target Flink via FlinkRunner
- PyFlink adapter as secondary option
- Excellent developer experience for Python users

### Notes
RIoTBench Java uses Storm because it was state-of-art in 2016. In 2025, Beam is the modern equivalent with better portability.

---

## ADR-003: Protocol-Based Task Interface

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Java uses `interface ITask<T,U>`. How to translate to Python?

### Decision
Use Python **Protocol** (structural subtyping) instead of ABC (nominal subtyping).

### Rationale

**For Protocol**:
- ✅ **Flexibility**: Duck typing - any class matching signature works
- ✅ **No inheritance required**: Tasks can implement ITask without inheriting
- ✅ **Better for testing**: Easy to create mock tasks
- ✅ **Type checking**: mypy validates at compile time
- ✅ **More Pythonic**: Matches Python's duck typing philosophy

**Against ABC (Abstract Base Class)**:
- ⚠️ Requires explicit inheritance
- ⚠️ More rigid, less flexible
- ⚠️ Harder to mock in tests

### Implementation

```python
# Protocol (chosen)
from typing import Protocol

class ITask(Protocol):
    def setup(self, logger, config) -> None: ...
    def do_task(self, data) -> Optional[float]: ...
    def get_last_result(self) -> Optional[Any]: ...
    def tear_down(self) -> float: ...

# Any class matching this signature is automatically an ITask
# No need to explicitly inherit

# ABC (not chosen)
from abc import ABC, abstractmethod

class ITask(ABC):
    @abstractmethod
    def setup(self, logger, config) -> None: pass
    # ... requires explicit inheritance
```

### Consequences
- More flexible task implementations
- Better interoperability with third-party code
- Still get type checking benefits
- Can mix with ABC for `BaseTask` (concrete implementation)

---

## ADR-004: Preserve Java Property Names

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Java uses properties like `AGGREGATE.BLOCK_COUNT.WINDOW_SIZE`. Python convention is `snake_case`.

### Decision
**Support both**: Python-style internally, Java-style for backward compatibility.

### Rationale

**For dual support**:
- ✅ **Migration**: Easy to migrate from Java properties files
- ✅ **Comparison**: Can use same config for Java and Python benchmarks
- ✅ **Pythonic**: Python code uses `snake_case`
- ✅ **Documentation**: Easier to reference Java docs

**Implementation**:
```python
class TaskConfig(BaseModel):
    # Python style (internal)
    aggregate_block_window_size: int = 100
    
    def to_flat_dict(self):
        # Java style (for tasks)
        return {
            'AGGREGATE.BLOCK_COUNT.WINDOW_SIZE': self.aggregate_block_window_size,
            # ...
        }
    
    @classmethod
    def from_properties(cls, path: str):
        # Load Java properties file
        # Convert to Python style
```

### Consequences
- Can use existing Java properties files
- Python code remains idiomatic
- Need to maintain mapping between styles
- Documentation must show both forms

---

## ADR-005: scikit-learn Instead of Weka

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Java RIoTBench uses Weka for ML. Need Python alternative.

### Decision
Use **scikit-learn** as primary ML library, with support for PyTorch/TensorFlow.

### Rationale

**For scikit-learn**:
- ✅ **Feature parity**: Has all Weka algorithms (DT, LR, etc.)
- ✅ **Better API**: More Pythonic and consistent
- ✅ **Performance**: Often faster than Weka
- ✅ **Ecosystem**: Better integration with NumPy, Pandas
- ✅ **Documentation**: Excellent docs and examples
- ✅ **Active**: Regular updates, large community
- ✅ **Serialization**: Easy model save/load (pickle, joblib)

**Against Weka**:
- ❌ Java-only (no Python bindings worth using)
- ❌ Would require JNI/py4j (slow, complex)
- ❌ Older library, less active

**Against PyTorch/TensorFlow**:
- ⚠️ Overkill for simple ML (DT, LR)
- ⚠️ Higher overhead
- ⚠️ Harder to train simple models
- ✅ But: Can still use for advanced benchmarks

### Implementation Strategy

```python
# Phase 1: scikit-learn for classical ML
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LinearRegression

# Phase 2 (optional): Deep learning
import torch
from transformers import AutoModel
```

### Consequences
- Need to retrain models with scikit-learn
- Must validate predictions match Weka (within numerical precision)
- Opens door to modern ML (transformers, etc.)
- Better Python ecosystem integration

### Model Migration
1. Extract Weka training data
2. Retrain with scikit-learn
3. Validate predictions match
4. Provide pre-trained models
5. Document conversion process

---

## ADR-006: Async I/O Support (Optional)

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Java uses synchronous I/O. Python has async/await. Should we support async?

### Decision
Support **both sync and async**, with sync as default.

### Rationale

**For optional async**:
- ✅ **Performance**: Non-blocking I/O for Azure, MQTT
- ✅ **Scalability**: More concurrent connections
- ✅ **Modern**: AsyncIO is Python standard
- ✅ **Framework support**: Beam/Flink can use async

**Against mandatory async**:
- ⚠️ More complex code
- ⚠️ Harder to debug
- ⚠️ Not all tasks benefit

### Implementation

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
    
    def do_task_logic(self, data):
        # Fallback: run async in sync context
        return asyncio.run(self.do_task_logic_async(data))
```

### Consequences
- Better I/O performance for async tasks
- Complexity isolated to I/O tasks
- Stateless tasks stay simple (sync)
- Can benchmark sync vs async performance

---

## ADR-007: Pydantic for Configuration

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Java uses `.properties` files. Python has many config options (YAML, TOML, JSON, env vars).

### Decision
Use **Pydantic** models with **YAML** as primary format, supporting `.properties` for backward compat.

### Rationale

**For Pydantic**:
- ✅ **Type safety**: Runtime validation
- ✅ **Documentation**: Field descriptions built-in
- ✅ **Validation**: Custom validators
- ✅ **IDE support**: Autocomplete
- ✅ **Environment variables**: Automatic loading
- ✅ **Multiple formats**: YAML, JSON, env vars
- ✅ **Nested config**: Better than flat properties

**Against raw dictionaries**:
- ❌ No type checking
- ❌ No validation
- ❌ Easy to make typos

**Against dataclasses**:
- ⚠️ No validation
- ⚠️ No serialization helpers

### Implementation

```python
# config.yaml (primary)
aggregate:
  block_window_size: 100
  use_field_index: 5

# config.properties (backward compat)
AGGREGATE.BLOCK_COUNT.WINDOW_SIZE=100
AGGREGATE.BLOCK_COUNT.USE_MSG_FIELD=5

# Python code
class AggregateConfig(BaseModel):
    block_window_size: int = Field(default=100, gt=0)
    use_field_index: int = Field(default=5, ge=0)

config = PyRIoTBenchConfig.from_yaml('config.yaml')
# or
config = PyRIoTBenchConfig.from_properties('config.properties')
```

### Consequences
- Better developer experience (validation, autocomplete)
- Can still use Java config files
- Need to maintain dual format support
- More lines of code, but safer

---

## ADR-008: OpenTelemetry for Observability

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Java has basic timing. Modern systems need richer metrics.

### Decision
Integrate **OpenTelemetry** for metrics and tracing (optional, not required).

### Rationale

**For OpenTelemetry**:
- ✅ **Standard**: Industry standard (CNCF)
- ✅ **Rich metrics**: Counters, histograms, gauges
- ✅ **Distributed tracing**: Cross-service visibility
- ✅ **Multi-backend**: Prometheus, Jaeger, Datadog, etc.
- ✅ **No vendor lock-in**: Portable across platforms
- ✅ **Automatic instrumentation**: Libraries auto-instrumented

**Against custom metrics**:
- ❌ Reinventing the wheel
- ❌ No standard format
- ❌ Harder to integrate with monitoring tools

**Against no observability**:
- ❌ Hard to debug performance issues
- ❌ No production visibility

### Implementation

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

### Consequences
- Better production observability
- Can export to any monitoring system
- Optional (basic timing still works)
- Slight overhead (minimal for most tasks)

---

## ADR-009: Standalone Runner for Testing

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Need fast iteration during development. Beam has overhead even with DirectRunner.

### Decision
Implement **StandaloneRunner** for file-based testing (no distributed framework).

### Rationale

**For standalone runner**:
- ✅ **Fast**: No framework overhead
- ✅ **Simple**: Just read file, process, write file
- ✅ **Debug**: Use standard Python debugger
- ✅ **Unit tests**: No need for Beam in tests
- ✅ **CI/CD**: Fast automated testing

**Against Beam-only**:
- ⚠️ Slower iteration
- ⚠️ More complex debugging
- ⚠️ Harder to run simple tests

### Implementation

```python
runner = StandaloneRunner(MyTask, config)
runner.run_file('input.txt', 'output.txt')

# vs Beam (heavier)
with beam.Pipeline() as p:
    (p 
     | beam.io.ReadFromText('input.txt')
     | beam.ParDo(TaskDoFn(MyTask, config))
     | beam.io.WriteToText('output.txt'))
```

### Consequences
- Faster development cycle
- Easier debugging
- Not for production (use Beam/Flink)
- Need to maintain both runners

---

## ADR-010: Task Registry with Decorator

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Java uses manual factory pattern. How to make task discovery easier in Python?

### Decision
Use **decorator-based registration** with central registry.

### Rationale

**For decorator**:
- ✅ **Automatic**: Registration at import time
- ✅ **Clean**: No boilerplate
- ✅ **Pythonic**: Idiomatic Python pattern
- ✅ **Discoverable**: `TaskRegistry.list_tasks()`
- ✅ **Dynamic**: Load tasks by name

**Against manual factory**:
- ❌ More boilerplate
- ❌ Easy to forget to register

### Implementation

```python
# Old way (Java)
class MyTaskBolt extends BaseTaskBolt {
    protected ITask getTaskInstance() {
        return new MyTask();
    }
}
# Register manually in factory

# New way (Python)
@register_task("my_task")
class MyTask(BaseTask):
    pass

# Automatic registration, dynamic loading
task_class = TaskRegistry.get("my_task")
```

### Consequences
- Less boilerplate
- Easier to add new tasks
- Must import task module to register (solve with `__init__.py`)
- Better CLI (`list-tasks` command)

---

## ADR-011: Same Dataset Files

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Should we use same datasets as Java version or create new ones?

### Decision
Use **same dataset files** (TAXI, SYS, FIT, CITY, GRID).

### Rationale

**For same datasets**:
- ✅ **Comparability**: Direct comparison with Java results
- ✅ **Validation**: Verify correctness
- ✅ **Research**: Reproducible results
- ✅ **Documentation**: Reference Java papers

**Against new datasets**:
- ⚠️ Not comparable
- ⚠️ Can't validate against Java

### Consequences
- Need to support SenML format (JSON)
- CSV formats stay same
- Model files need retraining (Weka → sklearn)
- Can add new datasets later

---

## ADR-012: Gradual Type Checking (mypy strict)

**Status**: Accepted  
**Date**: 2025-10-09

### Context
Python supports optional type hints. How strict should we be?

### Decision
Use **mypy strict mode** for all code.

### Rationale

**For strict typing**:
- ✅ **Catch bugs**: Type errors caught before runtime
- ✅ **Documentation**: Types are documentation
- ✅ **IDE support**: Better autocomplete
- ✅ **Refactoring**: Safer refactoring
- ✅ **Modern**: Best practice for libraries

**Against no types**:
- ❌ Runtime errors harder to catch
- ❌ Worse developer experience

### Implementation

```python
# pyproject.toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true

# All code typed
def do_task(self, data: Dict[str, Any]) -> Optional[float]:
    ...
```

### Consequences
- Higher code quality
- Better developer experience
- More upfront work (typing)
- Easier maintenance

---

## Summary: Design Philosophy

### Core Principles

1. **Preserve Portability**
   - Keep task interface platform-agnostic
   - Use adapter pattern for platforms
   - Configuration externalized

2. **Modernize Tooling**
   - Type hints (mypy)
   - Modern ML (scikit-learn)
   - Cloud-native (Beam)
   - Standard observability (OpenTelemetry)

3. **Developer Experience**
   - Easy to add new benchmarks
   - Fast testing (standalone runner)
   - Good documentation
   - Clear error messages

4. **Performance**
   - Optimize hot paths
   - Use NumPy for math
   - Async I/O where beneficial
   - Profile and measure

5. **Compatibility**
   - Support Java properties
   - Same datasets
   - Comparable results
   - Migration path

---

**These decisions guide the implementation. Review before major changes!**

**Last Updated**: October 9, 2025  
**Status**: Approved for implementation

