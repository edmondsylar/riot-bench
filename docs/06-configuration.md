# Configuration Guide

## Overview

RIoTBench uses a properties-based configuration system where all benchmark parameters are specified in `tasks.properties` files. This guide provides detailed information about all configuration options.

---

## Configuration File Structure

### File Format

```properties
# Category.Operation.Subcategory.Parameter=value
CATEGORY.OPERATION.PARAMETER=value

# Comments start with #
# Use absolute paths for file references
# Boolean values: true/false
# Numeric values: integers or decimals
# Lists: comma-separated values
```

### Loading Configuration

Configuration is loaded at topology startup:

```java
Properties p = new Properties();
InputStream input = new FileInputStream("tasks.properties");
p.load(input);
```

---

## Parse Configuration

### CSV Parsing

```properties
# Schema for CSV data (field names)
PARSE.CSV_SCHEMA_FILEPATH=/path/to/sys-schema.txt

# Schema with annotation fields
PARSE.CSV_SCHEMA_WITH_ANNOTATEDFIELDS_FILEPATH=/path/to/sys-schema-with-annotations.txt

# Metadata field schema
PARSE.META_FIELD_SCHEMA=timestamp,longitude,latitude

# Identifier field schema
PARSE.ID_FIELD_SCHEMA=source

# Field index to use from message
PARSE.CSV_SENML_USE_MSG_FIELD=0
```

**Schema File Format** (`sys-schema.txt`):
```
timestamp
source
temperature
humidity
light
dust
airquality_raw
```

### SenML Parsing

```properties
# Schema for SenML CSV conversion
SPOUT.SENML_CSV_SCHEMA_PATH=/path/to/sys-schema-for-senml.txt
```

### XML Parsing

```properties
# Path to XML file for parsing
PARSE.XML_FILEPATH=/path/to/sample.xml
```

---

## Filter Configuration

### Bloom Filter

```properties
# Training parameters
FILTER.BLOOM_FILTER_TRAIN.EXPECTED_INSERTIONS=20000000
FILTER.BLOOM_FILTER_TRAIN.FALSEPOSITIVE_RATIO=0.01

# Model path
FILTER.BLOOM_FILTER.MODEL_PATH=/path/to/bloomfilter.model

# Field to check
FILTER.BLOOM_FILTER_CHECK.USE_MSG_FIELD=0
```

**Training Parameters**:
- `EXPECTED_INSERTIONS`: Number of elements to insert (higher = larger filter)
- `FALSEPOSITIVE_RATIO`: Probability of false positive (lower = more accurate, larger filter)

**Model File**: Serialized Guava BloomFilter object

### Multiple Bloom Filters

```properties
# List of model paths (comma-separated)
FILTER.MULTI_BLOOM_FILTER.MODEL_PATH_LIST=/path/to/filter1,/path/to/filter2

# List of fields to check (comma-separated)
FILTER.MULTI_BLOOM_FILTER.USE_MSG_FIELD_LIST=source,deviceId
```

### Range Filter

```properties
# Format: field:min:max,field:min:max,...
FILTER.RANGE_FILTER.VALID_RANGE=temperature:0.7:35.1,humidity:20.3:69.1,light:0:5153,dust:83.36:3322.67,airquality_raw:12:49

# Field index to use
FILTER.RANGE_FILTER.USE_MSG_FIELD=0
```

**Format**:
- Each range: `fieldName:minValue:maxValue`
- Multiple ranges separated by commas
- Values outside range are filtered out

---

## Aggregate Configuration

### Block Window

```properties
# Window size (number of events)
AGGREGATE.BLOCK_COUNT.WINDOW_SIZE=10

# Field index to use
AGGREGATE.BLOCK_COUNT.USE_MSG_FIELD=6
```

### Block Window Average

```properties
# Fields to average (comma-separated)
AGGREGATE.BLOCK_AVERAGE.USE_MSG_FIELD=temperature,humidity,light,dust,airquality_raw
```

### Distinct Approximate Count

```properties
# Number of HyperLogLog buckets (higher = more accurate)
AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS=5

# Field to count distinct values
AGGREGATE.DISTINCT_APPROX_COUNT.USE_MSG_FIELD=source
```

**Bucket Size**:
- 4-6: Moderate accuracy (~5% error)
- 7-10: Good accuracy (~2% error)
- 11-16: High accuracy (<1% error)

### Accumulator

