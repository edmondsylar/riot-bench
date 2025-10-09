# Micro-Benchmarks

## Overview

RIoTBench includes **26 micro-benchmarks** that test individual operations commonly found in IoT stream processing applications. Each micro-benchmark is implemented as a standalone task that can be executed independently or composed into larger dataflows.

## Benchmark Characteristics

Each micro-benchmark has the following properties:

- **Code**: Short identifier (e.g., SML, BLF, DTC)
- **Category**: Type of operation (Parse, Filter, Statistical, Predictive, IO, Visualization)
- **Operation**: Processing pattern (Transform, Filter, Aggregate, etc.)
- **Cardinality**: Input-to-output ratio (1:1, 1:0/1, N:1, N:M)
- **Stateful**: Whether the operation maintains state across events

## Complete Benchmark List

| Benchmark Name | Code | Category | Operation | Cardinality | Stateful |
|----------------|------|----------|-----------|-------------|----------|
| Annotate | ANN | Parse | Transform | 1:1 | No |
| CsvToSenML | C2S | Parse | Transform | 1:1 | No |
| SenML Parsing | SML | Parse | Transform | 1:1 | No |
| XML Parsing | XML | Parse | Transform | 1:1 | No |
| Bloom Filter | BLF | Filter | Filter | 1:0/1 | No |
| Range Filter | RGF | Filter | Filter | 1:0/1 | No |
| Accumulator | ACC | Statistical | Aggregate | N:1 | Yes |
| Average | AVG | Statistical | Aggregate | N:1 | Yes |
| Distinct Approx. Count | DAC | Statistical | Transform | 1:1 | Yes |
| Kalman Filter | KAL | Statistical | Transform | 1:1 | Yes |
| Second Order Moment | SOM | Statistical | Transform | 1:1 | Yes |
| Interpolation | INP | Statistical | Transform | 1:1 | Yes |
| Decision Tree Classify | DTC | Predictive | Transform | 1:1 | No |
| Decision Tree Train | DTT | Predictive | Aggregate | N:1 | No |
| Multi-var. Linear Reg. | MLR | Predictive | Transform | 1:1 | No |
| Multi-var. Linear Reg. Train | MLT | Predictive | Aggregate | N:1 | No |
| Sliding Linear Regression | SLR | Predictive | Flat Map | N:M | Yes |
| Azure Blob Download | ABD | IO | Source/Transform | 1:1 | No |
| Azure Blob Upload | ABU | IO | Sink | 1:1 | No |
| Azure Table Lookup | ATL | IO | Source/Transform | 1:1 | No |
| Azure Table Range | ATR | IO | Source/Transform | 1:1 | No |
| Azure Table Insert | ATI | IO | Transform | 1:1 | No |
| MQTT Publish | MQP | IO | Sink | 1:1 | No |
| MQTT Subscribe | MQS | IO | Source | 1:1 | No |
| Local Files Zip | LZP | IO | Sink | 1:1 | No |
| Remote Files Zip | RZP | IO | Sink | 1:1 | No |
| Multi-Line Plot | PLT | Visualization | Transform | 1:1 | No |

---

## 1. Parse Benchmarks

Parse benchmarks handle data format conversions and field extraction from structured formats.

### 1.1 Annotate (ANN)

**Purpose**: Adds metadata annotations to data based on classification results or lookup tables.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.annotate.Annotate`

**Use Case**: Adding semantic labels to sensor data (e.g., "Excellent", "Good", "Poor" air quality)

**Configuration**:
```properties
PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH=/path/to/schema-with-annotations.txt
```

---

### 1.2 CsvToSenML (C2S)

**Purpose**: Converts CSV-formatted sensor data to SenML (Sensor Markup Language) format.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.parse.CsvToSenMLParse`

**Input**: CSV string with sensor readings
**Output**: JSON-formatted SenML message

**Use Case**: Standardizing heterogeneous sensor data formats

**Configuration**:
```properties
PARSE.CSV_SENML_USE_MSG_FIELD=0
PARSE.META_FIELD_SCHEMA=timestamp,longitude,latitude
PARSE.ID_FIELD_SCHEMA=source
```

---

### 1.3 SenML Parsing (SML)

**Purpose**: Parses SenML (Sensor Markup Language) messages and extracts sensor readings.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.parse.SenMLParse`

**SenML Format**:
```json
{
  "bn": "urn:dev:mac:0024befffe804ff1",
  "bt": 1320067464,
  "bu": "A",
  "e": [{"n": "voltage", "u": "V", "v": 120.1}]
}
```

**Use Case**: Processing standardized IoT sensor messages

---

### 1.4 XML Parsing (XML)

**Purpose**: Parses XML-formatted sensor data and extracts values.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.parse.XMLParse`

