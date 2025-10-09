# Architecture & Design

## Overview

RIoTBench follows a **modular, layered architecture** that separates platform-agnostic benchmark logic from platform-specific execution infrastructure. This design enables:

1. **Portability**: Tasks can be adapted to different stream processing platforms
2. **Reusability**: Micro-benchmarks can be composed into various dataflows
3. **Testability**: Tasks can be tested independently
4. **Extensibility**: New benchmarks can be added easily

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│              Application Layer                          │
│  (ETL, STATS, TRAIN, PRED Topologies)                  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           Storm Integration Layer                       │
│  (Spouts, Bolts, Topology Builders)                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          Task Abstraction Layer                         │
│  (ITask Interface, AbstractTask)                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         Benchmark Implementation Layer                  │
│  (26 Micro-benchmark Tasks)                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           External Dependencies                         │
│  (Weka, Azure SDK, MQTT, Commons Math, etc.)           │
└─────────────────────────────────────────────────────────┘
```

---

## Core Design Patterns

### 1. Task Interface Pattern

All benchmarks implement a common interface for consistent execution:

```java
public interface ITask<T, U> {
    // Initialize task with configuration
    void setup(Logger logger, Properties properties);
    
    // Execute task logic on input
    Float doTask(Map<String, T> input);
    
    // Get additional results beyond Float return value
    U getLastResult();
    
    // Cleanup and return average execution time
    float tearDown();
}
```

### 2. Template Method Pattern

`AbstractTask` provides common functionality:

```java
public abstract class AbstractTask<T, U> implements ITask<T, U> {
    protected Logger l;
    protected StopWatch sw;      // For timing measurements
    protected int counter;        // Number of invocations
    private U lastResult;         // For complex return values
    
    @Override
    public final Float doTask(Map<String, T> map) {
        sw.resume();              // Start timer
        Float result = doTaskLogic(map);  // Call child implementation
        sw.suspend();             // Stop timer
        counter++;
        return result;
    }
    
    // Child classes implement this
    protected abstract Float doTaskLogic(Map<String, T> map);
    
    @Override
    public float tearDown() {
        sw.stop();
        return sw.getTime() / counter;  // Average execution time
    }
}
```

**Benefits**:
- Automatic timing instrumentation
- Consistent lifecycle management
- Separation of concerns

### 3. Adapter Pattern

Storm Bolts wrap tasks to bridge Storm's tuple model with task's map model:

```java
public class DecisionTreeClassifyBolt extends BaseRichBolt {
    private DecisionTreeClassify task;
    private Properties properties;
    private OutputCollector collector;
    
    @Override
    public void prepare(Map conf, TopologyContext context, 
                       OutputCollector collector) {
        this.collector = collector;
        // Initialize task
        task = new DecisionTreeClassify();
        task.setup(logger, properties);
    }
    
    @Override
    public void execute(Tuple tuple) {
        // Convert Storm tuple to task input
        Map<String, String> taskInput = new HashMap<>();
        taskInput.put("msgId", tuple.getStringByField("MSGID"));
        taskInput.put("data", tuple.getStringByField("DATA"));
        
        // Execute task
        Float result = task.doTask(taskInput);
        
        // Convert result to Storm tuple
        if (result != null && result != Float.MIN_VALUE) {
            collector.emit(new Values(
                tuple.getStringByField("MSGID"),
                result,
                task.getLastResult()
            ));
        }
        
        collector.ack(tuple);
    }
    
    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        declarer.declare(new Fields("MSGID", "RESULT", "CLASS"));
    }
}
```

---

## Module Structure

### Module: `iot-bm-tasks`

**Location**: `modules/tasks/`

**Purpose**: Platform-agnostic benchmark implementations

**Package Structure**:
```
in.dream_lab.bm.stream_iot.tasks/
├── ITask.java              # Task interface
├── AbstractTask.java       # Base implementation
├── Defaults.java           # Default constants
├── Utils.java              # Utility functions
├── aggregate/              # Statistical aggregations
│   └── DistinctApproxCount.java
├── annotate/               # Data annotation
│   ├── Annotate.java
│   └── AnnotateDTClass.java
├── filter/                 # Filtering operations
│   ├── BloomFilterCheck.java
│   ├── BloomFilterTrain.java
│   ├── MultipleBloomFilterCheck.java
│   └── RangeFilterCheck.java
├── io/                     # I/O operations
│   ├── AzureBlobDownloadTask.java
│   ├── AzureBlobUploadTask.java
│   ├── AzureTableInsert.java
│   ├── AzureTableRangeQueryTask*.java
│   ├── MQTTPublishTask.java
│   └── MQTTSubscribeTask.java
├── parse/                  # Data parsing
│   ├── SenMLParse.java
│   ├── XMLParse.java
│   └── CsvToSenMLParse.java
├── predict/                # Machine learning
│   ├── DecisionTreeClassify.java
│   ├── DecisionTreeTrain.java
│   ├── LinearRegressionPredictor.java
│   └── LinearRegressionTrain.java
├── statistics/             # Statistical operations
│   ├── KalmanFilter.java
│   ├── Interpolation.java
│   └── SecondOrderMoment.java
├── utils/                  # Helper classes
│   └── TimestampValue.java
└── visualize/              # Visualization
    └── XChartMultiLinePlotTask.java
