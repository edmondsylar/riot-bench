# Application Benchmarks

## Overview

RIoTBench provides **4 application-level benchmarks** that represent complete, end-to-end IoT dataflows. These applications compose multiple micro-benchmarks into realistic streaming pipelines that mirror real-world IoT use cases.

Each application benchmark demonstrates different aspects of IoT stream processing:

| Application | Code | Purpose | Complexity | Primary Operations |
|-------------|------|---------|------------|-------------------|
| **ETL** | ETL | Data ingestion and preparation | Medium | Parse, Filter, Transform |
| **STATS** | STATS | Real-time analytics dashboard | Medium | Statistical computations |
| **TRAIN** | TRAIN | Online machine learning | High | Model training, I/O |
| **PRED** | PRED | Real-time predictions | High | ML inference, integration |

---

## 1. ETL (Extract, Transform, Load)

### Purpose
The ETL dataflow demonstrates a typical data ingestion and preprocessing pipeline that:
1. Ingests raw sensor data
2. Parses and validates the data
3. Filters outliers and invalid readings
4. Interpolates missing values
5. Joins with metadata
6. Annotates with semantic labels
7. Converts to standard format
8. Publishes to downstream systems

### Dataflow Diagram

```
[Data Source]
      ↓
[SenML Parse] ──────────── Parse raw sensor messages
      ↓
[Range Filter] ─────────── Remove outliers
      ↓
[Bloom Filter] ─────────── Filter invalid sensors
      ↓
[Interpolation] ────────── Fill missing values
      ↓
[Join] ─────────────────── Join with metadata
      ↓
[Annotation] ───────────── Add semantic labels
      ↓
[CSV to SenML] ─────────── Convert to standard format
      ↓
[MQTT Publish] ─────────── Publish results
      ↓
[Sink] ─────────────────── Log output
```

### Implementation

**Main Class**: `in.dream_lab.bm.stream_iot.storm.topo.apps.ETLTopology`

**Storm Topology Structure**:

```java
TopologyBuilder builder = new TopologyBuilder();

// Data ingestion
builder.setSpout("spout", new SampleSenMLSpout(...), parallelism);

// Parse SenML messages
builder.setBolt("SenMLParseBolt", new SenMLParseBolt(props), 1)
    .shuffleGrouping("spout");

// Filter out-of-range values
builder.setBolt("RangeFilterBolt", new RangeFilterBolt(props), 1)
    .fieldsGrouping("SenMLParseBolt", new Fields("OBSTYPE"));

// Filter invalid sensors using Bloom filter
builder.setBolt("BloomFilterBolt", new BloomFilterCheckBolt(props), 1)
    .fieldsGrouping("RangeFilterBolt", new Fields("OBSTYPE"));

// Interpolate missing values
builder.setBolt("InterpolationBolt", new InterpolationBolt(props), 1)
    .fieldsGrouping("BloomFilterBolt", new Fields("OBSTYPE"));

// Join sensor data with metadata
builder.setBolt("JoinBolt", new JoinBolt(props), 1)
    .fieldsGrouping("InterpolationBolt", new Fields("MSGID"));

// Annotate with labels
builder.setBolt("AnnotationBolt", new AnnotationBolt(props), 1)
    .shuffleGrouping("JoinBolt");

// Convert to SenML format
builder.setBolt("CsvToSenMLBolt", new CsvToSenMLBolt(props), 1)
    .shuffleGrouping("AnnotationBolt");

// Publish to MQTT
builder.setBolt("PublishBolt", new MQTTPublishBolt(props), 1)
    .shuffleGrouping("CsvToSenMLBolt");

// Sink for logging
builder.setBolt("sink", new Sink(logFile), 1)
    .shuffleGrouping("PublishBolt");
```

### Micro-Benchmarks Used
- **SML**: SenML Parsing
- **RGF**: Range Filter
- **BLF**: Bloom Filter
- **INP**: Interpolation
- **JOIN**: Join operation
- **ANN**: Annotation
- **C2S**: CSV to SenML conversion
- **MQP**: MQTT Publish

### Grouping Strategies
- **Shuffle Grouping**: For stateless operations (parsing, annotation)
- **Fields Grouping**: For operations needing data from same sensor/observation type together

