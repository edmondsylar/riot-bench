# 🔥 PHASE 2 BATTLE PLAN - Core Benchmarks Implementation

**Created**: October 11, 2025  
**Status**: READY TO STORM! 🚀  
**Goal**: Implement 5 core benchmarks (one per category) perfectly translated from Java

---

## 🎯 Mission Overview

We're implementing **5 representative benchmarks** - one from each major category:

1. ✅ **Parse**: SenML Parse (DONE in Phase 1!)
2. 🔥 **Filter**: Bloom Filter Check
3. 🔥 **Statistics**: Kalman Filter
4. 🔥 **Predictive**: Decision Tree Classify
5. 🔥 **Aggregate**: Block Window Average

---

## 📚 Java Implementation Analysis

### Core Patterns Discovered

#### **1. Thread-Safe Static Initialization**
```java
private static final Object SETUP_LOCK = new Object();
private static boolean doneSetup = false;
private static BloomFilter<String> bloomFilter;  // Shared across threads

public void setup(Logger l_, Properties p_) {
    super.setup(l_, p_);
    synchronized (SETUP_LOCK) {
        if(!doneSetup) {
            // Load model/config ONCE for all threads
            bloomFilter = loadModel();
            doneSetup = true;
        }
    }
}
```

**Python Translation**:
```python
class BloomFilterCheck(BaseTask):
    # Class variables (shared across instances)
    _bloom_filter: Optional[BloomFilter] = None
    _setup_lock = threading.Lock()
    _setup_done = False
    
    def setup(self) -> None:
        super().setup()
        with self._setup_lock:
            if not self._setup_done:
                # Load once
                self.__class__._bloom_filter = load_model()
                self.__class__._setup_done = True
```

#### **2. Instance State for Stateful Tasks**
```java
// Static config (shared)
private static float q_processNoise;
private static float r_sensorNoise;

// Instance state (per thread/instance)
private float p0_priorErrorCovariance;
private float x0_previousEstimation;
```

**Python Translation**:
```python
class KalmanFilter(StatefulTask):
    # Class vars (config)
    _q_process_noise: float = 0.1
    _r_sensor_noise: float = 0.1
    
    def setup(self) -> None:
        super().setup()
        # Instance state
        self.p0_prior_error_cov = 1.0
        self.x0_previous_est = 0.0
```

#### **3. Return Value Convention**
```java
protected Float doTaskLogic(Map map) {
    if (error) {
        return Float.MIN_VALUE;  // Error sentinel
    }
    if (no_output) {
        return null;  // No output
    }
    return result;  // Success with value
}
```

**Python Translation**:
```python
def do_task(self, data: Any) -> Optional[float]:
    if error:
        return float('-inf')  # Error sentinel
    if no_output:
        return None  # No output
    return result  # Success
```

#### **4. Complex Results via setLastResult()**
```java
String result = classify(data);
return Float.valueOf(classification_index);  // For flow control
// Store actual string result
super.setLastResult(result);
```

**Python Translation**:
```python
def do_task(self, data):
    result_string = classify(data)
    self._last_result = TaskResult(
        value=classification_index,
        metadata={"class_name": result_string}
    )
    return float(classification_index)
```

---

## 🎯 Benchmark #1: Bloom Filter Check

### **Java Implementation Analysis**

**File**: `filter/BloomFilterCheck.java` (100 lines)

**Key Features**:
1. Loads pre-trained Bloom filter from file (Guava library)
2. Checks membership for input strings
3. Returns 1.0 if present, 0.0 if not
4. Supports random testing (50% hit rate)

**Configuration**:
```properties
FILTER.BLOOM_FILTER.MODEL_PATH=/path/to/bloomfilter.model
FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD=0  # 0=random, >0=field index
FILTER.BLOOM_FILTER_TRAIN.EXPECTED_INSERTIONS=20000000
```

**Data Flow**:
```
Input → Extract field (or generate random) → bloomFilter.mightContain() → 1.0 or 0.0
```

**Dependencies**:
- Guava BloomFilter (`com.google.common.hash.BloomFilter`)
- Serialization support

### **Python Translation Plan**

**Library Choice**: `pybloom-live` or `bitarray` + manual implementation

**File Structure**:
```
pyriotbench/tasks/filter/
├── __init__.py
├── bloom_filter_check.py
└── bloom_filter_train.py  (Phase 4)
```

