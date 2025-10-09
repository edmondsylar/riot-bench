# PyRIoTBench: Architecture Deep Dive

**Companion to**: 00-PORTING-PLAN.md  
**Focus**: Technical architecture details and implementation patterns

---

## 🏗️ Part 1: Preserving Portability - The Key Patterns

### Pattern 1: Task Interface as Contract

The **ITask interface** is the foundation of portability. Let's analyze why it works:

```java
// Java: Platform-agnostic contract
public interface ITask<T,U> {
    void setup(Logger l_, Properties p_);      // Initialize
    Float doTask(Map<String, T> map);         // Process one element
    U getLastResult();                         // Retrieve complex result
    float tearDown();                          // Cleanup & metrics
}
```

#### Why This Design Works:

1. **No Platform Dependencies**: 
   - No imports from Storm/Flink/Beam
   - Uses only Java standard library (`Map`, `Properties`)
   - Framework-agnostic logging interface

2. **Single Responsibility**:
   - Task = pure computation
   - Platform adapter = I/O, distribution, fault tolerance
   - Clean separation enables independent testing

3. **Flexible Return Types**:
   ```java
   Float doTask(...)      // Simple status: 0.0=success, null=skip, -inf=error
   U getLastResult()      // Complex result: ML model, aggregated data, etc.
   ```

4. **Lifecycle Hooks**:
   ```
   setup() → [doTask() × N] → tearDown()
   ```
   - Matches all streaming platform lifecycles
   - Setup: Load models, initialize state
   - doTask: Per-event processing
   - tearDown: Emit metrics, close resources

#### Python Translation:

```python
from typing import Protocol, TypeVar, Dict, Optional, Any
import logging

T = TypeVar('T')  # Input type
U = TypeVar('U')  # Output type

class ITask(Protocol[T, U]):
    """
    Platform-agnostic task protocol.
    Matches Java ITask semantics exactly.
    """
    
    def setup(self, logger: logging.Logger, config: Dict[str, Any]) -> None:
        """
        One-time initialization.
        
        Args:
            logger: Python logging.Logger (replaces SLF4J)
            config: Dict instead of Properties (more Pythonic)
        """
        ...
    
    def do_task(self, data: Dict[str, T]) -> Optional[float]:
        """
        Process single element.
        
        Args:
            data: Dictionary with key "D" for default input
        
        Returns:
            float: Status (0.0+ = success, None = skip, -inf = error)
        """
        ...
    
    def get_last_result(self) -> Optional[U]:
        """Retrieve complex result from last do_task call"""
        ...
    
    def tear_down(self) -> float:
        """
        Cleanup and return metrics.
        
        Returns:
            float: Average execution time per call (seconds)
        """
        ...
```

**Key Translation Decisions**:
- `Properties` → `Dict[str, Any]`: More Pythonic, supports nested config
- `Logger` → `logging.Logger`: Standard library equivalent
- `Map<String, T>` → `Dict[str, T]`: Direct mapping
- Keep method names (`do_task` vs `doTask`): Python naming convention

---

### Pattern 2: Template Method in AbstractTask

The **AbstractTask** implements timing instrumentation transparently:

```java
// Java: Template method pattern
public abstract class AbstractTask<T, U> implements ITask<T, U> {
    protected Logger l;
    protected StopWatch sw;
    protected int counter;
    
    @Override
    public Float doTask(Map<String, T> map) {
        sw.resume();
        ////////////////////////
        Float result = doTaskLogic(map);  // Child implements this
        ////////////////////////
        sw.suspend();
        counter++;
        return result;
    }
    
    protected abstract Float doTaskLogic(Map<String, T> map);
    
    @Override
    public float tearDown() {
        sw.stop();
        return sw.getTime()/counter;  // Average time per call
    }
}
```

#### Why This Pattern is Brilliant:

1. **Zero Timing Overhead for Task Authors**:
   - Task implementer only writes business logic in `doTaskLogic()`
   - Timing happens automatically in `doTask()`
   - Consistent metrics across all 26 benchmarks

2. **Separation of Concerns**:
   - `AbstractTask`: Cross-cutting concerns (timing, logging, lifecycle)
   - Child task: Pure computation logic
   - No accidental coupling

3. **Template Method Benefits**:
   ```
   doTask() {           ← Fixed algorithm (AbstractTask)
       start_timer()
       doTaskLogic()    ← Varying part (child task)
       stop_timer()
   }
   ```

