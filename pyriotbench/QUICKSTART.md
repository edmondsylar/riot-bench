# Quick Start Guide - Using PyRIoTBench Core

This guide shows how to create and use benchmark tasks with the core abstractions we just built.

---

## 📦 Installation

```bash
cd pyriotbench
pip install -e ".[dev]"
```

---

## 🚀 Creating Your First Task

### Simple Task (Stateless)

```python
from pyriotbench import BaseTask, register_task

@register_task("double")
class DoubleTask(BaseTask):
    """Simple task that doubles the input."""
    
    def do_task(self, value: float) -> float:
        return value * 2
```

That's it! No timing code, no error handling - it's all automatic!

---

## 🎯 Using Tasks

### Basic Usage

```python
from pyriotbench import create_task

# Create task instance
task = create_task("double")

# Setup (called once)
task.setup()

# Execute (called per input)
result = task.execute(5.0)  # Returns 10.0

# Check timing and status
last_result = task.get_last_result()
print(last_result)  # [✓] 10.0 (0.03ms)

# Cleanup (called once)
task.tear_down()
```

### Check Available Tasks

```python
from pyriotbench import list_tasks

print(list_tasks())  # ['double', 'multiply', 'bloom-filter', ...]
```

---

## 🧠 Stateful Tasks

For tasks that need to remember previous values:

```python
from pyriotbench import StatefulTask, register_task

@register_task("moving-average")
class MovingAverageTask(StatefulTask):
    """Computes moving average over a window."""
    
    def setup(self):
        super().setup()
        self.window_size = 10
        self.set_state("values", [])
    
    def do_task(self, value: float) -> float:
        values = self.get_state("values", [])
        values.append(value)
        
        # Keep only last N values
        if len(values) > self.window_size:
            values.pop(0)
        
        self.set_state("values", values)
        return sum(values) / len(values)
```

Usage:

```python
task = create_task("moving-average")
task.setup()

# Process stream
for value in [1, 2, 3, 4, 5]:
    avg = task.execute(value)
    print(f"Value: {value}, Avg: {avg:.2f}")
```

---

## ⚙️ Task with Configuration

```python
from pyriotbench import BaseTask, register_task

@register_task("threshold")
class ThresholdTask(BaseTask):
    """Outputs 1 if input exceeds threshold, else 0."""
    
    def __init__(self, threshold: float = 100.0):
        super().__init__()
        self.threshold = threshold
    
    def do_task(self, value: float) -> int:
        return 1 if value > self.threshold else 0
```

Usage:

```python
from pyriotbench import create_task

# Create with custom threshold
task = create_task("threshold", threshold=50.0)
task.setup()

print(task.execute(30.0))  # 0
print(task.execute(60.0))  # 1
```

---

## 🔧 Task with Setup/Teardown

```python
from pyriotbench import BaseTask, register_task
import pickle

@register_task("ml-predictor")
class MLPredictorTask(BaseTask):
    """Loads ML model and makes predictions."""
    
    def setup(self):
        super().setup()
        # Load model once during setup
        with open("model.pkl", "rb") as f:
            self.model = pickle.load(f)
        self._logger.info("Model loaded successfully")
    
    def do_task(self, features: list) -> float:
        # Pure prediction logic
        return self.model.predict([features])[0]
    
    def tear_down(self):
        # Cleanup
        self.model = None
        super().tear_down()
```

---

## 🧪 Testing Tasks

Tasks are easy to test in isolation:

```python
import pytest
from my_tasks import DoubleTask

def test_double_task():
    task = DoubleTask()
    task.setup()
    
    # Test execution
    result = task.execute(5.0)
    assert result == 10.0
    
    # Test timing
    last = task.get_last_result()
    assert last.success is True
    assert last.execution_time_ms > 0
    
    # Test multiple executions
    task.execute(3.0)
    assert task.get_last_result().value == 6.0
    
    task.tear_down()

def test_double_task_with_error():
    task = DoubleTask()
    task.setup()
    
    # If task raises exception
    result = task.execute("not a number")  # Would raise TypeError
    
    # Error is caught automatically
    assert result == float('-inf')
    
    last = task.get_last_result()
    assert last.success is False
    assert "error" in last.error_message.lower()
```