**Implementation**:
```python
from pybloom_live import BloomFilter
import pickle

@register_task("bloom_filter")
class BloomFilterCheck(BaseTask):
    """
    Bloom filter membership check.
    
    Loads pre-trained Bloom filter and checks if input values
    are likely members of the set. Uses probabilistic data structure
    for memory-efficient set membership testing.
    """
    
    # Class vars (shared state)
    _bloom_filter: Optional[BloomFilter] = None
    _use_msg_field: int = 0
    _testing_range: int = 20000000
    _setup_lock = threading.Lock()
    _setup_done = False
    
    def setup(self) -> None:
        super().setup()
        
        with self._setup_lock:
            if not self._setup_done:
                # Load config
                model_path = self.config.get('FILTER.BLOOM_FILTER.MODEL_PATH')
                self.__class__._use_msg_field = int(
                    self.config.get('FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD', 0)
                )
                
                # Load bloom filter
                with open(model_path, 'rb') as f:
                    self.__class__._bloom_filter = pickle.load(f)
                
                self._logger.info(f"Loaded bloom filter from {model_path}")
                self.__class__._setup_done = True
    
    def do_task(self, input_data: Any) -> float:
        """Check membership in bloom filter."""
        # Extract input
        if self._use_msg_field > 0:
            # Use specific field from CSV
            fields = input_data.split(',')
            test_value = fields[self._use_msg_field - 1]
        else:
            # Generate random value for testing
            import random
            test_value = str(random.randint(0, self._testing_range))
        
        # Check membership
        is_member = test_value in self._bloom_filter
        
        self._logger.debug(f"Bloom filter check: {test_value} -> {is_member}")
        
        return 1.0 if is_member else 0.0
```

**Tests to Write**:
```python
def test_bloom_filter_check_membership():
    """Test bloom filter with known members."""
    
def test_bloom_filter_check_non_membership():
    """Test bloom filter with non-members."""
    
def test_bloom_filter_check_field_extraction():
    """Test extraction from CSV fields."""
    
def test_bloom_filter_check_random_mode():
    """Test random value generation mode."""
```

---

## 🎯 Benchmark #2: Kalman Filter

### **Java Implementation Analysis**

**File**: `statistics/KalmanFilter.java` (120 lines)

**Key Features**:
1. **Stateful** - maintains estimation across invocations
2. 1D Kalman filter for sensor noise reduction
3. Time update + Measurement update steps
4. Per-instance state (previous estimation, error covariance)

**Algorithm**:
```
// Time Update (Prediction)
p1 = p0 + q_processNoise

// Measurement Update (Correction)
k = p1 / (p1 + r_sensorNoise)
x1 = x0 + k * (z_measured - x0)
p1 = (1 - k) * p1

// Update for next iteration
x0 = x1
p0 = p1
```

**Configuration**:
```properties
STATISTICS.KALMAN_FILTER.USE_MSG_FIELD=0
STATISTICS.KALMAN_FILTER.PROCESS_NOISE=0.1
STATISTICS.KALMAN_FILTER.SENSOR_NOISE=0.1
STATISTICS.KALMAN_FILTER.ESTIMATED_ERROR=1.0
```

### **Python Translation Plan**

**Library Choice**: Pure NumPy or `filterpy` (for advanced Kalman)