#### Python Translation:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
import time
import logging

@dataclass
class TaskMetrics:
    """Task execution metrics"""
    total_time: float = 0.0
    call_count: int = 0
    error_count: int = 0
    
    @property
    def avg_time(self) -> float:
        return self.total_time / self.call_count if self.call_count > 0 else 0.0


class BaseTask(ABC):
    """
    Abstract base with template method pattern.
    Implements ITask protocol.
    """
    
    DEFAULT_KEY = "D"
    
    def __init__(self):
        self.logger: Optional[logging.Logger] = None
        self.config: Dict[str, Any] = {}
        self._metrics = TaskMetrics()
        self._last_result: Optional[Any] = None
    
    def setup(self, logger: logging.Logger, config: Dict[str, Any]) -> None:
        """Setup with metric initialization"""
        self.logger = logger
        self.config = config
        self._metrics = TaskMetrics()
    
    def do_task(self, data: Dict[str, Any]) -> Optional[float]:
        """
        Template method with timing instrumentation.
        Child implements do_task_logic(), this handles timing.
        """
        start = time.perf_counter()
        try:
            result = self.do_task_logic(data)  # Call child implementation
            elapsed = time.perf_counter() - start
            self._metrics.total_time += elapsed
            self._metrics.call_count += 1
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            self._metrics.total_time += elapsed
            self._metrics.call_count += 1
            self._metrics.error_count += 1
            self.logger.error(f"Error in {self.__class__.__name__}: {e}")
            return float('-inf')  # Signal error
    
    @abstractmethod
    def do_task_logic(self, data: Dict[str, Any]) -> Optional[float]:
        """
        Child classes implement this.
        No timing code needed - handled by do_task().
        """
        pass
    
    def get_last_result(self) -> Optional[Any]:
        """Get complex result"""
        return self._last_result
    
    def _set_last_result(self, result: Any) -> Any:
        """Set complex result (for child classes)"""
        self._last_result = result
        return result
    
    def tear_down(self) -> float:
        """Return average execution time"""
        avg = self._metrics.avg_time
        self.logger.info(f"{self.__class__.__name__}: {self._metrics.call_count} calls, "
                        f"{avg:.6f}s avg, {self._metrics.error_count} errors")
        return avg
```

**Improvements Over Java**:
1. ✅ **Dataclass for Metrics**: Cleaner than scattered fields
2. ✅ **Property for avg_time**: More Pythonic than method
3. ✅ **Exception Handling**: Built into template (Java delegates to caller)
4. ✅ **Error Counter**: Track failures automatically

---

### Pattern 3: Adapter Pattern for Platform Integration

The **BaseTaskBolt** wraps tasks for Storm, demonstrating the adapter pattern:

```java
// Java: Storm Bolt adapter
public abstract class BaseTaskBolt extends BaseRichBolt {
    protected ITask task;
    protected Properties p;
    
    public BaseTaskBolt(Properties p_) {
        p = p_;
    }
    
    @Override
    public void prepare(Map map, TopologyContext topologyContext, 
                       OutputCollector outputCollector) {
        this.collector = outputCollector;
        task = getTaskInstance();  // Factory method
        task.setup(l, p);           // Initialize task
    }
    
    abstract protected ITask getTaskInstance();
    
    @Override
    public void execute(Tuple input) {
        // 1. Extract data from Storm tuple
        String rowString = input.getStringByField("RowString");
        String msgId = input.getStringByField("MSGID");
        
        // 2. Convert to task format (Map)
        HashMap<String, String> map = new HashMap<>();
        map.put(AbstractTask.DEFAULT_KEY, rowString);
        
        // 3. Invoke task (platform-agnostic call)
        Float res = task.doTask(map);
        
        // 4. Convert back to Storm format
        if(res != null && res != Float.MIN_VALUE) {
            collector.emit(new Values(rowString, msgId, res));
        }
    }
    
    @Override
    public void cleanup() {
        task.tearDown();
    }
}
```

#### Adapter Pattern Breakdown:

```
┌─────────────────────────────────────────────────┐
│  Storm Topology (Platform-Specific)             │
│  ┌────────────┐      ┌────────────┐            │
│  │   Spout    │─────▶│    Bolt    │            │
│  └────────────┘      └────────────┘            │
│                           ▲                      │
│                           │ BaseTaskBolt         │
└───────────────────────────┼──────────────────────┘
                            │ Adapter Layer