### Typical Throughput
- **Input Rate**: 100-10,000 events/second
- **End-to-end Latency**: 50-200ms
- **Scalability**: Highly parallelizable

### Use Cases
- Smart city sensor data ingestion
- Industrial IoT data preprocessing
- Environmental monitoring systems

### Variants
- **ETL_SQL_Topology**: Uses SQL database instead of MQTT
- Dataset-specific versions for TAXI, SYS, FIT, CITY datasets

---

## 2. STATS (Statistical Summarization)

### Purpose
The STATS dataflow computes real-time statistical summaries and analytics on sensor streams:
1. Parses incoming sensor data
2. Filters valid sensors
3. Computes moving averages
4. Applies Kalman filtering for noise reduction
5. Performs sliding window predictions
6. Computes distinct counts and moments
7. Publishes analytics to dashboards

### Dataflow Diagram

```
[Data Source]
      ↓
[Parse & Project] ───────── Extract relevant fields
      ↓
[Bloom Filter Check] ───── Filter valid sensors
      ├──────┬──────┬──────┐
      ↓      ↓      ↓      ↓
 [Kalman] [SLR]  [SOM]  [DAC]  ← Statistical computations
      ↓      ↓      ↓      ↓     (parallel processing)
      └──────┴──────┴──────┘
              ↓
      [MQTT Publish] ────────── Publish analytics
              ↓
          [Sink]
```

### Implementation

**Main Class**: `in.dream_lab.bm.stream_iot.storm.topo.apps.IoTStatsTopology`

**Storm Topology Structure**:

```java
TopologyBuilder builder = new TopologyBuilder();

// Data ingestion
builder.setSpout("spout", new SampleSpout(...), 1);

// Parse and project relevant fields
builder.setBolt("ParseProjectSYSBolt", new ParseProjectSYSBolt(props), 1)
    .shuffleGrouping("spout");

// Filter valid sensors
builder.setBolt("BloomFilterCheckBolt", new BloomFilterCheckBolt(props), 1)
    .fieldsGrouping("ParseProjectSYSBolt", new Fields("obsType"));

// Parallel statistical computations
builder.setBolt("KalmanFilterBolt", new KalmanFilterBolt(props), 1)
    .fieldsGrouping("BloomFilterCheckBolt", new Fields("sensorID", "obsType"));

builder.setBolt("SimpleLinearRegressionPredictorBolt", 
    new SimpleLinearRegressionPredictorBolt(props), 1)
    .fieldsGrouping("KalmanFilterBolt", new Fields("sensorID", "obsType"));

builder.setBolt("SecondOrderMomentBolt", new SecondOrderMomentBolt(props), 1)
    .fieldsGrouping("BloomFilterCheckBolt", new Fields("sensorID", "obsType"));

builder.setBolt("DistinctApproxCountBolt", new DistinctApproxCountBolt(props), 1)
    .fieldsGrouping("BloomFilterCheckBolt", new Fields("obsType"));

// Publish results
builder.setBolt("MQTTPublishTaskBolt", new MQTTPublishTaskBolt(props), 1)
    .shuffleGrouping("SimpleLinearRegressionPredictorBolt")
    .shuffleGrouping("SecondOrderMomentBolt")
    .shuffleGrouping("DistinctApproxCountBolt");

// Sink
builder.setBolt("sink", new Sink(logFile), 1)
    .shuffleGrouping("MQTTPublishTaskBolt");
```

### Micro-Benchmarks Used
- **SML**: SenML Parsing
- **BLF**: Bloom Filter
- **AVG**: Block Window Average
- **KAL**: Kalman Filter
- **SLR**: Sliding Linear Regression
- **SOM**: Second Order Moment
- **DAC**: Distinct Approximate Count
- **MQP**: MQTT Publish

### Key Features

#### Parallel Processing
Multiple statistical operations run in parallel on the same stream, enabling real-time computation of diverse metrics.

#### State Management
Each statistical operation maintains state per sensor ID and observation type, using Storm's fields grouping to ensure all events for the same sensor reach the same bolt instance.

#### Windowing
Different operations use different window sizes:
- Block Average: 10 events
- Kalman Filter: Infinite (recursive)
- SLR: 10 events
- DAC: HyperLogLog buckets