```properties
# Window size for accumulation
AGGREGATE.ACCUMLATOR.TUPLE_WINDOW_SIZE=20

# Observation type for multi-value data
AGGREGATE.ACCUMLATOR.MULTIVALUE_OBSTYPE=SLR

# Timestamp field index
AGGREGATE.ACCUMLATOR.META_TIMESTAMP_FIELD=0
```

---

## Statistical Configuration

### Kalman Filter

```properties
# Process noise covariance (Q)
STATISTICS.KALMAN_FILTER.PROCESS_NOISE=0.125

# Measurement noise covariance (R)
STATISTICS.KALMAN_FILTER.SENSOR_NOISE=0.32

# Initial estimation error covariance (P)
STATISTICS.KALMAN_FILTER.ESTIMATED_ERROR=30

# Field index to filter
STATISTICS.KALMAN_FILTER.USE_MSG_FIELD=1

# List of fields to filter (comma-separated)
STATISTICS.KALMAN_FILTER.USE_MSG_FIELDLIST=temperature,humidity,light,dust,airquality_raw
```

**Parameter Tuning**:
- Lower `PROCESS_NOISE`: Assumes stable system (trusts model more)
- Lower `SENSOR_NOISE`: Assumes accurate sensors (trusts measurements more)
- Higher `ESTIMATED_ERROR`: More uncertainty initially (adapts faster)

### Interpolation

```properties
# Fields to interpolate (comma-separated)
STATISTICS.INTERPOLATION.USE_MSG_FIELD=temperature,humidity,light,dust,airquality_raw

# Window size for interpolation
STATISTICS.INTERPOLATION.WINDOW_SIZE=5
```

**Window Size**: Number of surrounding points to use for interpolation

### Second Order Moment

```properties
# Counter initialization
STATISTICS.MOMENT.COUNTER=0

# Maximum HashMap size for state management
STATISTICS.MOMENT.MAX_HASHMAPSIZE=10

# Field index to compute moments
STATISTICS.MOMENT.USE_MSG_FIELD=-1
```

---

## Classification Configuration

### Decision Tree (J48)

#### For SYS Dataset

```properties
# ARFF header file (defines features)
CLASSIFICATION.DECISION_TREE.ARFF_PATH=/path/to/DecisionTreeClassifyHeaderOnly-SYS.arff

# Trained model file
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/DecisionTreeClassify-SYS.model

# Index of classification result attribute
CLASSIFICATION.DECISION_TREE.CLASSIFY.RESULT_ATTRIBUTE_INDEX=6

# Field index to use from message
CLASSIFICATION.DECISION_TREE.USE_MSG_FIELD=-1

# Training: How often to rebuild model (number of instances)
CLASSIFICATION.DECISION_TREE.TRAIN.MODEL_UPDATE_FREQUENCY=100

# Sample header for training
CLASSIFICATION.DECISION_TREE.SAMPLE_HEADER=/path/to/header.arff
```

#### For TAXI Dataset

```properties
CLASSIFICATION.DECISION_TREE.ARFF_PATH=/path/to/DecisionTreeClassifyHeaderOnly-TAXI.arff
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/DecisionTreeClassify-TAXI.model
CLASSIFICATION.DECISION_TREE.CLASSIFY.RESULT_ATTRIBUTE_INDEX=3
CLASSIFICATION.DECISION_TREE.TRAIN.MODEL_UPDATE_FREQUENCY=300
```

**ARFF File Format**:
```
@RELATION airquality

@ATTRIBUTE timestamp NUMERIC
@ATTRIBUTE source STRING
@ATTRIBUTE temperature NUMERIC
@ATTRIBUTE humidity NUMERIC
@ATTRIBUTE light NUMERIC
@ATTRIBUTE dust NUMERIC
@ATTRIBUTE quality {Excellent,Good,Fair,Poor}

@DATA
```

---

## Prediction Configuration

### Linear Regression

#### For SYS Dataset

```properties
# ARFF header for predictor
PREDICT.LINEAR_REGRESSION.PREDICTOR.ARFF_PATH=/path/to/linearregressionHeaderOnly.arff

# ARFF header for training
PREDICT.LINEAR_REGRESSION.TRAIN.ARFF_PATH=/path/to/linearregressionHeaderOnly.arff

# Trained model file
PREDICT.LINEAR_REGRESSION.MODEL_PATH=/path/to/LR-SYS-Numeric.model

# Field index to use
PREDICT.LINEAR_REGRESSION.USE_MSG_FIELD=-1

# Training: Model update frequency
PREDICT.LINEAR_REGRESSION.TRAIN.MODEL_UPDATE_FREQUENCY=1000
```

#### For TAXI Dataset

