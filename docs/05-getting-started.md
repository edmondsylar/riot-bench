# Getting Started

## Prerequisites

### Software Requirements

- **Java Development Kit (JDK)**: Version 7 or higher
- **Apache Maven**: Version 3.0.4 or higher
- **Apache Storm**: Version 1.0.1 (for cluster deployment)
- **Git**: For cloning the repository

### Optional Requirements

- **Azure Account**: For Azure storage benchmarks
- **MQTT Broker**: For MQTT pub/sub benchmarks (e.g., Mosquitto, Apache Apollo)
- **MySQL**: For SQL-based benchmarks

### System Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4 GB
- Disk: 10 GB free space

**Recommended**:
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 20+ GB free space
- Network: Stable internet connection (for Azure/MQTT benchmarks)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/anshuiisc/riot-bench.git
cd riot-bench
```

### 2. Build the Project

```bash
mvn clean compile package -DskipTests
```

This command:
- Cleans previous builds
- Compiles Java sources
- Packages into JAR files
- Skips unit tests (for faster build)

**Expected Output**:
```
[INFO] ------------------------------------------------------------------------
[INFO] Reactor Summary:
[INFO] 
[INFO] IoT-BM ............................................. SUCCESS
[INFO] IoT-BM-TASKS ....................................... SUCCESS
[INFO] IoT-BM-STORM ....................................... SUCCESS
[INFO] iot-bm-distribution ................................ SUCCESS
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
```

### 3. Locate Build Artifacts

After successful build, find JARs in:

```
modules/storm/target/iot-bm-storm-0.1-jar-with-dependencies.jar
modules/tasks/target/iot-bm-tasks-0.1.jar
```

The `jar-with-dependencies.jar` contains all required dependencies.

---

## Quick Start: Local Mode

### 1. Prepare Configuration

Copy and edit the configuration file:

```bash
cd modules/tasks/src/main/resources/
cp tasks.properties tasks-local.properties
```

Edit `tasks-local.properties` and update paths:

```properties
# Update all file paths to absolute paths on your system
CLASSIFICATION.DECISION_TREE.ARFF_PATH=/absolute/path/to/DecisionTreeClassifyHeaderOnly-SYS.arff
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/absolute/path/to/DecisionTreeClassify-SYS.model
FILTER.BLOOM_FILTER.MODEL_PATH=/absolute/path/to/bloomfilter.model
```

### 2. Prepare Input Data

Use sample data provided:

```bash
cd modules/tasks/src/main/resources/
# Sample files available:
ls *.csv
# SYS_sample_data_senml.csv
# TAXI_sample_data_senml.csv
# FIT_sample_data_senml.csv
```

### 3. Run a Micro-Benchmark

Run a simple micro-benchmark in local mode:

```bash
storm jar modules/storm/target/iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.micro.MicroTopologyDriver \
  L \
  TestMicro \
  modules/tasks/src/main/resources/SYS_sample_data_senml.csv \
  EXP-001 \
  1.0 \
  ./output \
  modules/tasks/src/main/resources/tasks.properties \
  SenMLParse
```

**Argument Breakdown**:
1. `L` - Local mode (vs `C` for cluster)
2. `TestMicro` - Topology name
3. `SYS_sample_data_senml.csv` - Input dataset
4. `EXP-001` - Experiment run ID
5. `1.0` - Scaling factor (event rate multiplier)
6. `./output` - Output directory for logs
7. `tasks.properties` - Configuration file
8. `SenMLParse` - Micro-benchmark task name

### 4. Check Output

```bash
ls output/
# sink-TestMicro-EXP-001-1.0.log
# spout-TestMicro-EXP-001-1.0.log

cat output/sink-TestMicro-EXP-001-1.0.log
```

### 5. Run an Application Benchmark

Run the STATS application:

```bash
storm jar modules/storm/target/iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.IoTStatsTopology \
  L \
  STATS-TEST \
  modules/tasks/src/main/resources/SYS_sample_data_senml.csv \
  EXP-002 \
  1.0 \
  ./output \
  modules/tasks/src/main/resources/tasks.properties