### Typical Throughput
- **Input Rate**: 100-5,000 events/second
- **Latency**: 20-100ms per operation
- **State Size**: ~100KB per 1000 unique sensors

### Use Cases
- Smart building energy monitoring
- Air quality monitoring dashboards
- Traffic flow analytics
- Equipment health monitoring

### Variants
- **StatsWithVisualizationTopology**: Includes real-time plotting
- **Stats_SQL_Topology**: Stores results in SQL database

---

## 3. TRAIN (Model Training)

### Purpose
The TRAIN dataflow implements online machine learning where models are continuously updated with new data:
1. Periodically fetches training data batches
2. Trains decision tree and linear regression models
3. Uploads updated models to cloud storage
4. Publishes model metadata via MQTT

### Dataflow Diagram

```
[Timer Spout] ──────────── Periodic trigger
      ↓
[Azure Table Range Query] ── Fetch training batch
      ↓
      ├─────────────┬─────────────┐
      ↓             ↓             ↓
[Decision Tree] [Linear Reg] [Annotate]  ← Parallel training
    Train         Train
      ↓             ↓             ↓
      └─────────────┴─────────────┘
                    ↓
        [Azure Blob Upload] ──── Store model
                    ↓
           [MQTT Publish] ───── Notify model update
                    ↓
                [Sink]
```

### Implementation

**Main Classes**: 
- `IoTTrainTopologyTAXI`
- `IoTTrainTopologySYS`
- `IoTTrainTopologyFIT`

**Storm Topology Structure**:

```java
TopologyBuilder builder = new TopologyBuilder();

// Timer-based trigger for periodic training
builder.setSpout("TimeSpout", new SampleSpoutTimerForTrain(...), 1);

// Fetch training data from Azure Table
builder.setBolt("AzureTableRangeQueryBolt", 
    new AzureTableRangeQueryBolt(props), 10)
    .shuffleGrouping("TimeSpout");

// Train linear regression model
builder.setBolt("LinearRegressionTrainBolt", 
    new LinearRegressionTrainBolt(props), 1)
    .shuffleGrouping("AzureTableRangeQueryBolt");

// Upload trained model to Azure Blob
builder.setBolt("AzureBlobUploadTaskBolt", 
    new AzureBlobUploadTaskBolt(props), 1)
    .shuffleGrouping("LinearRegressionTrainBolt");

// Publish notification
builder.setBolt("MQTTPublishBolt", new MQTTPublishBolt(props), 1)
    .shuffleGrouping("AzureBlobUploadTaskBolt");

// Sink
builder.setBolt("sink", new Sink(logFile), 1)
    .shuffleGrouping("MQTTPublishBolt");
```

### Micro-Benchmarks Used
- **ATR**: Azure Table Range Query
- **DTT**: Decision Tree Train
- **MLT**: Multi-variate Linear Regression Train
- **ANN**: Annotate (for labeling)
- **ABU**: Azure Blob Upload
- **MQP**: MQTT Publish

### Training Strategy

#### Batch Training
Models are trained on batches of data rather than single instances:
- Batch size: 100-1000 records (configurable)
- Training frequency: Every N events or time period
- Model persistence: Serialized to Azure Blob Storage

#### Incremental Updates
```java
// Accumulate instances
if (instanceCount < MODEL_UPDATE_FREQUENCY) {
    trainingData.add(newInstance);
    instanceCount++;
} else {
    // Train model
    classifier.buildClassifier(trainingData);
    
    // Serialize model
    SerializationHelper.write(modelPath, classifier);
    
    // Reset for next batch
    trainingData.clear();
    instanceCount = 0;
}
```

### Typical Performance
- **Training Frequency**: Every 100-1000 events
- **Training Time**: 500ms - 5s per batch
- **Model Size**: 10KB - 5MB
- **Data Fetch Time**: 100ms - 2s

### Use Cases
- Adaptive anomaly detection
- Predictive maintenance with evolving patterns
- Traffic prediction models
- Energy consumption forecasting

### Dataset-Specific Implementations
- **TAXI**: Predicting taxi trip duration, fare
- **SYS**: Air quality level classification
- **FIT**: Activity recognition from fitness sensors