┌───────────────────────────┼──────────────────────┐
│  Task (Platform-Agnostic) │                      │
│  ┌─────────────────────────────────┐            │
│  │  ITask                           │            │
│  │  • setup()                       │            │
│  │  • doTask(Map) → Float           │            │
│  │  • tearDown()                    │            │
│  └─────────────────────────────────┘            │
└─────────────────────────────────────────────────┘
```

**Adapter Responsibilities**:
1. ✅ **Data Format Translation**: `Tuple` → `Map` → `Tuple`
2. ✅ **Lifecycle Mapping**: `prepare()` → `setup()`, `cleanup()` → `tearDown()`
3. ✅ **Error Handling**: Platform-specific error semantics
4. ✅ **Resource Management**: Collectors, context, etc.

#### Python Translation (Multiple Platforms):

```python
# ===== Apache Beam Adapter =====
import apache_beam as beam
from apache_beam.metrics import Metrics

class TaskDoFn(beam.DoFn):
    """Beam adapter for RIoTBench tasks"""
    
    def __init__(self, task_class: Type[ITask], config: Dict[str, Any]):
        self.task_class = task_class
        self.config = config
        self.task: Optional[ITask] = None
        
        # Beam-specific metrics
        self.counter = Metrics.counter(self.__class__, 'processed')
        self.latency = Metrics.distribution(self.__class__, 'latency_ms')
    
    def setup(self):
        """Beam lifecycle: initialize task"""
        logger = logging.getLogger('pyriotbench')
        self.task = self.task_class()
        self.task.setup(logger, self.config)
    
    def process(self, element: str):
        """Beam lifecycle: process element"""
        import time
        start = time.perf_counter()
        
        # Translate: Beam element → Task input
        data = {"D": element}
        result = self.task.do_task(data)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.latency.update(int(elapsed_ms))
        
        # Translate: Task result → Beam output
        if result is not None and result != float('-inf'):
            self.counter.inc()
            yield {
                'input': element,
                'result': result,
                'latency_ms': elapsed_ms
            }
    
    def teardown(self):
        """Beam lifecycle: cleanup"""
        if self.task:
            self.task.tear_down()


# ===== PyFlink Adapter =====
from pyflink.datastream import MapFunction

class TaskMapFunction(MapFunction):
    """PyFlink adapter for RIoTBench tasks"""
    
    def __init__(self, task_class: Type[ITask], config: Dict[str, Any]):
        self.task_class = task_class
        self.config = config
        self.task: Optional[ITask] = None
    
    def open(self, runtime_context):
        """Flink lifecycle: initialize"""
        logger = logging.getLogger('pyriotbench')
        self.task = self.task_class()
        self.task.setup(logger, self.config)
    
    def map(self, value: str) -> Optional[Dict[str, Any]]:
        """Flink lifecycle: process"""
        data = {"D": value}
        result = self.task.do_task(data)
        
        if result is not None and result != float('-inf'):
            return {'input': value, 'result': result}
        return None
    
    def close(self):
        """Flink lifecycle: cleanup"""
        if self.task:
            self.task.tear_down()


# ===== Ray Adapter =====
import ray

@ray.remote
class TaskActor:
    """Ray actor adapter for RIoTBench tasks"""
    
    def __init__(self, task_class: Type[ITask], config: Dict[str, Any]):
        logger = logging.getLogger('pyriotbench')
        self.task = task_class()
        self.task.setup(logger, config)
    
    def process(self, element: str) -> Optional[Dict[str, Any]]:
        """Process element"""
        data = {"D": element}
        result = self.task.do_task(data)
        
        if result is not None and result != float('-inf'):
            return {'input': element, 'result': result}
        return None
    
    def teardown(self) -> float:
        """Cleanup and return metrics"""
        return self.task.tear_down()


# ===== Standalone Adapter (for testing) =====
class StandaloneRunner:
    """Simple in-process runner"""
    
    def __init__(self, task_class: Type[ITask], config: Dict[str, Any]):
        logger = logging.getLogger('pyriotbench')
        self.task = task_class()
        self.task.setup(logger, config)
    
    def run(self, input_file: str, output_file: str):
        """Run task on file"""
        with open(input_file) as infile, open(output_file, 'w') as outfile:
            for line in infile:
                data = {"D": line.strip()}
                result = self.task.do_task(data)
                if result is not None and result != float('-inf'):
                    outfile.write(f"{line.strip()}\t{result}\n")
        
        avg_time = self.task.tear_down()
        print(f"Average time: {avg_time:.6f}s")