```

---

## Configuration

### Understanding tasks.properties

The `tasks.properties` file contains all benchmark configuration:

```properties
# General format: CATEGORY.SUBCATEGORY.PARAMETER=value

# Parsing configuration
PARSE.CSV_SCHEMA_FILEPATH=/path/to/schema.txt
PARSE.META_FIELD_SCHEMA=timestamp,longitude,latitude

# Filter configuration
FILTER.BLOOM_FILTER.MODEL_PATH=/path/to/bloomfilter.model
FILTER.RANGE_FILTER.VALID_RANGE=temperature:0.7:35.1,humidity:20.3:69.1

# ML configuration
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/path/to/model.model
CLASSIFICATION.DECISION_TREE.ARFF_PATH=/path/to/header.arff

# Statistical configuration
STATISTICS.KALMAN_FILTER.PROCESS_NOISE=0.125
STATISTICS.KALMAN_FILTER.SENSOR_NOISE=0.32

# I/O configuration (optional)
IO.AZURE_STORAGE_CONN_STR=your_connection_string
IO.MQTT_PUBLISH.APOLLO_URL=tcp://localhost:1883
```

### Required Files

Ensure these files exist and paths are correct:

**For SYS Dataset**:
- `DecisionTreeClassifyHeaderOnly-SYS.arff`
- `DecisionTreeClassify-SYS.model`
- `bloomfilter.model`
- `LR-SYS-Numeric.model`

**For TAXI Dataset**:
- `DecisionTreeClassifyHeaderOnly-TAXI.arff`
- `DecisionTreeClassify-TAXI.model`
- `LR-TAXI-Numeric.model`

All these files are included in `modules/tasks/src/main/resources/`.

---

## Running Different Benchmarks

### Micro-Benchmarks

**Template**:
```bash
storm jar <jar-path> \
  in.dream_lab.bm.stream_iot.storm.topo.micro.MicroTopologyDriver \
  <mode> <topo-name> <input-file> <run-id> <scale> <output-dir> <config-file> <task-name>
```

**Available Task Names**:

| Task Name | Description |
|-----------|-------------|
| `SenMLParse` | Parse SenML messages |
| `XMLParse` | Parse XML data |
| `CsvToSenMLParse` | Convert CSV to SenML |
| `Annotate` | Add annotations |
| `BloomFilterCheck` | Check Bloom filter |
| `RangeFilter` | Range filtering |
| `BlockWindowAverage` | Moving average |
| `KalmanFilter` | Kalman filtering |
| `Interpolation` | Value interpolation |
| `DistinctApproxCount` | Distinct count |
| `DecisionTreeClassify` | DT classification |
| `LinearRegressionPredictor` | LR prediction |
| `AzureBlobUpload` | Upload to Azure |
| `MQTTPublish` | Publish to MQTT |

**Examples**:

```bash
# Decision Tree Classification
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.micro.MicroTopologyDriver \
  L DTC-Test data.csv EXP-001 1.0 ./output tasks.properties DecisionTreeClassify

# Kalman Filter
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.micro.MicroTopologyDriver \
  L KF-Test data.csv EXP-002 1.0 ./output tasks.properties KalmanFilter

# Bloom Filter
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.micro.MicroTopologyDriver \
  L BF-Test data.csv EXP-003 1.0 ./output tasks.properties BloomFilterCheck
```

### Application Benchmarks

**ETL Topology**:
```bash
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.ETLTopology \
  L ETL-Test input.csv EXP-ETL 1.0 ./output tasks.properties
```

**STATS Topology**:
```bash
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.IoTStatsTopology \
  L STATS-Test input.csv EXP-STATS 1.0 ./output tasks.properties
```

**TRAIN Topology** (requires Azure Table):
```bash
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.IoTTrainTopologyTAXI \
  L TRAIN-Test timer-input.csv EXP-TRAIN 1.0 ./output tasks_TAXI.properties