---

## 4. PRED (Predictive Analytics)

### Purpose
The PRED dataflow performs real-time predictions using pre-trained or continuously updated models:
1. Ingests sensor data stream
2. Fetches latest trained models from storage
3. Applies ML models for classification/regression
4. Computes block window averages
5. Estimates prediction errors
6. Publishes predictions via MQTT

### Dataflow Diagram

```
[Sensor Stream]              [MQTT Model Updates]
      ↓                               ↓
[SenML Parse] ─────────────── [MQTT Subscribe]
      ↓                               ↓
      ├─────────────┐         [Azure Blob Download]
      ↓             ↓                 ↓
[Decision Tree] [Linear Reg] ←───────┘
   Classify      Predict      (Model loading)
      ↓             ↓
      └─────────────┘
            ↓
   [Block Window Avg] ──────── Compute actual averages
            ↓
   [Error Estimation] ─────── Compare prediction vs actual
            ↓
      [MQTT Publish] ────────── Publish predictions
            ↓
         [Sink]
```

### Implementation

**Main Classes**:
- `IoTPredictionTopologyTAXI`
- `IoTPredictionTopologySYS`
- `IoTPredictionTopologyFIT`

**Storm Topology Structure**:

```java
TopologyBuilder builder = new TopologyBuilder();

// Sensor data stream
builder.setSpout("spout1", new SampleSenMLSpout(...), 1);

// Model update stream
builder.setSpout("mqttSubscribeTaskBolt", 
    new MQTTSubscribeSpout(props, "dummyLog"), 1);

// Parse sensor data
builder.setBolt("SenMLParseBoltPREDTAXI", 
    new SenMLParseBoltPREDTAXI(props), 1)
    .shuffleGrouping("spout1");

// Download latest model when notified
builder.setBolt("AzureBlobDownloadTaskBolt", 
    new AzureBlobDownloadTaskBolt(props), 1)
    .shuffleGrouping("mqttSubscribeTaskBolt");

// Decision tree classification
builder.setBolt("DecisionTreeClassifyBolt", 
    new DecisionTreeClassifyBolt(props), 1)
    .shuffleGrouping("SenMLParseBoltPREDTAXI")
    .fieldsGrouping("AzureBlobDownloadTaskBolt", new Fields("ANALAYTICTYPE"));

// Linear regression prediction
builder.setBolt("LinearRegressionPredictorBolt", 
    new LinearRegressionPredictorBolt(props), 1)
    .shuffleGrouping("SenMLParseBoltPREDTAXI")
    .fieldsGrouping("AzureBlobDownloadTaskBolt", new Fields("ANALAYTICTYPE"));

// Compute block average for ground truth
builder.setBolt("BlockWindowAverageBolt", 
    new BlockWindowAverageBolt(props), 1)
    .shuffleGrouping("SenMLParseBoltPREDTAXI");

// Estimate prediction error
builder.setBolt("ErrorEstimationBolt", new ErrorEstimationBolt(props), 1)
    .shuffleGrouping("BlockWindowAverageBolt")
    .shuffleGrouping("LinearRegressionPredictorBolt");

// Publish predictions
builder.setBolt("MQTTPublishBolt", new MQTTPublishBolt(props), 1)
    .fieldsGrouping("ErrorEstimationBolt", new Fields("ANALAYTICTYPE"))
    .fieldsGrouping("DecisionTreeClassifyBolt", new Fields("ANALAYTICTYPE"));

// Sink
builder.setBolt("sink", new Sink(logFile), 1)
    .shuffleGrouping("MQTTPublishBolt");
```

### Micro-Benchmarks Used
- **SML**: SenML Parsing
- **MQS**: MQTT Subscribe (for model updates)
- **ABD**: Azure Blob Download (fetch models)
- **DTC**: Decision Tree Classify
- **MLR**: Multi-variate Linear Regression
- **AVG**: Block Window Average
- **MQP**: MQTT Publish

### Key Features

#### Dynamic Model Loading
Models can be updated without restarting the topology:
1. Training pipeline publishes model update notification to MQTT
2. Prediction topology subscribes to model update topic
3. New model is downloaded from Azure Blob Storage
4. Prediction bolt loads new model dynamically