```

**Key Insight**: 
- Same task code (`ITask` implementation)
- Different adapters for Beam/Flink/Ray/Standalone
- Adapter handles platform-specific I/O, lifecycle, metrics
- Task remains 100% portable

---

## 🏗️ Part 2: State Management Patterns

### Pattern: Static Configuration vs Instance State

Java RIoTBench has a clever pattern for thread-safe state:

```java
public class BlockWindowAverage extends AbstractTask<String,Float> {
    // ===== Static: Shared configuration (immutable after setup) =====
    private static final Object SETUP_LOCK = new Object();
    private static boolean doneSetup = false;
    private static float aggCountWindowSize = 0;  // Config
    private static int useMsgField;               // Config
    
    // ===== Instance: Per-task computation state (mutable) =====
    private float aggCount;    // Current window count
    private float aggSum;      // Current window sum
    private float avgRes;      // Last average result
    
    public void setup(Logger l_, Properties p_) {
        super.setup(l_, p_);
        
        // One-time static initialization (synchronized)
        synchronized (SETUP_LOCK) {
            if(!doneSetup) {
                aggCountWindowSize = Integer.parseInt(
                    p_.getProperty("AGGREGATE.BLOCK_COUNT.WINDOW_SIZE")
                );
                useMsgField = Integer.parseInt(
                    p_.getProperty("AGGREGATE.BLOCK_COUNT.USE_MSG_FIELD")
                );
                doneSetup = true;
            }
        }
        
        // Per-instance initialization
        aggCount = 0;
        aggSum = 0;
        avgRes = 0;
    }
    
    @Override
    protected Float doTaskLogic(Map<String,String> map) {
        String m = map.get(AbstractTask.DEFAULT_KEY);
        String[] fields = m.split(",");
        float value = Float.parseFloat(fields[useMsgField]);
        
        // Update instance state
        aggSum += value;
        aggCount++;
        
        // Window complete?
        if(aggCount >= aggCountWindowSize) {
            avgRes = aggSum / aggCount;
            aggCount = 0;  // Reset window
            aggSum = 0;
            return setLastResult(avgRes);
        }
        return null;  // Window not complete
    }
}
```

#### Why This Pattern?

1. **Configuration Immutable After Setup**:
   - Read from properties once
   - Store in static fields
   - All instances share same config
   - No repeated parsing overhead

2. **State Local to Each Instance**:
   - Each task maintains own window (`aggCount`, `aggSum`)
   - No shared mutable state between instances
   - Naturally thread-safe for computation

3. **Synchronized Setup**:
   - Ensures config loaded exactly once
   - Safe even if multiple threads create instances
   - `doneSetup` flag prevents re-initialization

#### Python Translation:

```python
from dataclasses import dataclass, field
from typing import ClassVar, Dict, Any, Optional
import threading

@dataclass
class BlockWindowAverageConfig:
    """Configuration (class-level, immutable)"""
    window_size: int = 100
    use_field: int = 5

class BlockWindowAverage(BaseTask[str, float]):
    """
    Compute moving average over block window.
    
    State Management:
    - Config: Class variable (shared, immutable)
    - Computation: Instance variables (per-task, mutable)
    """
    
    # ===== Class-level (static in Java) =====
    _config: ClassVar[Optional[BlockWindowAverageConfig]] = None
    _config_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def __init__(self):
        super().__init__()
        # ===== Instance-level computation state =====
        self.window_sum: float = 0.0
        self.window_count: int = 0
        self.last_avg: float = 0.0
    
    def setup(self, logger: logging.Logger, config: Dict[str, Any]) -> None:
        """Setup with thread-safe config initialization"""
        super().setup(logger, config)
        
        # One-time class-level setup (thread-safe)
        with self._config_lock:
            if not self._setup_done:
                self.__class__._config = BlockWindowAverageConfig(
                    window_size=int(config.get('AGGREGATE.BLOCK_COUNT.WINDOW_SIZE', 100)),
                    use_field=int(config.get('AGGREGATE.BLOCK_COUNT.USE_MSG_FIELD', 5))
                )
                self.__class__._setup_done = True
        
        # Instance-level setup
        self.window_sum = 0.0
        self.window_count = 0
        self.last_avg = 0.0
    
    def do_task_logic(self, data: Dict[str, str]) -> Optional[float]:
        """Compute windowed average"""
        input_str = data.get(self.DEFAULT_KEY, "")
        fields = input_str.split(',')
        
        # Access class-level config (immutable, no lock needed)
        value = float(fields[self._config.use_field])
        
        # Update instance-level state (mutable, but instance-local)
        self.window_sum += value
        self.window_count += 1
        
        # Window complete?
        if self.window_count >= self._config.window_size:
            self.last_avg = self.window_sum / self.window_count
            # Reset window
            self.window_count = 0
            self.window_sum = 0.0
            # Return result
            return self._set_last_result(self.last_avg)
        
        return None  # Window incomplete