```

**PRED Topology** (requires MQTT and Azure):
```bash
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.IoTPredictionTopologyTAXI \
  L PRED-Test input.csv EXP-PRED 1.0 ./output tasks_TAXI.properties
```

---

## Cluster Deployment

### 1. Setup Storm Cluster

Follow Apache Storm documentation to set up a cluster:
- Install and configure ZooKeeper
- Configure Storm Nimbus
- Configure Storm Supervisors

### 2. Submit Topology to Cluster

Change mode from `L` to `C`:

```bash
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.micro.MicroTopologyDriver \
  C \
  TestMicro \
  /path/on/storm/cluster/input.csv \
  EXP-001 \
  1.0 \
  /path/on/storm/cluster/output \
  /path/on/storm/cluster/tasks.properties \
  DecisionTreeClassify
```

**Important**: All file paths must be accessible from Storm worker nodes.

### 3. Monitor Topology

```bash
# List running topologies
storm list

# View topology UI
# Open browser to http://<nimbus-host>:8080

# Check logs
storm logs TestMicro

# Kill topology
storm kill TestMicro
```

### 4. Adjust Parallelism

Edit topology code to increase parallelism:

```java
builder.setBolt("processBolt", new ProcessBolt(props), 10)  // 10 parallel tasks
    .shuffleGrouping("spout");
```

Rebuild and redeploy.

---

## Scaling Input Rate

### Using Scaling Factor

The scaling factor multiplies the input event rate:

```bash
# Normal rate (1.0x)
... 1.0 ...

# Half rate (0.5x) - slower
... 0.5 ...

# Double rate (2.0x) - faster
... 2.0 ...

# 10x rate
... 10.0 ...
```

### Understanding Spout Behavior

The spout reads data and controls emission rate based on:
1. Scaling factor parameter
2. Timestamps in input data
3. Current system time

---

## Analyzing Results

### Log Files

**Spout Log** (`spout-*.log`):
- Event emission timestamps
- Events per second
- Total events emitted

**Sink Log** (`sink-*.log`):
- Event reception timestamps
- Processing results
- End-to-end latency

### Parsing Logs

```bash
# Count total events
wc -l output/sink-*.log

# View first 10 results
head -n 10 output/sink-*.log

# Check for errors
grep ERROR logs/worker-*.log
```

### Performance Metrics

Calculate metrics from logs:

```python
import pandas as pd

# Load sink log
df = pd.read_csv('sink-log.csv', names=['timestamp', 'msgId', 'result'])

# Calculate latency
df['latency'] = df['timestamp'] - df['emit_time']

# Calculate throughput
throughput = len(df) / (df['timestamp'].max() - df['timestamp'].min())

print(f"Average Latency: {df['latency'].mean():.2f} ms")
print(f"Throughput: {throughput:.2f} events/sec")
```

---

## Troubleshooting

### Build Errors

**Problem**: Maven build fails

**Solution**:
```bash
# Clean and rebuild
mvn clean install -DskipTests

# Check Java version
java -version  # Should be 7+