#### Dual Prediction Streams
Runs classification and regression in parallel:
- **Classification**: Categorical predictions (e.g., air quality level)
- **Regression**: Continuous predictions (e.g., temperature forecast)

#### Error Estimation
Compares predictions against actual observed values in real-time to compute prediction accuracy metrics.

### Typical Performance
- **Input Rate**: 100-10,000 events/second
- **Prediction Latency**: 1-10ms
- **Model Load Time**: 50-500ms
- **End-to-end Latency**: 100-300ms

### Use Cases
- Real-time air quality forecasting
- Predictive maintenance alerts
- Traffic congestion prediction
- Energy demand forecasting
- Health monitoring and alerts

### Integration Pattern
```
Training Pipeline (TRAIN) ──→ [Azure Blob] ←── Prediction Pipeline (PRED)
                                    ↑  ↓
                              [MQTT Broker]
                              (Model updates)
```

---

## Running Application Benchmarks

### Command Format

```bash
storm jar <jar-path> <main-class> <args>
```

### Example: Running ETL

```bash
storm jar iot-bm-storm-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.ETLTopology \
  C ETL-TAXI /data/taxi-input.csv TAXI-001 1.0 \
  /logs/output /config/tasks_TAXI.properties
```

### Example: Running STATS

```bash
storm jar iot-bm-storm-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.IoTStatsTopology \
  L STATS-SYS /data/sys-input.csv SYS-001 1.0 \
  /logs/output /config/tasks.properties
```

### Example: Running TRAIN

```bash
storm jar iot-bm-storm-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.IoTTrainTopologyTAXI \
  C TRAIN-TAXI /data/timer-input.csv TRAIN-001 1.0 \
  /logs/output /config/tasks_TAXI.properties
```

### Example: Running PRED

```bash
storm jar iot-bm-storm-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.IoTPredictionTopologyTAXI \
  C PRED-TAXI /data/taxi-predict.csv PRED-001 1.0 \
  /logs/output /config/tasks_TAXI.properties
```

### Argument Explanation

1. **Deployment Mode**: `C` (cluster) or `L` (local)
2. **Topology Name**: Unique identifier
3. **Input File**: Path to dataset CSV
4. **Run ID**: Experiment identifier
5. **Scaling Factor**: Event rate multiplier
6. **Output Directory**: Where to write logs
7. **Config File**: Path to tasks.properties

---

## Performance Comparison

| Application | Complexity | Avg Latency | Throughput | Stateful Ops | I/O Ops |
|-------------|------------|-------------|------------|--------------|---------|
| **ETL** | Medium | 50-200ms | High | 2 | 1 |
| **STATS** | Medium | 20-100ms | High | 5 | 1 |
| **TRAIN** | High | 500ms-5s | Low | 2 | 2-3 |
| **PRED** | High | 100-300ms | Medium | 3 | 2-3 |

---

## Customization

### Adding New Operations

To add a new bolt to an application:

```java
// 1. Create or reuse a task
builder.setBolt("MyCustomBolt", new MyCustomBolt(props), parallelism)
    .shuffleGrouping("PreviousBolt");

// 2. Connect to sink
builder.setBolt("sink", new Sink(logFile), 1)
    .shuffleGrouping("MyCustomBolt");
```

### Changing Parallelism

```java
// Increase parallelism for compute-intensive operations
builder.setBolt("DecisionTreeClassifyBolt", 
    new DecisionTreeClassifyBolt(props), 10)  // 10 parallel instances
    .shuffleGrouping("ParseBolt");
```

### Modifying Grouping Strategy

```java
// Fields grouping ensures same key goes to same instance
.fieldsGrouping("source", new Fields("sensorID", "obsType"))

// Shuffle grouping distributes randomly
.shuffleGrouping("source")

// All grouping sends to all instances
.allGrouping("source")

// Global grouping sends everything to one instance
.globalGrouping("source")
```

---

## Next Steps

- Understand the [Architecture & Design](04-architecture.md) behind these applications
- Learn how to [Configure and Run](05-getting-started.md) the benchmarks
- Explore [Configuration Options](06-configuration.md) for tuning