```

**Alternative: Using attrs for Cleaner Config**:

```python
import attrs
from typing import ClassVar

@attrs.define
class BlockWindowAverage(BaseTask[str, float]):
    # Class-level config (shared)
    _config: ClassVar[Optional[Dict]] = None
    _config_lock: ClassVar[threading.Lock] = threading.Lock()
    
    # Instance-level state (per-task)
    window_sum: float = attrs.field(default=0.0, init=False)
    window_count: int = attrs.field(default=0, init=False)
    last_avg: float = attrs.field(default=0.0, init=False)
    
    # ... rest same as above
```

---

### Pattern: Stateful Aggregation (Accumulator)

The **AccumulatorTask** shows complex stateful computation:

```java
public class AccumlatorTask extends AbstractTask<String, Map<String, Map<String, Queue<TimestampValue>>>> {
    // Configuration (static)
    private static int tupleWindowSize;
    private static ArrayList<String> multiValueObsType;
    
    // State (instance)
    private Map<String, Map<String, Queue<TimestampValue>>> valuesMap;
    private int counter;
    
    @Override
    public Float doTaskLogic(Map<String, String> map) {
        String sensorId = map.get("SENSORID");
        String meta = map.get("META");
        String obsVal = map.get("OBSVALUE");
        String obsType = map.get("OBSTYPE");
        
        // Build nested key: sensorId + obsType
        String key = sensorId + obsType;
        
        // Get or create nested map
        Map<String, Queue<TimestampValue>> innerMap = valuesMap.get(key);
        if (innerMap == null) {
            innerMap = new HashMap<>();
            Queue<TimestampValue> queue = new PriorityQueue<>();
            innerMap.put(meta, queue);
            valuesMap.put(key, innerMap);
        }
        
        // Add value to queue
        Queue<TimestampValue> queue = innerMap.get(meta);
        queue.add(new TimestampValue(obsVal, meta));
        
        // Increment counter
        counter++;
        
        // Window complete?
        if (counter == tupleWindowSize) {
            setLastResult(valuesMap);  // Complex result
            valuesMap = new HashMap<>();  // Reset state
            counter = 0;
            return 1.0f;  // Signal output ready
        }
        
        return 0.0f;  // Accumulating
    }
}
```

#### Python Translation with Type Safety:

```python
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Dict, Optional
import threading

@dataclass(order=True)
class TimestampValue:
    """Value with timestamp for priority queue"""
    timestamp: str
    value: str = field(compare=False)

class AccumulatorTask(BaseTask[str, Dict[str, Dict[str, PriorityQueue]]]):
    """
    Accumulate values in windowed batches.
    
    State: Nested dictionary of priority queues
    Output: Complete accumulated batch when window full
    """
    
    # Class-level config
    _config_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    _window_size: ClassVar[int] = 0
    _multi_value_types: ClassVar[list] = []
    
    def __init__(self):
        super().__init__()
        # Instance state: nested map of queues
        self.values_map: Dict[str, Dict[str, PriorityQueue]] = {}
        self.counter: int = 0
    
    def setup(self, logger: logging.Logger, config: Dict[str, Any]) -> None:
        super().setup(logger, config)
        
        # One-time config initialization
        with self._config_lock:
            if not self._setup_done:
                self.__class__._window_size = int(
                    config.get('AGGREGATE.ACCUMLATOR.TUPLE_WINDOW_SIZE', 100)
                )
                multi_val_str = config.get('AGGREGATE.ACCUMLATOR.MULTIVALUE_OBSTYPE', '')
                self.__class__._multi_value_types = multi_val_str.split(',') if multi_val_str else []
                self.__class__._setup_done = True
        
        # Instance initialization
        self.values_map = {}
        self.counter = 0
    
    def do_task_logic(self, data: Dict[str, str]) -> Optional[float]:
        """Accumulate values in window"""
        sensor_id = data.get("SENSORID", "")
        meta = data.get("META", "")
        obs_value = data.get("OBSVALUE", "")
        obs_type = data.get("OBSTYPE", "")
        timestamp = data.get("TS", "")
        
        # Build composite key
        key = f"{sensor_id}{obs_type}"
        
        # Get or create nested structure
        if key not in self.values_map:
            self.values_map[key] = {}
        
        inner_map = self.values_map[key]
        if meta not in inner_map:
            inner_map[meta] = PriorityQueue()
        
        queue = inner_map[meta]
        
        # Handle multi-value observations
        if obs_type in self._multi_value_types:
            for value in obs_value.split('#'):
                queue.put(TimestampValue(timestamp, value))
        else:
            queue.put(TimestampValue(timestamp, obs_value))
        
        # Increment window counter
        self.counter += 1
        
        # Window complete?
        if self.counter >= self._window_size:
            # Set complex result
            self._set_last_result(self.values_map)
            # Reset state
            self.values_map = {}
            self.counter = 0
            return 1.0  # Signal: output ready
        
        return 0.0  # Still accumulating