```

**Dependencies**:
- Apache Commons Math (statistics)
- Weka (machine learning)
- Azure SDK (cloud I/O)
- Eclipse Paho (MQTT)
- Google Guava (Bloom filters)
- XChart (visualization)

---

### Module: `iot-bm-storm`

**Location**: `modules/storm/`

**Purpose**: Apache Storm integration

**Package Structure**:
```
in.dream_lab.bm.stream_iot.storm/
├── bolts/                      # Storm bolts
│   ├── ETL/                    # ETL application bolts
│   │   └── TAXI/               # Dataset-specific
│   ├── IoTStatsBolt/           # STATS application
│   ├── IoTPredictionBolts/     # PRED application
│   │   ├── TAXI/
│   │   ├── SYS/
│   │   └── FIT/
│   └── TRAIN/                  # TRAIN application
│       ├── TAXI/
│       ├── SYS/
│       └── FIT/
├── spouts/                     # Data sources
│   ├── SampleSpout.java        # Basic spout
│   ├── SampleSenMLSpout.java   # SenML format
│   ├── MQTTSubscribeSpout.java # MQTT ingestion
│   └── SampleSpoutTimerForTrain.java  # Timer-based
├── sinks/                      # Data sinks
│   └── Sink.java               # Logging sink
├── topo/                       # Topology definitions
│   ├── apps/                   # Application topologies
│   │   ├── ETLTopology.java
│   │   ├── IoTStatsTopology.java
│   │   ├── IoTPredictionTopology*.java
│   │   └── IoTTrainTopology*.java
│   └── micro/                  # Micro-benchmark topologies
│       ├── MicroTopologyDriver.java
│       ├── MicroTopologyFactory.java
│       └── MQTTSubscriberTopology.java
└── genevents/                  # Event generation
    └── factory/
        ├── ArgumentClass.java
        └── ArgumentParser.java
```

**Dependencies**:
- Apache Storm 1.0.1
- iot-bm-tasks module
- OpenCSV (data parsing)

---

### Module: `iot-bm-distribution`

**Location**: `modules/distribution/`

**Purpose**: Packaging and assembly

**Contains**:
- Maven assembly descriptors
- Build scripts for creating distributable JAR files

---

## Task Lifecycle

### 1. Initialization Phase

```
Topology Submission
        ↓
Bolt.prepare() called by Storm
        ↓
Load properties from file
        ↓
Create task instance
        ↓
task.setup(logger, properties)
        ↓
Task initializes resources:
  - Load ML models
  - Open connections
  - Initialize state
```

### 2. Execution Phase

```
Storm receives tuple
        ↓
Bolt.execute(tuple) called
        ↓
Convert tuple to Map<String, T>
        ↓
task.doTask(map)
        ↓
AbstractTask.doTask():
  - Resume timer
  - Call doTaskLogic()
  - Suspend timer
  - Increment counter
        ↓
Bolt converts result to output tuple
        ↓
collector.emit(outputTuple)
        ↓