**Configuration**:
```properties
PARSE.XML_FILEPATH=/path/to/sample.xml
```

**Use Case**: Legacy systems that produce XML sensor data

---

## 2. Filter Benchmarks

Filter benchmarks determine which events should be processed further based on specific criteria.

### 2.1 Bloom Filter (BLF)

**Purpose**: Probabilistic filter to check if a sensor ID exists in a trained set with high efficiency.

**Implementation**: 
- `in.dream_lab.bm.stream_iot.tasks.filter.BloomFilterCheck` (checking)
- `in.dream_lab.bm.stream_iot.tasks.filter.BloomFilterTrain` (training)

**How it works**: Uses Guava's BloomFilter for space-efficient membership testing with configurable false positive rate.

**Configuration**:
```properties
FILTER.BLOOM_FILTER.MODEL_PATH=/path/to/bloomfilter.model
FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD=0
FILTER.BLOOM_FILTER_TRAIN.EXPECTED_INSERTIONS=20000000
FILTER.BLOOM_FILTER_TRAIN.FALSEPOSITIVE_RATIO=0.01
```

**Use Case**: Filtering out unauthorized sensor IDs or known malicious sources

**Performance**: O(k) where k is number of hash functions, typically 10-15x faster than hash table lookup

---

### 2.2 Range Filter (RGF)

**Purpose**: Filters out sensor readings that fall outside valid ranges (outlier detection).

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.filter.RangeFilterCheck`

**Configuration**:
```properties
FILTER.RANGE_FILTER.VALID_RANGE=temperature:0.7:35.1,humidity:20.3:69.1,light:0:5153
FILTER.RANGE_FILTER.USE_MSG_FIELD=0
```

**Use Case**: Removing physically impossible sensor readings (e.g., temperature > 100°C)

**Output**: Returns Float.MIN_FLOAT if value is out of range, actual value otherwise

---

## 3. Statistical Benchmarks

Statistical benchmarks perform real-time analytics and statistical computations on streaming data.

### 3.1 Accumulator (ACC)

**Purpose**: Accumulates values over a sliding window for windowed aggregations.

**Implementation**: Part of aggregate operations

**Configuration**:
```properties
AGGREGATE.ACCUMLATOR.TUPLE_WINDOW_SIZE=20
AGGREGATE.ACCUMLATOR.MULTIVALUE_OBSTYPE=SLR
```

**Use Case**: Computing windowed sums, counts, or collecting batches for training

---

### 3.2 Average (AVG)

**Purpose**: Computes moving average over a block window of sensor readings.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.aggregate.BlockWindowAverage`

**Configuration**:
```properties
AGGREGATE.BLOCK_COUNT.WINDOW_SIZE=10
AGGREGATE.BLOCK_AVERAGE.USE_MSG_FIELD=temperature,humidity,light
```

**Algorithm**: Maintains a sliding window and computes arithmetic mean

**Use Case**: Smoothing noisy sensor data

---

### 3.3 Distinct Approximate Count (DAC)

**Purpose**: Estimates the number of distinct elements in a stream using HyperLogLog algorithm.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.aggregate.DistinctApproxCount`

**Configuration**:
```properties
AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS=5
AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD=source
```

**Algorithm**: HyperLogLog provides approximate count with ~2% error using minimal memory

**Use Case**: Counting unique sensors, users, or events in real-time

---

### 3.4 Kalman Filter (KAL)

**Purpose**: Applies Kalman filtering to estimate true sensor values from noisy measurements.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.statistics.KalmanFilter`

**Configuration**:
```properties
STATISTICS.KALMAN_FILTER.PROCESS_NOISE=0.125
STATISTICS.KALMAN_FILTER.SENSOR_NOISE=0.32
STATISTICS.KALMAN_FILTER.ESTIMATED_ERROR=30
STATISTICS.KALMAN_FILTER.USE_MSG_FIELDLIST=temperature,humidity,light
```

**Algorithm**: Recursive Bayesian estimation with prediction and correction steps

**Use Case**: Cleaning noisy sensor readings, sensor fusion

---

### 3.5 Interpolation (INP)