```

**Key Points**:
1. ✅ **Nested State**: `Dict[str, Dict[str, PriorityQueue]]` 
2. ✅ **Window Logic**: Counter triggers output
3. ✅ **Complex Result**: `get_last_result()` returns full accumulated batch
4. ✅ **State Reset**: After window emits, reset to empty

---

## 🏗️ Part 3: Configuration Architecture

### Pattern: Hierarchical Namespace

Java properties use dot-separated namespaces:

```properties
# tasks.properties
PARSE.SENML_ENABLED=TRUE
PARSE.CSV_DELIMITER=,

FILTER.BLOOM_FILTER.MODEL_PATH=/path/to/model
FILTER.BLOOM_FILTER.EXPECTED_INSERTIONS=1000000
FILTER.RANGE.MIN_VALUE=0.0
FILTER.RANGE.MAX_VALUE=100.0

AGGREGATE.BLOCK_COUNT.WINDOW_SIZE=100
AGGREGATE.BLOCK_COUNT.USE_MSG_FIELD=5

CLASSIFICATION.DTC.MODEL_PATH=/models/decision_tree.model
CLASSIFICATION.DTC.TRAIN_FREQUENCY=1000

AZURE.ACCOUNT_NAME=myaccount
AZURE.CONTAINER_NAME=mybenchmarks

MQTT.BROKER=mqtt.eclipse.org
MQTT.PORT=1883
```

#### Python Improvement: YAML + Pydantic

```python
# config.py - Type-safe configuration with validation
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
import yaml
from pathlib import Path

class ParseConfig(BaseModel):
    """Parse task configuration"""
    senml_enabled: bool = Field(default=True, description="Enable SenML parsing")
    csv_delimiter: str = Field(default=',', description="CSV delimiter character")

class FilterConfig(BaseModel):
    """Filter task configuration"""
    bloom_filter_model_path: Optional[Path] = None
    bloom_expected_insertions: int = 1_000_000
    range_min_value: float = 0.0
    range_max_value: float = 100.0
    
    @validator('bloom_filter_model_path')
    def check_model_exists(cls, v):
        if v is not None and not v.exists():
            raise ValueError(f"Model file not found: {v}")
        return v

class AggregateConfig(BaseModel):
    """Aggregate task configuration"""
    block_window_size: int = Field(default=100, gt=0)
    use_field_index: int = Field(default=5, ge=0)
    accumulator_window_size: int = 100

class ClassificationConfig(BaseModel):
    """ML classification configuration"""
    decision_tree_model_path: Optional[Path] = None
    train_frequency: int = Field(default=1000, gt=0)
    model_type: str = Field(default='sklearn', regex='^(sklearn|pytorch)$')

class AzureConfig(BaseModel):
    """Azure storage configuration"""
    account_name: str
    account_key: str
    container_name: str = 'riotbench'
    
    class Config:
        # Load from environment variables
        env_prefix = 'AZURE_'

class MQTTConfig(BaseModel):
    """MQTT broker configuration"""
    broker: str = 'localhost'
    port: int = Field(default=1883, ge=1, le=65535)
    topic: str = 'riotbench/data'
    qos: int = Field(default=1, ge=0, le=2)