collector.ack(inputTuple)
```

### 3. Termination Phase

```
Topology killed or worker shutdown
        ↓
Bolt.cleanup() called
        ↓
task.tearDown()
        ↓
AbstractTask.tearDown():
  - Stop timer
  - Calculate average time
  - Return metrics
        ↓
Close resources
```

---

## Data Flow Architecture

### Input Data Format

Tasks receive input as `Map<String, T>` where keys are field names:

```java
Map<String, String> input = {
    "msgId": "sensor_123",
    "timestamp": "1234567890",
    "sensorID": "temp_sensor_01",
    "obsType": "temperature",
    "data": "25.5,60.2,1200,150,25",
    "meta": "lat:12.34,lon:56.78"
}
```

### Output Data Format

Tasks return:
1. **Float**: Primary result (execution status or simple metric)
   - `Float.MIN_VALUE`: Error occurred
   - `null`: No output (filtered)
   - Other values: Valid result
   
2. **Generic Type U**: Complex results via `getLastResult()`
   - Parsed objects
   - Predictions
   - Serialized models

### Storm Tuple Schema

Each bolt defines its output schema:

```java
@Override
public void declareOutputFields(OutputFieldsDeclarer declarer) {
    declarer.declare(new Fields(
        "MSGID",        // Message identifier
        "TIMESTAMP",    // Event timestamp
        "SENSORID",     // Sensor identifier
        "OBSTYPE",      // Observation type
        "DATA",         // Payload
        "METADATA"      // Additional info
    ));
}
```

---

## State Management

### Stateless Tasks

Tasks like parsing, filtering, and prediction are stateless:

```java
public class RangeFilterCheck extends AbstractTask<String, String> {
    @Override
    protected Float doTaskLogic(Map<String, String> map) {
        String value = map.get("data");
        double numValue = Double.parseDouble(value);
        
        // No state maintained between invocations
        if (numValue < minRange || numValue > maxRange) {
            return Float.MIN_VALUE;  // Filtered
        }
        return (float) numValue;
    }
}
```

### Stateful Tasks

Tasks like Kalman filter maintain state per sensor:

```java
public class KalmanFilter extends AbstractTask {
    // State maintained across events
    private Map<String, KalmanState> sensorStates = new HashMap<>();
    
    @Override
    protected Float doTaskLogic(Map<String, String> map) {
        String sensorId = map.get("sensorID");
        
        // Get or create state for this sensor
        KalmanState state = sensorStates.computeIfAbsent(
            sensorId, k -> new KalmanState()
        );
        
        // Update state based on new measurement
        double measurement = Double.parseDouble(map.get("value"));
        state.predict();
        state.update(measurement);
        
        return (float) state.getEstimate();
    }
}
```

### Storm Fields Grouping

Stateful operations use fields grouping to ensure all events for the same key go to the same bolt instance:

```java
builder.setBolt("KalmanFilterBolt", new KalmanFilterBolt(props), 3)
    .fieldsGrouping("upstream", new Fields("sensorID", "obsType"));
```

This guarantees that all data for `sensor_A` always goes to the same instance (0, 1, or 2).

---

## Configuration Management

### Properties File Structure

```properties
# Category.Operation.Subcategory.Parameter
FILTER.BLOOM_FILTER.MODEL_PATH=/path/to/model
FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD=0

CLASSIFICATION.DECISION_TREE.ARFF_PATH=/path/to/header.arff
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/model.model

IO.AZURE_STORAGE_CONN_STR=DefaultEndpointsProtocol=https;...
IO.MQTT_PUBLISH.APOLLO_URL=tcp://broker:1883
```

### Loading Configuration

```java
Properties props = new Properties();
InputStream input = new FileInputStream("tasks.properties");
props.load(input);

// Pass to bolts
builder.setBolt("bolt", new SomeBolt(props), parallelism);
```

### Task Access

```java
public class SomeTask extends AbstractTask {
    private String modelPath;
    