**Purpose**: Fills missing sensor values using linear interpolation.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.statistics.Interpolation`

**Configuration**:
```properties
STATISTICS.INTERPOLATION.USE_MSG_FIELD=temperature,humidity,light
STATISTICS.INTERPOLATION.WINDOW_SIZE=5
```

**Algorithm**: Linear interpolation between previous and next known values

**Use Case**: Handling sensor dropouts or missing data

---

### 3.6 Second Order Moment (SOM)

**Purpose**: Computes variance and standard deviation in real-time.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.statistics.SecondOrderMoment`

**Algorithm**: Incremental variance using Welford's method

**Use Case**: Detecting anomalies based on statistical variance

---

## 4. Predictive Analytics Benchmarks

Predictive benchmarks use machine learning models for classification and regression.

### 4.1 Decision Tree Classify (DTC)

**Purpose**: Classifies sensor data using a pre-trained decision tree model.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.predict.DecisionTreeClassify`

**ML Framework**: Weka J48 (C4.5 decision tree)

**Configuration**:
```properties
CLASSIFICATION.DECISION_TREE.ARFF_PATH=/path/to/header.arff
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/model.model
CLASSIFICATION.DECISION_TREE.CLASSIFY.RESULT_ATTRIBUTE_INDEX=6
```

**Input**: Feature vector from parsed sensor data
**Output**: Class label (e.g., "Excellent", "Good", "Fair", "Poor")

**Use Case**: Air quality classification, equipment health prediction

---

### 4.2 Decision Tree Train (DTT)

**Purpose**: Trains/updates a decision tree model on incoming data batches.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.predict.DecisionTreeTrain`

**Configuration**:
```properties
CLASSIFICATION.DECISION_TREE.TRAIN.MODEL_UPDATE_FREQUENCY=100
```

**Algorithm**: Batch training on accumulated instances

**Use Case**: Online learning, adaptive models

---

### 4.3 Multi-variate Linear Regression (MLR)

**Purpose**: Predicts a continuous value using a pre-trained linear regression model.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.predict.LinearRegressionPredictor`

**ML Framework**: Weka Linear Regression

**Configuration**:
```properties
PREDICT.LINEAR_REGRESSION.MODEL_PATH=/path/to/LR-model.model
PREDICT.LINEAR_REGRESSION.TRAIN.ARFF_PATH=/path/to/header.arff
```

**Use Case**: Predicting energy consumption, traffic flow, sensor values

---

### 4.4 Multi-variate Linear Regression Train (MLT)

**Purpose**: Trains/updates a linear regression model on streaming data.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.predict.LinearRegressionTrain`

**Configuration**:
```properties
PREDICT.LINEAR_REGRESSION.TRAIN.MODEL_UPDATE_FREQUENCY=300
```

---

### 4.5 Sliding Linear Regression (SLR)

**Purpose**: Computes linear regression over a sliding window for trend analysis.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.predict.SimpleLinearRegressionPredictor`

**Configuration**:
```properties
PREDICT.SIMPLE_LINEAR_REGRESSION.WINDOW_SIZE_TRAIN=10
PREDICT.SIMPLE_LINEAR_REGRESSION.WINDOW_SIZE_PREDICT=10
```

**Algorithm**: Uses Apache Commons Math SimpleRegression

**Use Case**: Detecting trends, forecasting next values

---

## 5. I/O Benchmarks

I/O benchmarks test integration with external storage systems and messaging infrastructure.

### 5.1 Azure Blob Download (ABD)

**Purpose**: Downloads files from Azure Blob Storage.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.io.AzureBlobDownloadTask`

**Configuration**:
```properties
IO.AZURE_STORAGE_CONN_STR=DefaultEndpointsProtocol=https;...
IO.AZURE_BLOB.CONTAINER_NAME=mycontainer
IO.AZURE_BLOB_DOWNLOAD.FILE_NAMES=file1.jpg,file2.jpg
```

**Use Case**: Fetching reference data, models, or configuration files

---

### 5.2 Azure Blob Upload (ABU)

**Purpose**: Uploads data or results to Azure Blob Storage.

**Implementation**: 
- `in.dream_lab.bm.stream_iot.tasks.io.AzureBlobUploadTask`
- `in.dream_lab.bm.stream_iot.tasks.io.AzureBlobUploadFromStreamTask`

**Configuration**:
```properties
IO.AZURE_BLOB_UPLOAD.FILE_SOURCE_PATH=/path/to/file.png
IO.AZURE_BLOB_UPLOAD.DIR_NAME=/output/directory
```

**Use Case**: Storing trained models, aggregated results, or logs

---

### 5.3 Azure Table Insert (ATI)