# Check Maven version
mvn -version   # Should be 3.0.4+
```

### Runtime Errors

**Problem**: `ClassNotFoundException`

**Solution**: Use the jar-with-dependencies:
```bash
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar ...
```

**Problem**: `FileNotFoundException` for models/data

**Solution**: Use absolute paths in `tasks.properties`:
```properties
CLASSIFICATION.DECISION_TREE.MODEL_PATH=/absolute/path/to/model.model
```

**Problem**: `NullPointerException` in task

**Solution**: Check that required properties are set:
```bash
# Verify properties file
cat tasks.properties | grep MODEL_PATH
```

### Azure Errors

**Problem**: Azure connection fails

**Solution**:
1. Verify connection string is correct
2. Check network connectivity
3. Ensure Azure account has necessary permissions

**Problem**: Azure Table not found

**Solution**:
```bash
# Create table first using Azure Portal or CLI
az storage table create --name sensordata
```

### MQTT Errors

**Problem**: Cannot connect to MQTT broker

**Solution**:
1. Verify broker is running:
```bash
# For Mosquitto
systemctl status mosquitto
```

2. Check URL format:
```properties
IO.MQTT_PUBLISH.APOLLO_URL=tcp://localhost:1883
# NOT http:// or mqtt://
```

3. Test connection:
```bash
mosquitto_pub -t test -m "hello"
mosquitto_sub -t test
```

### Performance Issues

**Problem**: Low throughput

**Solution**:
1. Increase parallelism in topology
2. Add more Storm workers
3. Check for bottlenecks (I/O, CPU)
4. Optimize JVM settings:
```bash
export STORM_JAR_JVM_OPTS="-Xmx4g -Xms4g"
```

**Problem**: High latency

**Solution**:
1. Reduce batch sizes
2. Optimize task logic
3. Use faster I/O (SSD, local vs remote)
4. Check network latency

---

## Best Practices

### Development

1. **Test Locally First**: Always test in local mode before cluster deployment
2. **Start Small**: Begin with small datasets and low parallelism
3. **Incremental Changes**: Make one change at a time
4. **Use Version Control**: Track configuration changes

### Deployment

1. **Monitor Resources**: Watch CPU, memory, disk usage
2. **Log Rotation**: Enable log rotation to prevent disk fill
3. **Backup Configs**: Keep copies of working configurations
4. **Document Changes**: Note what configurations work best

### Performance Testing

1. **Baseline First**: Run with default settings to establish baseline
2. **Vary One Parameter**: Change one thing at a time
3. **Multiple Runs**: Run each test 3-5 times for consistency
4. **Record Everything**: Log all parameters and results

---

## Example Workflows

### Workflow 1: Test Decision Tree Benchmark

```bash
# 1. Build project
mvn clean package -DskipTests

# 2. Prepare data
cd modules/tasks/src/main/resources/
head -1000 SYS_sample_data_senml.csv > test_data.csv

# 3. Verify configuration
grep DECISION_TREE tasks.properties

# 4. Run benchmark
storm jar ../../storm/target/iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.micro.MicroTopologyDriver \
  L DTC-Test test_data.csv EXP-DTC 1.0 ./output tasks.properties \
  DecisionTreeClassify

# 5. Check results
cat output/sink-DTC-Test-EXP-DTC-1.0.log
```

### Workflow 2: Run Complete ETL Pipeline

```bash
# 1. Prepare full dataset
cp inputFileForTimerSpout-TAXI.csv /data/taxi-full.csv

# 2. Update configuration for TAXI
vi tasks_TAXI.properties

# 3. Run ETL topology
storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
  in.dream_lab.bm.stream_iot.storm.topo.apps.ETLTopology \
  L ETL-TAXI /data/taxi-full.csv EXP-ETL-001 1.0 \
  ./output tasks_TAXI.properties

# 4. Monitor execution
tail -f output/sink-ETL-TAXI-EXP-ETL-001-1.0.log

# 5. Analyze results
python analyze_results.py output/sink-*.log
```

### Workflow 3: Benchmark Comparison

```bash
# Test different scaling factors
for scale in 0.5 1.0 2.0 5.0; do
    storm jar iot-bm-storm-0.1-jar-with-dependencies.jar \
      in.dream_lab.bm.stream_iot.storm.topo.micro.MicroTopologyDriver \
      L Test-$scale data.csv EXP-$scale $scale ./output \
      tasks.properties DecisionTreeClassify
    
    sleep 60  # Wait for completion
done

# Compare results
python compare_throughput.py output/
```

---

## Next Steps

- Review [Configuration Guide](06-configuration.md) for detailed configuration options
- Explore [Dataset Information](07-datasets.md) to understand input data formats
- Read [Micro-Benchmarks](02-micro-benchmarks.md) for specific task details
- Study [Application Benchmarks](03-application-benchmarks.md) for complex dataflows