    @Override
    public void setup(Logger l, Properties p) {
        super.setup(l, p);
        // Read configuration
        modelPath = p.getProperty("CLASSIFICATION.MODEL_PATH");
        
        // Initialize resources
        loadModel(modelPath);
    }
}
```

---

## Error Handling

### Task-Level Errors

```java
@Override
protected Float doTaskLogic(Map<String, String> map) {
    try {
        // Task logic
        return result;
    } catch (Exception e) {
        l.error("Error in task", e);
        return Float.MIN_VALUE;  // Signal error
    }
}
```

### Bolt-Level Errors

```java
@Override
public void execute(Tuple tuple) {
    try {
        Float result = task.doTask(convertTuple(tuple));
        
        if (result != null && result != Float.MIN_VALUE) {
            collector.emit(tuple, outputValues);
            collector.ack(tuple);
        } else {
            // Task failed or filtered
            collector.ack(tuple);  // Still acknowledge
        }
    } catch (Exception e) {
        l.error("Error in bolt", e);
        collector.fail(tuple);  // Trigger replay
    }
}
```

### Storm Reliability

RIoTBench leverages Storm's at-least-once processing:
- **Anchoring**: Output tuples are anchored to input tuples
- **Acking**: Successful processing is acknowledged
- **Timeout**: Unacked tuples are replayed after timeout
- **Fail**: Explicit failures trigger immediate replay

---

## Extensibility Points

### Adding New Micro-Benchmarks

1. **Implement Task**:
```java
package in.dream_lab.bm.stream_iot.tasks.mynew;

public class MyNewTask extends AbstractTask<String, String> {
    @Override
    public void setup(Logger l, Properties p) {
        super.setup(l, p);
        // Initialize
    }
    
    @Override
    protected Float doTaskLogic(Map<String, String> map) {
        // Implement logic
        return result;
    }
}
```

2. **Create Bolt**:
```java
public class MyNewBolt extends BaseRichBolt {
    private MyNewTask task;
    // Implement prepare(), execute(), declareOutputFields()
}
```

3. **Add to Factory**:
```java
// In MicroTopologyFactory.java
case "MyNewTask": return new MyNewBolt(p);
```

4. **Update Configuration**:
```properties
MYNEW.PARAMETER=value
```

### Adapting to Other Platforms

To port to Apache Flink:

1. Keep task implementations unchanged
2. Implement Flink-specific wrappers:
   - `MapFunction` or `FlatMapFunction` for stateless
   - `KeyedProcessFunction` for stateful
3. Build Flink DataStream API topology

Example:
```java
DataStream<Event> events = ...;

DataStream<Result> results = events
    .map(new FlinkTaskWrapper<>(new DecisionTreeClassify(), props));
```

---

## Performance Considerations

### Task Execution Overhead

```
Total Latency = Task Logic Time + Overhead

Overhead includes:
- Map conversion: ~0.1ms
- Timer operations: ~0.05ms
- Result conversion: ~0.1ms
- Tuple serialization: ~0.5-2ms
```

### Parallelism Guidelines

| Task Type | Recommended Parallelism | Reason |
|-----------|------------------------|---------|
| Parse | Low (1-3) | I/O bound, simple logic |
| Filter | Low (1-3) | Very fast, little CPU |
| Statistical | Medium (3-10) | CPU bound, stateful |
| ML | High (10-50) | CPU intensive |
| I/O | Low (1-5) | External dependency bound |

### Resource Requirements

| Component | CPU | Memory | Network |
|-----------|-----|--------|---------|
| Parse tasks | Low | Low | Low |
| Stateful tasks | Medium | Medium | Low |
| ML tasks | High | High | Low |
| I/O tasks | Low | Low | High |

---

## Design Benefits

✅ **Separation of Concerns**: Platform logic separate from benchmark logic  
✅ **Testability**: Tasks can be unit tested without Storm  
✅ **Reusability**: Same task used in multiple topologies  
✅ **Portability**: Easy to adapt to other platforms  
✅ **Maintainability**: Clear structure and responsibilities  
✅ **Extensibility**: Easy to add new benchmarks  
✅ **Performance**: Minimal overhead from abstraction  

---

## Next Steps

- Learn how to [Get Started](05-getting-started.md) running benchmarks
- Explore [Configuration Options](06-configuration.md) in detail
- Review [Dataset Information](07-datasets.md) for input data