```properties
PREDICT.LINEAR_REGRESSION.TRAIN.ARFF_PATH=/path/to/linearregressionHeaderOnly-TAXI.arff
PREDICT.LINEAR_REGRESSION.MODEL_PATH=/path/to/LR-TAXI-Numeric.model
PREDICT.LINEAR_REGRESSION.TRAIN.MODEL_UPDATE_FREQUENCY=300
```

### Simple Linear Regression

```properties
# Field index to use
PREDICT.SIMPLE_LINEAR_REGRESSION.USE_MSG_FIELD=-1

# Window size for training
PREDICT.SIMPLE_LINEAR_REGRESSION.WINDOW_SIZE_TRAIN=10

# Window size for prediction
PREDICT.SIMPLE_LINEAR_REGRESSION.WINDOW_SIZE_PREDICT=10
```

---

## I/O Configuration

### Azure Storage

#### Connection

```properties
# Azure Storage connection string
IO.AZURE_STORAGE_CONN_STR=DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net
```

**Getting Connection String**:
1. Azure Portal → Storage Account → Access Keys
2. Copy "Connection string"

#### Azure Table Storage

```properties
# Table name
IO.AZURE_TABLE.TABLE_NAME=sensordata

# Partition key for queries
IO.AZURE_TABLE.PARTITION_KEY=1

# Row key range for queries
IO.AZURE_TABLE.START_ROW_KEY=1
IO.AZURE_TABLE.END_ROW_KEY=1220000

# Field index to use
IO.AZURE_TABLE.USE_MSG_FIELD=0
```

**Table Structure**:
- `PartitionKey`: Group data (e.g., by sensor ID)
- `RowKey`: Unique identifier within partition
- Additional columns: Your sensor data

#### Azure Blob Storage

```properties
# Container name
IO.AZURE_BLOB.CONTAINER_NAME=mycontainer

# File names for download (comma-separated)
IO.AZURE_BLOB_DOWNLOAD.FILE_NAMES=model1.bin,model2.bin

# File paths for upload (comma-separated)
IO.AZURE_BLOB_UPLOAD.FILE_SOURCE_PATH=/path/to/file1.png,/path/to/file2.png

# Upload directory
IO.AZURE_BLOB_UPLOAD.DIR_NAME=/path/to/upload/dir

# Field index to use
IO.AZURE_BLOB.USE_MSG_FIELD=0
IO.AZURE_BLOB_DOWNLOAD.USE_MSG_FIELD=-1
```

### MQTT

```properties
# MQTT broker URL (format: tcp://host:port)
IO.MQTT_PUBLISH.APOLLO_URL=tcp://broker.example.com:1883

# Username (optional)
IO.MQTT_PUBLISH.APOLLO_USER=admin

# Password (optional)
IO.MQTT_PUBLISH.APOLLO_PASSWORD=secret

# Client identifier
IO.MQTT_PUBLISH.APOLLO_CLIENT=benchmarkPublisher

# Topic name
IO.MQTT_PUBLISH.TOPIC_NAME=sensors/output
```

**Broker Setup**:

For Mosquitto:
```bash
# Install
sudo apt-get install mosquitto mosquitto-clients

# Configure (no auth)
# Edit /etc/mosquitto/mosquitto.conf
allow_anonymous true
listener 1883

# Restart
sudo systemctl restart mosquitto
```

For authentication:
```bash
# Create password file
sudo mosquitto_passwd -c /etc/mosquitto/passwd admin

# Update config
password_file /etc/mosquitto/passwd
allow_anonymous false

# Restart
sudo systemctl restart mosquitto
```

---

## Mathematical Operations

### Pi Calculation (Viète's Formula)

```properties
# Number of iterations
MATH.PI_VIETE.ITERS=1600
```

Higher iterations = more accuracy, but slower computation

---

## Dataset-Specific Configuration

### Multiple Configuration Files

Create separate config files for different datasets:

```bash
tasks.properties          # Generic/SYS
tasks_TAXI.properties     # TAXI dataset
tasks_FIT.properties      # FIT dataset
tasks_CITY.properties     # CITY dataset
tasks_GRID.properties     # GRID dataset
```

### Switching Datasets

Comment/uncomment sections in `tasks.properties`:

```properties
## FOR SYS dataset
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/model-SYS.model

## FOR TAXI dataset
#CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/model-TAXI.model
```

Or use separate files:
```bash
storm jar ... tasks_TAXI.properties
```

---

## Environment-Specific Configuration

### Development