**Implementation**:
```python
import random

@register_task("kalman_filter")
class KalmanFilterTask(StatefulTask):
    """
    1D Kalman filter for sensor noise reduction.
    
    Applies Kalman filtering to reduce noise in sensor measurements.
    Maintains state across invocations for continuous estimation.
    
    Based on: "Kalman Filter For Dummies" by Bilgin Esme
    """
    
    # Class vars (config - shared)
    _use_msg_field: int = 0
    _q_process_noise: float = 0.1
    _r_sensor_noise: float = 0.1
    _setup_lock = threading.Lock()
    _setup_done = False
    
    def setup(self) -> None:
        super().setup()
        
        with self._setup_lock:
            if not self._setup_done:
                # Load config
                self.__class__._use_msg_field = int(
                    self.config.get('STATISTICS.KALMAN_FILTER.USE_MSG_FIELD', 0)
                )
                self.__class__._q_process_noise = float(
                    self.config.get('STATISTICS.KALMAN_FILTER.PROCESS_NOISE', 0.1)
                )
                self.__class__._r_sensor_noise = float(
                    self.config.get('STATISTICS.KALMAN_FILTER.SENSOR_NOISE', 0.1)
                )
                self.__class__._setup_done = True
        
        # Instance state (per task instance)
        self.p0_prior_error_cov = float(
            self.config.get('STATISTICS.KALMAN_FILTER.ESTIMATED_ERROR', 1.0)
        )
        self.x0_previous_est = 0.0
    
    def do_task(self, input_data: Any) -> float:
        """Apply Kalman filter to measurement."""
        
        # Extract measurement
        if self._use_msg_field > 0:
            z_measured = float(input_data.split(',')[self._use_msg_field - 1])
        elif self._use_msg_field == 0:
            z_measured = float(input_data)
        else:
            # Generate random value: 10 +/- 1.0
            z_measured = 10.0 + random.uniform(-1.0, 1.0)
        
        # Time Update (Prediction)
        p1_current_error_cov = self.p0_prior_error_cov + self._q_process_noise
        
        # Measurement Update (Correction)
        k_kalman_gain = p1_current_error_cov / (
            p1_current_error_cov + self._r_sensor_noise
        )
        x1_current_est = self.x0_previous_est + k_kalman_gain * (
            z_measured - self.x0_previous_est
        )
        p1_current_error_cov = (1 - k_kalman_gain) * p1_current_error_cov
        
        # Update state for next iteration
        self.x0_previous_est = x1_current_est
        self.p0_prior_error_cov = p1_current_error_cov
        
        self._logger.debug(
            f"Kalman: measured={z_measured:.3f}, "
            f"estimated={x1_current_est:.3f}, "
            f"error_cov={p1_current_error_cov:.6f}"
        )
        
        return x1_current_est
```

**Tests to Write**:
```python
def test_kalman_filter_reduces_noise():
    """Test that Kalman filter smooths noisy signal."""
    
def test_kalman_filter_state_persistence():
    """Test that state is maintained across calls."""
    
def test_kalman_filter_convergence():
    """Test that filter converges to true value."""
```

---

## 🎯 Benchmark #3: Decision Tree Classify

### **Java Implementation Analysis**

**File**: `predict/DecisionTreeClassify.java` (150 lines)

**Key Features**:
1. Loads Weka J48 decision tree model
2. Parses ARFF header for data structure
3. Classifies CSV input tuples
4. Returns class index + class name

**Weka Dependencies**:
- `weka.classifiers.trees.J48`
- `weka.core.Instance`
- `weka.core.Instances`

**Configuration**:
```properties
CLASSIFICATION.DECISION_TREE.USE_MSG_FIELD=0
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/model.model
CLASSIFICATION.DECISION_TREE.SAMPLE_HEADER=/path/to/header.arff
CLASSIFICATION.DECISION_TREE.CLASSIFY.RESULT_ATTRIBUTE_INDEX=5
```

**Data Flow**:
```
CSV → Parse → Create Instance → Classify → Return class index
```

### **Python Translation Plan**

**Library Choice**: `scikit-learn` (replaces Weka)

**Challenge**: Weka models → scikit-learn models
- **Solution**: Retrain models with scikit-learn OR convert Weka→sklearn