class PyRIoTBenchConfig(BaseModel):
    """Root configuration"""
    parse: ParseConfig = ParseConfig()
    filter: FilterConfig = FilterConfig()
    aggregate: AggregateConfig = AggregateConfig()
    classification: ClassificationConfig = ClassificationConfig()
    azure: Optional[AzureConfig] = None
    mqtt: MQTTConfig = MQTTConfig()
    
    # Custom task-specific properties
    custom: Dict[str, Any] = {}
    
    @classmethod
    def from_yaml(cls, path: str) -> 'PyRIoTBenchConfig':
        """Load from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_properties(cls, path: str) -> 'PyRIoTBenchConfig':
        """Load from Java .properties file (backward compat)"""
        # Parse properties file into nested dict
        config_dict = {}
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Convert AGGREGATE.BLOCK_COUNT.WINDOW_SIZE to nested dict
                    parts = key.strip().lower().split('.')
                    current = config_dict
                    for part in parts[:-1]:
                        current = current.setdefault(part, {})
                    current[parts[-1]] = value.strip()
        
        # Map to Pydantic model
        return cls(**config_dict)
    
    def to_flat_dict(self) -> Dict[str, Any]:
        """
        Convert to flat dictionary for task.setup().
        Maintains Java property naming for backward compat.
        """
        return {
            'PARSE.SENML_ENABLED': self.parse.senml_enabled,
            'FILTER.BLOOM_FILTER.MODEL_PATH': str(self.filter.bloom_filter_model_path) if self.filter.bloom_filter_model_path else None,
            'AGGREGATE.BLOCK_COUNT.WINDOW_SIZE': self.aggregate.block_window_size,
            'CLASSIFICATION.DTC.MODEL_PATH': str(self.classification.decision_tree_model_path) if self.classification.decision_tree_model_path else None,
            # ... all mappings
            **self.custom
        }

# Example YAML configuration
"""
# config.yaml
parse:
  senml_enabled: true
  csv_delimiter: ","

filter:
  bloom_filter_model_path: /path/to/model
  bloom_expected_insertions: 1000000
  range_min_value: 0.0
  range_max_value: 100.0

aggregate:
  block_window_size: 100
  use_field_index: 5

classification:
  decision_tree_model_path: /models/dtc.pkl
  train_frequency: 1000
  model_type: sklearn

azure:
  account_name: ${AZURE_ACCOUNT_NAME}  # From environment
  account_key: ${AZURE_ACCOUNT_KEY}
  container_name: riotbench

mqtt:
  broker: mqtt.eclipse.org
  port: 1883
  topic: riotbench/sensors
  qos: 1
"""

# Usage
config = PyRIoTBenchConfig.from_yaml('config.yaml')
task.setup(logger, config.to_flat_dict())
```

**Benefits**:
1. ✅ **Type Safety**: Pydantic validates types at runtime
2. ✅ **Documentation**: Field descriptions built-in
3. ✅ **Validation**: Custom validators (e.g., file exists, range checks)
4. ✅ **Environment Variables**: Automatic loading from env
5. ✅ **Backward Compat**: Can load Java `.properties` files
6. ✅ **IDE Support**: Autocomplete for all config fields

---

## 🎯 Summary: What to Preserve vs Improve

| Aspect | Java Implementation | Preserve? | Python Improvement |
|--------|-------------------|-----------|-------------------|
| **Task Interface** | `ITask<T,U>` | ✅ Yes | Protocol with type hints |
| **Template Method** | `AbstractTask` | ✅ Yes | Dataclasses for metrics |
| **Adapter Pattern** | `BaseTaskBolt` | ✅ Yes | Multiple adapters (Beam/Flink/Ray) |
| **State Management** | Static + instance vars | ✅ Yes | ClassVar + attrs/dataclasses |
| **Configuration** | `.properties` file | ✅ Structure | YAML + Pydantic validation |
| **Registry** | Manual factory | ⚠️ Improve | Decorator-based registration |
| **Metrics** | Basic timing | ⚠️ Improve | OpenTelemetry integration |
| **ML Libraries** | Weka (Java-only) | ❌ Replace | scikit-learn/PyTorch |
| **Async I/O** | Synchronous only | ❌ Add | AsyncIO support |
| **Type Safety** | Java generics | ⚠️ Improve | Mypy strict mode |

**Core Principle**: Preserve the brilliant **portability architecture**, modernize the **tooling and libraries**.

