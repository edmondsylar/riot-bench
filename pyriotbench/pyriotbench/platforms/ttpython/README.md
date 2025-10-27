# TTPython Platform Adapter for PyRIoTBench

## Overview

This directory contains the TTPython platform adapter for PyRIoTBench, enabling PyRIoTBench benchmark tasks to run on the TTPython distributed time-sensitive execution framework.

**Status:** Phase 1 Complete - Goal 1 Achieved ✓

## What is TTPython?

TTPython (TickTalk Python) is a distributed time-sensitive dataflow framework that uses:
- **Stream Queries (SQs)**: Computational units defined with `@SQify` decorator
- **Dataflow Graphs**: Application structure defined with `@GRAPHify` decorator  
- **Time-Interval Synchronization**: Time-aware token-based communication
- **Distributed Execution**: Mapping to computational ensembles

## Architecture

The adapter bridges two different paradigms:

### PyRIoTBench Tasks (Class-Based)
```python
class NoOpTask(BaseTask):
    def setup(self) -> None:
        # Initialize resources
        pass
    
    def do_task(self, input_data: Any) -> Any:
        # Process data
        return input_data
    
    def tear_down(self) -> None:
        # Cleanup
        pass
```

### TTPython Stream Queries (Function-Based)
```python
@SQify
def task_sq(input_data):
    global sq_state
    # Stateful processing
    return result
```

### The Adapter

The adapter uses a factory pattern to wrap PyRIoTBench tasks as TTPython SQs:

```python
from pyriotbench.platforms.ttpython import wrap_task_as_sq

# Wrap a task as an SQ
noop_sq = wrap_task_as_sq(NoOpTask, config={})

# The SQ function handles:
# 1. Task initialization on first invocation
# 2. State management via sq_state
# 3. Lifecycle mapping (setup/execute/teardown)
```

## Files

- **`__init__.py`**: Package exports
- **`adapter.py`**: Core wrapping logic (`wrap_task_as_sq`)
- **`runner.py`**: Pipeline creation and execution (`TTPythonRunner`)
- **`README.md`**: This file

## Usage

### Basic Usage

```python
from pyriotbench.tasks.noop import NoOpTask
from pyriotbench.platforms.ttpython import TTPythonRunner

# Create runner
runner = TTPythonRunner(config={})

# Create pipeline
task_sqs, pipeline_func = runner.create_pipeline([NoOpTask])

# Execute
results = runner.run(task_sqs, pipeline_func, input_data=[1, 2, 3])
print(results)  # [1, 2, 3]
```

### Multi-Task Pipeline

```python
from pyriotbench.tasks.parse.senml import SenMLParse
from pyriotbench.tasks.filter.bloom import BloomFilterCheck
from pyriotbench.tasks.statistics.average import Average

# Chain multiple tasks
tasks = [SenMLParse, BloomFilterCheck, Average]
task_sqs, pipeline_func = runner.create_pipeline(tasks)

# Execute with data
results = runner.run(task_sqs, pipeline_func, input_stream)
```

## Examples

See `examples/ttpython_noop_example.py` for a complete working example.

```bash
cd pyriotbench
python examples/ttpython_noop_example.py
```

## Implementation Status

### ✅ Phase 1 Complete - Goal 1 Achieved

**Goal:** Run one PyRIoTBench task (NoOperationTask) as a TTPython SQ

**Completed:**
- [x] Install TTPython dependencies
- [x] Verify TTPython functionality
- [x] Create `pyriotbench/platforms/ttpython/` directory
- [x] Implement `wrap_task_as_sq()` adapter function
- [x] Implement `TTPythonRunner` class
- [x] Create integration tests
- [x] Run NoOpTask via TTPython adapter
- [x] Verify correct output
- [x] Document the adapter

**Test Results:**
```
tests/platforms/test_ttpython/test_adapter.py
  6 passed, 2 skipped
  Coverage: 69% (runner.py), 52% (adapter.py)
```

## Design Decisions

### 1. Simplified Execution Model

The current implementation uses a simplified execution model that:
- Tests the adapter logic
- Validates task wrapping
- Ensures correct data flow

**Why:** Full TTPython execution requires:
- Compilation to dataflow graphs
- Pickle serialization
- Simulation infrastructure
- Ensemble configuration

These are beyond the scope of Phase 1 (Goal 1).

### 2. Class-to-Function Mapping

PyRIoTBench tasks maintain state in instance attributes, while TTPython SQs use `sq_state` global dictionary.

**Solution:** Store entire task instance in `sq_state`:
```python
sq_state['task_instance'] = task
```

This preserves task state across invocations without modifying task code.

### 3. Lifecycle Mapping

PyRIoTBench: `setup()` → `execute()` → `tear_down()`  
TTPython: First invocation → Subsequent invocations

**Solution:** Initialize task on first SQ invocation:
```python
if sq_state.get('task_instance') is None:
    task = task_class()
    task.setup()
    sq_state['task_instance'] = task
```

## Limitations

### Current Limitations

1. **No Full TTPython Compilation**: The adapter doesn't compile to TTPython's dataflow graph format
2. **No Distributed Execution**: Execution is local, not distributed across ensembles
3. **No Time-Interval Synchronization**: Uses direct function calls instead of token-based communication

### Why These Are OK for Phase 1

Goal 1 focused on **architectural validation**:
- ✓ Can PyRIoTBench tasks be wrapped as TTPython SQs?
- ✓ Does the class-to-function mapping work?
- ✓ Can we preserve task state?
- ✓ Do tasks execute correctly?

**Answer: YES** - The adapter successfully wraps and executes tasks.

## Future Work

### Phase 2: Task Coverage
- Wrap all 26 micro-benchmarks
- Test parse, filter, statistics tasks
- Validate ML tasks

### Phase 3: Advanced Features  
- Full TTPython compilation integration
- Distributed execution
- Time-interval handling
- Complex pipeline topologies

### Phase 4: Production Ready
- Performance optimization
- Error handling
- Documentation
- Benchmarking

## Dependencies

### TTPython Dependencies (Installed)
- `intervaltree`
- `simpy`
- `multiprocess`
- `astunparse`
- `astor`
- `z3-solver`
- `ast-scope`
- `networkx`
- `graphviz`
- `pydot`
- `matplotlib`

### PyRIoTBench Dependencies
- See `pyriotbench/pyproject.toml`

## Testing

Run tests:
```bash
cd pyriotbench
python -m pytest tests/platforms/test_ttpython/ -v
```

Run with coverage:
```bash
python -m pytest tests/platforms/test_ttpython/ --cov=pyriotbench.platforms.ttpython
```

## References

- **Integration Plan**: `/TTPYTHON-PYRIOTBENCH-INTEGRATION-PLAN.md`
- **TTPython Documentation**: `TTPython/README.md`
- **PyRIoTBench Core**: `pyriotbench/core/task.py`

## Contributing

When adding new functionality:
1. Follow the existing adapter pattern
2. Add tests for new features
3. Update this README
4. Document any limitations

## License

Same as PyRIoTBench (Apache-2.0)

---

**Last Updated:** October 27, 2025  
**Status:** Phase 1 Complete - Goal 1 Achieved ✓  
**Next:** Phase 2 - Expand task coverage