---

## 🎨 Advanced: Custom Result Metadata

```python
from pyriotbench import BaseTask, TaskResult, register_task

@register_task("analyzer")
class AnalyzerTask(BaseTask):
    """Task that adds metadata to results."""
    
    def do_task(self, data: dict) -> float:
        score = sum(data.values())
        
        # Store metadata
        self._last_result = TaskResult(
            value=score,
            execution_time_ms=0,  # Will be overwritten
            success=True,
            metadata={
                "input_size": len(data),
                "max_value": max(data.values()),
                "algorithm": "sum-v2"
            }
        )
        
        return score
```

---

## 📊 Complete Example: Bloom Filter

```python
from pyriotbench import BaseTask, register_task
from typing import Set
import hashlib

@register_task("bloom-filter")
class BloomFilterTask(BaseTask):
    """Membership test using Bloom filter."""
    
    def __init__(self, size: int = 10000, num_hashes: int = 3):
        super().__init__()
        self.size = size
        self.num_hashes = num_hashes
        self.bit_array: Set[int] = set()
    
    def setup(self):
        super().setup()
        # Could load pre-trained filter here
        self._logger.info(f"Bloom filter initialized: size={self.size}")
    
    def _hash(self, item: str, seed: int) -> int:
        """Generate hash for item with seed."""
        h = hashlib.md5(f"{item}{seed}".encode())
        return int(h.hexdigest(), 16) % self.size
    
    def do_task(self, item: str) -> bool:
        """Check if item might be in set."""
        for i in range(self.num_hashes):
            if self._hash(item, i) not in self.bit_array:
                return False
        return True
    
    def add(self, item: str) -> None:
        """Add item to filter (training phase)."""
        for i in range(self.num_hashes):
            self.bit_array.add(self._hash(item, i))
    
    def tear_down(self):
        self._logger.info(f"Filter used {len(self.bit_array)} bits")
        super().tear_down()
```

Usage:

```python
# Create and train
bf = create_task("bloom-filter", size=1000, num_hashes=3)
bf.setup()

# Add items (training)
for word in ["apple", "banana", "cherry"]:
    bf.add(word)

# Test membership
print(bf.execute("apple"))   # True (definitely maybe in set)
print(bf.execute("grape"))   # False (definitely not in set)

# Check timing
print(bf.get_last_result())  # [✓] False (0.02ms)

bf.tear_down()
```

---

## 🎯 Key Takeaways

### What You Get for Free:
✅ **Automatic timing** - Every execution is timed (microsecond precision)  
✅ **Error handling** - Exceptions caught and logged, sentinel value returned  
✅ **Result tracking** - Last result always available via `get_last_result()`  
✅ **Logging** - Built-in logger per task class  
✅ **Type safety** - Full type hints with mypy support  
✅ **Testing** - Easy to test in isolation, no platform needed  

### What You Write:
- Just the `do_task()` method with your business logic
- Optionally: `setup()` and `tear_down()` for resources
- That's it! 🎉

### Benefits:
- **Platform-agnostic** - Same code runs on Beam, Flink, Ray, standalone
- **Clean code** - No timing instrumentation cluttering your logic
- **Composable** - Tasks can be chained in pipelines
- **Testable** - No external dependencies needed for testing
- **Discoverable** - Registry knows all tasks, can list and instantiate dynamically

---

## 📚 Next Steps

- Read `core/task.py` for full API documentation
- Read `core/registry.py` for registry details
- Look at `tests/test_core/` for more examples
- Check `CHECKPOINT-03.md` for architecture details

---

**Built with PyRIoTBench Core** ❤️  
*"Write once, run anywhere" - for real this time!*