```properties
# tasks-dev.properties
# Use local paths
IO.MQTT_PUBLISH.APOLLO_URL=tcp://localhost:1883
IO.AZURE_STORAGE_CONN_STR=UseDevelopmentStorage=true

# Small test models
CLASSIFICATION.DECISION_TREE.TRAIN.MODEL_UPDATE_FREQUENCY=10
```

### Production

```properties
# tasks-prod.properties
# Use remote services
IO.MQTT_PUBLISH.APOLLO_URL=tcp://prod-broker.example.com:1883
IO.AZURE_STORAGE_CONN_STR=<production-connection-string>

# Larger batches
CLASSIFICATION.DECISION_TREE.TRAIN.MODEL_UPDATE_FREQUENCY=1000
```

---

## Performance Tuning

### Memory Settings

```properties
# For large models or datasets, increase JVM heap
export STORM_JAR_JVM_OPTS="-Xmx8g -Xms8g"
```

### Batch Sizes

Larger batches = better throughput, higher latency:

```properties
# Small batches (lower latency)
AGGREGATE.BLOCK_COUNT.WINDOW_SIZE=5
CLASSIFICATION.DECISION_TREE.TRAIN.MODEL_UPDATE_FREQUENCY=50

# Large batches (higher throughput)
AGGREGATE.BLOCK_COUNT.WINDOW_SIZE=100
CLASSIFICATION.DECISION_TREE.TRAIN.MODEL_UPDATE_FREQUENCY=1000
```

### Statistical Parameters

More accurate = more computation:

```properties
# High accuracy (slower)
AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS=16
FILTER.BLOOM_FILTER_TRAIN.FALSEPOSITIVE_RATIO=0.001

# Moderate accuracy (faster)
AGGREGATE.DISTINCT_APPROX_COUNT.BUCKETS=8
FILTER.BLOOM_FILTER_TRAIN.FALSEPOSITIVE_RATIO=0.01
```

---

## Validation

### Check Configuration

```bash
# Verify all paths exist
for path in $(grep PATH= tasks.properties | cut -d= -f2); do
    if [ ! -f "$path" ]; then
        echo "Missing: $path"
    fi
done
```

### Test Configuration

```python
import java.util.Properties

props = Properties()
with open('tasks.properties') as f:
    props.load(f)

# Check required properties
required = [
    'CLASSIFICATION.DECISION_TREE.MODEL_PATH',
    'FILTER.BLOOM_FILTER.MODEL_PATH',
]

for prop in required:
    if prop not in props:
        print(f"Missing required property: {prop}")
```

---

## Configuration Templates

### Minimal Configuration

```properties
# Minimal tasks.properties for SenML parsing only
PARSE.CSV_SCHEMA_FILEPATH=/path/to/schema.txt
PARSE.META_FIELD_SCHEMA=timestamp,longitude,latitude
PARSE.ID_FIELD_SCHEMA=source
```

### Full ML Configuration

```properties
# Complete ML pipeline configuration
CLASSIFICATION.DECISION_TREE.ARFF_PATH=/path/to/header.arff
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/dt-model.model
CLASSIFICATION.DECISION_TREE.TRAIN.MODEL_UPDATE_FREQUENCY=100

PREDICT.LINEAR_REGRESSION.TRAIN.ARFF_PATH=/path/to/lr-header.arff
PREDICT.LINEAR_REGRESSION.MODEL_PATH=/path/to/lr-model.model
PREDICT.LINEAR_REGRESSION.TRAIN.MODEL_UPDATE_FREQUENCY=100

FILTER.BLOOM_FILTER.MODEL_PATH=/path/to/bloomfilter.model
```

### Cloud-Only Configuration

```properties
# For benchmarks using only Azure services
IO.AZURE_STORAGE_CONN_STR=<your-connection-string>
IO.AZURE_TABLE.TABLE_NAME=sensordata
IO.AZURE_TABLE.PARTITION_KEY=1
IO.AZURE_BLOB.CONTAINER_NAME=models
```

---

## Troubleshooting Configuration

### Common Issues

**Problem**: Property not found
```
Solution: Check spelling and case (properties are case-sensitive)
```

**Problem**: File not found at runtime
```
Solution: Use absolute paths, not relative paths
```

**Problem**: Connection refused (Azure/MQTT)
```
Solution: Verify connection strings and network access
```

**Problem**: Model loading fails
```
Solution: Ensure model file matches library version (Weka 3.6.6)
```

---

## Next Steps

- Review [Dataset Information](07-datasets.md) for input data formats
- See [Getting Started](05-getting-started.md) for running benchmarks
- Check [Architecture](04-architecture.md) to understand how configuration is used