**Implementation**:
```python
from sklearn.tree import DecisionTreeClassifier
import joblib
import numpy as np

@register_task("decision_tree_classify")
class DecisionTreeClassifyTask(BaseTask):
    """
    Decision tree classification for IoT sensor data.
    
    Loads pre-trained scikit-learn decision tree model and
    classifies input CSV tuples into predefined classes.
    
    Example classes:
    - SYS dataset: Bad, Average, Good, VeryGood, Excellent
    - TAXI dataset: Bad, Good, VeryGood
    """
    
    # Class vars (shared)
    _model: Optional[DecisionTreeClassifier] = None
    _use_msg_field: int = 0
    _class_names: List[str] = []
    _feature_names: List[str] = []
    _sample_input: str = ""
    _setup_lock = threading.Lock()
    _setup_done = False
    
    def setup(self) -> None:
        super().setup()
        
        with self._setup_lock:
            if not self._setup_done:
                # Load config
                model_path = self.config.get('CLASSIFICATION.DECISION_TREE.MODEL_PATH')
                self.__class__._use_msg_field = int(
                    self.config.get('CLASSIFICATION.DECISION_TREE.USE_MSG_FIELD', 0)
                )
                
                # Load sklearn model (joblib format)
                self.__class__._model = joblib.load(model_path)
                
                # Load class names and feature names from config
                self.__class__._class_names = self.config.get(
                    'CLASSIFICATION.DECISION_TREE.CLASS_NAMES',
                    ['Bad', 'Average', 'Good', 'VeryGood', 'Excellent']
                )
                self.__class__._feature_names = self.config.get(
                    'CLASSIFICATION.DECISION_TREE.FEATURE_NAMES',
                    ['Temp', 'Humid', 'Light', 'Dust', 'AirQuality']
                )
                
                # Sample input for testing
                self.__class__._sample_input = self.config.get(
                    'CLASSIFICATION.DECISION_TREE.SAMPLE_INPUT',
                    '-71.10,42.37,10.1,65.3,0'
                )
                
                self._logger.info(f"Loaded decision tree with {len(self._class_names)} classes")
                self.__class__._setup_done = True
    
    def do_task(self, input_data: Any) -> float:
        """Classify input tuple using decision tree."""
        
        # Extract features
        if self._use_msg_field > 0:
            features_str = input_data.split(',')
        else:
            features_str = self._sample_input.split(',')
        
        # Convert to numpy array
        features = np.array([float(f) for f in features_str]).reshape(1, -1)
        
        # Classify
        class_index = self._model.predict(features)[0]
        class_name = self._class_names[int(class_index)]
        
        # Store result metadata
        self._last_result = TaskResult(
            value=float(class_index),
            metadata={
                'class_name': class_name,
                'class_index': int(class_index),
                'features': features.tolist()
            }
        )
        
        self._logger.debug(f"Classification: {features_str} → {class_name} (index={class_index})")
        
        return float(class_index)
```

**Model Training Script** (separate utility):
```python
# utils/train_decision_tree.py
def train_decision_tree_from_arff(arff_path, output_path):
    """Train sklearn DecisionTree from Weka ARFF file."""
    # Parse ARFF
    # Train sklearn model
    # Save with joblib
```

---

## 🎯 Benchmark #4: Block Window Average

### **Java Implementation Analysis**

**File**: `aggregate/BlockWindowAverage.java`

**Key Features**:
1. **Windowed aggregation** - accumulates values until window full
2. Emits average when window size reached
3. Resets window after emission
4. Stateful per sensor

**Configuration**:
```properties
AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE=10
AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD=1
```

### **Python Translation Plan**

**Implementation**:
```python
from collections import defaultdict
from typing import Dict, List

@register_task("block_window_average")
class BlockWindowAverageTask(StatefulTask):
    """
    Block window average aggregation.
    
    Accumulates values in fixed-size windows and emits
    average when window is full. Useful for reducing
    data volume while preserving trends.
    """
    
    # Class vars (config)
    _window_size: int = 10
    _use_msg_field: int = 1
    _setup_lock = threading.Lock()
    _setup_done = False
    
    def setup(self) -> None:
        super().setup()
        
        with self._setup_lock:
            if not self._setup_done:
                self.__class__._window_size = int(
                    self.config.get('AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE', 10)
                )
                self.__class__._use_msg_field = int(
                    self.config.get('AGGREGATE.BLOCK_WINDOW_AVERAGE.USE_MSG_FIELD', 1)
                )
                self.__class__._setup_done = True
        
        # Instance state - windows per sensor
        self.windows: Dict[str, List[float]] = defaultdict(list)
    
    def do_task(self, input_data: Any) -> Optional[float]:
        """Accumulate value and emit average when window full."""
        
        # Parse input: "sensor_id,value" or just "value"
        parts = input_data.split(',')
        
        if len(parts) >= 2:
            sensor_id = parts[0]
            value = float(parts[self._use_msg_field - 1])
        else:
            sensor_id = "default"
            value = float(parts[0])
        
        # Add to window
        self.windows[sensor_id].append(value)
        
        # Check if window is full
        if len(self.windows[sensor_id]) >= self._window_size:
            # Calculate average
            avg = sum(self.windows[sensor_id]) / len(self.windows[sensor_id])
            
            # Reset window
            self.windows[sensor_id].clear()
            
            self._logger.debug(
                f"Window full for {sensor_id}: emitting avg={avg:.3f}"
            )
            
            return avg
        else:
            # Window not full yet, no output
            return None
```