**Purpose**: Inserts sensor data into Azure Table Storage.

**Implementation**: 
- `in.dream_lab.bm.stream_iot.tasks.io.AzureTableInsert`
- `in.dream_lab.bm.stream_iot.tasks.io.AzureTableBatchInsert`

**Configuration**:
```properties
IO.AZURE_TABLE.TABLE_NAME=sensordata
IO.AZURE_TABLE.PARTITION_KEY=1
```

**Use Case**: Persisting processed sensor data for historical queries

---

### 5.4 Azure Table Range Query (ATR)

**Purpose**: Queries a range of rows from Azure Table Storage.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.io.AzureTableRangeQueryTask*`

**Configuration**:
```properties
IO.AZURE_TABLE.START_ROW_KEY=1
IO.AZURE_TABLE.END_ROW_KEY=1220000
```

**Use Case**: Fetching historical data for training or comparison

---

### 5.5 MQTT Publish (MQP)

**Purpose**: Publishes processed data to an MQTT broker.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.io.MQTTPublishTask`

**Configuration**:
```properties
IO.MQTT_PUBLISH.APOLLO_URL=tcp://broker.example.com:1883
IO.MQTT_PUBLISH.TOPIC_NAME=sensors/output
IO.MQTT_PUBLISH.APOLLO_USER=admin
IO.MQTT_PUBLISH.APOLLO_PASSWORD=secret
```

**Use Case**: Publishing results to downstream systems or dashboards

---

### 5.6 MQTT Subscribe (MQS)

**Purpose**: Subscribes to an MQTT topic to receive sensor data.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.io.MQTTSubscribeTask`

**Use Case**: Ingesting data from MQTT-based sensor networks

---

## 6. Visualization Benchmarks

### 6.1 Multi-Line Plot (PLT)

**Purpose**: Creates real-time line plots for multiple time series.

**Implementation**: `in.dream_lab.bm.stream_iot.tasks.visualize.XChartMultiLinePlotTask`

**Library**: XChart (https://github.com/knowm/XChart)

**Configuration**: Plots are generated as PNG/JPEG images

**Use Case**: Real-time monitoring dashboards, trend visualization

---

## Running Micro-Benchmarks

### Standalone Execution

Each micro-benchmark can be tested independently:

```java
Properties props = new Properties();
props.load(new FileInputStream("tasks.properties"));

DecisionTreeClassify task = new DecisionTreeClassify();
task.setup(logger, props);

Map<String, String> input = new HashMap<>();
input.put("msgId", "sensor123");
input.put("data", "25.5,60.2,1200,150,25");

Float result = task.doTask(input);
```

### Storm Topology Execution

Use the `MicroTopologyDriver` to run any micro-benchmark:

```bash
storm jar iot-bm-storm.jar \
  in.dream_lab.bm.stream_iot.storm.topo.micro.MicroTopologyDriver \
  C MyTopology /path/to/input.csv PLUG-001 1.0 \
  /path/to/output /path/to/tasks.properties DecisionTreeClassify
```

### Task Names for MicroTopologyDriver

Refer to `MicroTopologyFactory.java` for the complete list of task names:

- `SenMLParse`, `XMLParse`, `CsvToSenMLParse`, `Annotate`
- `BloomFilterCheck`, `RangeFilter`
- `BlockWindowAverage`, `KalmanFilter`, `Interpolation`, `DistinctApproxCount`
- `DecisionTreeClassify`, `DecisionTreeTrain`, `LinearRegressionPredictor`, `LinearRegressionTrain`
- `AzureBlobUpload`, `AzureBlobDownload`, `AzureTableInsert`, `AzureTableRangeQuery`
- `MQTTPublish`, `MQTTSubscribe`

---

## Performance Characteristics

| Category | Avg. Latency | CPU Intensity | Memory Usage | I/O Dependency |
|----------|--------------|---------------|--------------|----------------|
| Parse | Low (< 1ms) | Low | Low | No |
| Filter | Very Low (< 0.5ms) | Very Low | Low-Medium | No |
| Statistical | Low-Medium | Medium | Medium | No |
| Predictive | Medium-High | High | Medium-High | No |
| I/O | High (> 50ms) | Low | Low | **Yes** |
| Visualization | High | Medium | High | Yes |

---

## Next Steps

- Learn how micro-benchmarks are combined into [Application Benchmarks](03-application-benchmarks.md)
- Understand the [Architecture & Design](04-architecture.md) of the task framework
- Follow the [Getting Started Guide](05-getting-started.md) to run benchmarks