---

## 📋 Implementation Checklist

### **Benchmark #1: Bloom Filter** 🔥
- [ ] Create `pyriotbench/tasks/filter/__init__.py`
- [ ] Implement `bloom_filter_check.py`
- [ ] Install `pybloom-live` dependency
- [ ] Create test fixtures (sample bloom filter)
- [ ] Write 20+ unit tests
- [ ] Test with TAXI/SYS datasets
- [ ] Update task registry imports
- [ ] Document configuration options
- [ ] Create example usage

### **Benchmark #2: Kalman Filter** 🔥
- [ ] Create `pyriotbench/tasks/statistics/__init__.py`
- [ ] Implement `kalman_filter.py`
- [ ] Test state persistence
- [ ] Test noise reduction
- [ ] Write 15+ unit tests
- [ ] Validate against Java results
- [ ] Document algorithm
- [ ] Create example with noisy signal

### **Benchmark #3: Decision Tree** 🔥
- [ ] Create `pyriotbench/tasks/predict/__init__.py`
- [ ] Implement `decision_tree_classify.py`
- [ ] Train sklearn models (replace Weka)
- [ ] Create model conversion utility
- [ ] Write 20+ unit tests
- [ ] Test with SYS/TAXI datasets
- [ ] Document model format
- [ ] Create training script

### **Benchmark #4: Block Window Average** 🔥
- [ ] Create `pyriotbench/tasks/aggregate/__init__.py`
- [ ] Implement `block_window_average.py`
- [ ] Test windowing logic
- [ ] Test multi-sensor handling
- [ ] Write 15+ unit tests
- [ ] Test with streaming data
- [ ] Document windowing behavior

### **Integration** 🔥
- [ ] Update CLI imports (auto-register new tasks)
- [ ] Update `list-tasks` command
- [ ] Add example configs for each task
- [ ] Update README with new tasks
- [ ] Run full test suite (target: >90% coverage)
- [ ] Update progress tracking
- [ ] Create checkpoint document

---

## 🎯 Success Criteria

### **Functional**
- ✅ All 4 new tasks registered and discoverable
- ✅ Can run via CLI: `pyriotbench run <task> input.txt`
- ✅ Results match Java implementation (within tolerance)
- ✅ All tests passing (target: 80+ new tests)

### **Quality**
- ✅ >90% test coverage maintained
- ✅ 0 mypy errors (strict mode)
- ✅ All docstrings complete
- ✅ Performance within 30% of Java

### **Documentation**
- ✅ Each task has comprehensive docstring
- ✅ Configuration options documented
- ✅ Example usage for each task
- ✅ Checkpoint document created

---

## 🚀 Execution Order

### **Sprint 1: Filters (Days 1-2)**
1. Bloom Filter Check
2. Test bloom filter
3. Integration test

### **Sprint 2: Statistics (Days 3-4)**
1. Kalman Filter
2. Test kalman filter
3. Validate noise reduction

### **Sprint 3: Predictive (Days 5-7)**
1. Decision Tree Classify
2. Train sklearn models
3. Test classification
4. Model conversion utilities

### **Sprint 4: Aggregate (Day 8)**
1. Block Window Average
2. Test windowing
3. Integration tests

### **Sprint 5: Polish (Day 9-10)**
1. Full integration testing
2. Documentation
3. Examples
4. Checkpoint report

---

## 💡 Key Insights for Translation

### **1. Thread Safety → Class Variables**
Java's synchronized blocks → Python's class variables with locks

### **2. Stateful Tasks → StatefulTask Base Class**
Use our `StatefulTask` class for tasks with memory

### **3. Weka → scikit-learn**
Need model conversion or retraining

### **4. Guava → Python Equivalents**
- BloomFilter → `pybloom-live`
- Collections → built-in Python collections

### **5. Testing Strategy**
Match Java test files but use pytest conventions

---

## 📊 Progress Tracking

```
Phase 2 Progress: [░░░░░░░░░░] 0/4 tasks (0%)

Bloom Filter:      [ ] Not started
Kalman Filter:     [ ] Not started  
Decision Tree:     [ ] Not started
Block Window Avg:  [ ] Not started
```

---

**LET'S STORM FORWARD! 🔥🚀**

**Next Step**: Implement Bloom Filter Check task!
