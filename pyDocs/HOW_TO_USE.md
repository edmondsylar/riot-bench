# PyRIoTBench - How to Use Guide

**Complete guide for using PyRIoTBench benchmark suite**

This document provides comprehensive instructions on how to install, configure, and run PyRIoTBench benchmarks using both CLI and Python API.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Python API Usage](#python-api-usage)
- [Available Benchmarks](#available-benchmarks)
- [Configuration](#configuration)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before using PyRIoTBench, ensure you have:

- **Python 3.10 or higher** installed
- **pip** package manager
- **Git** (for development installation)
- Basic understanding of streaming/batch processing concepts

Check your Python version:
```bash
python --version  # Should be 3.10 or higher
```

---

## Installation

### Option 1: Basic Installation (Recommended for Users)

Install PyRIoTBench from PyPI:

```bash
pip install pyriotbench
```

### Option 2: Installation with All Features

Include all optional dependencies (Apache Beam, ML libraries, Azure, MQTT):

```bash
pip install pyriotbench[all]
```

### Option 3: Feature-Specific Installation

Install only specific features:

```bash
# Machine Learning tasks
pip install pyriotbench[ml]

# Apache Beam integration
pip install pyriotbench[beam]

# Azure storage tasks
pip install pyriotbench[azure]

# MQTT tasks
pip install pyriotbench[mqtt]
```

### Option 4: Development Installation

For contributing or local development:

```bash
# Clone the repository
git clone https://github.com/edmondsylar/riot-bench.git

# Navigate to pyriotbench directory
cd riot-bench/pyriotbench

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Verify Installation

After installation, verify it works:

```bash
pyriotbench --version
pyriotbench --help
```

---

## Quick Start

### 1. List Available Benchmarks

See all available benchmark tasks:

```bash
# Simple list
pyriotbench list-tasks

# Detailed list with descriptions
pyriotbench list-tasks --verbose
```

### 2. Prepare Input Data

Create a simple text file for testing:

```bash
echo -e "line 1\nline 2\nline 3" > input.txt
```

### 3. Run Your First Benchmark

Run the simplest benchmark (no-operation):

```bash
pyriotbench run noop input.txt
```

This will process the file and display results to stdout.

### 4. Save Output to File

```bash
pyriotbench run noop input.txt -o output.txt
```

---

## CLI Usage

The CLI provides three main commands: `list-tasks`, `run`, `benchmark`, and `batch`.

### Command: list-tasks

List all available benchmark tasks.

**Basic Usage:**
```bash
pyriotbench list-tasks
```

**With Descriptions:**
```bash
pyriotbench list-tasks --verbose
```

---

### Command: run

Execute a single benchmark task on an input file.

**Syntax:**
```bash
pyriotbench run <task_name> <input_file> [OPTIONS]
```

**Options:**
- `-o, --output FILE` - Output file path (default: stdout)
- `-c, --config FILE` - Configuration file (YAML or properties)
- `--progress/--no-progress` - Enable/disable progress reporting (default: enabled)
- `--progress-interval N` - Progress report interval in records (default: 1000)
- `-v, --verbose` - Enable verbose logging

**Examples:**

```bash
# Basic execution (output to stdout)
pyriotbench run noop input.txt

# Save output to file
pyriotbench run noop input.txt -o output.txt

# With configuration file
pyriotbench run senml_parse data.csv -c config.yaml -o parsed.txt

# With progress reporting every 5000 records
pyriotbench run senml_parse data.csv -o output.txt --progress-interval 5000

# Verbose mode for debugging
pyriotbench run kalman_filter sensor_data.txt -v -o filtered.txt
```

---

### Command: benchmark

Run a benchmark with detailed metrics collection.

**Syntax:**
```bash
pyriotbench benchmark <task_name> <input_file> -m <metrics_file> [OPTIONS]
```

**Note:** The `--metrics` flag is **required** for benchmark mode.

**Options:**
- `-m, --metrics FILE` - Metrics output file (JSON format) - **REQUIRED**
- `-o, --output FILE` - Output file path
- `-c, --config FILE` - Configuration file
- `--progress-interval N` - Progress report interval

**Examples:**

```bash
# Basic benchmarking with metrics
pyriotbench benchmark noop input.txt -m metrics.json

# With output and metrics
pyriotbench benchmark noop input.txt -o output.txt -m metrics.json

# Benchmark SenML parsing with configuration
pyriotbench benchmark senml_parse data.csv \
    -o parsed.txt \
    -m metrics.json \
    -c config.yaml \
    --progress-interval 1000
```

**Metrics Output:**
The metrics file contains:
- Total execution time
- Throughput (records/second)
- Latency statistics (min, max, avg, p50, p95, p99)
- Error count and rate
- Task-specific metrics

---

### Command: batch

Process multiple input files in batch mode.

**Syntax:**
```bash
pyriotbench batch <task_name> <input_files...> -o <output_dir> [OPTIONS]
```

**Options:**
- `-o, --output DIR` - Output directory - **REQUIRED**
- `-m, --metrics DIR` - Metrics directory (optional)
- `-c, --config FILE` - Configuration file

**Examples:**

```bash
# Process multiple files
pyriotbench batch noop file1.txt file2.txt file3.txt -o output_dir/

# With wildcards
pyriotbench batch noop data/*.txt -o output_dir/

# With metrics for each file
pyriotbench batch noop file1.txt file2.txt \
    -o output_dir/ \
    -m metrics_dir/

# Batch with configuration
pyriotbench batch senml_parse data/*.csv \
    -o parsed_dir/ \
    -m metrics_dir/ \
    -c config.yaml
```

**Note:** Output files will have the same name as input files.

---

### Getting Help

```bash
# General help
pyriotbench --help

# Command-specific help
pyriotbench run --help
pyriotbench benchmark --help
pyriotbench batch --help
```

---

## Python API Usage

You can also use PyRIoTBench programmatically in your Python code.

### Basic Task Usage

```python
from pyriotbench import create_task

# Create task instance
task = create_task("noop")

# Setup (initialize task)
task.setup()

# Process data
result = task.execute("some data")

# Check timing and status
last_result = task.get_last_result()
print(last_result)  # Shows result with execution time

# Cleanup
avg_time = task.tear_down()
print(f"Average execution time: {avg_time:.3f}ms")
```

### Advanced Task Usage with Configuration

```python
from pyriotbench.tasks.parse import SenMLParse
import logging

# Create task
task = SenMLParse()

# Setup with configuration
logger = logging.getLogger('pyriotbench')
config = {
    'PARSE.SENML_ENABLED': True,
    'PARSE.VALIDATION': True
}
task.setup(logger, config)

# Process SenML data
data = {"D": '{"bn": "sensor1", "e": [{"n": "temp", "v": 23.5}]}'}
result = task.do_task(data)

# Get result
parsed = task.get_last_result()
print(f"Parsed: {parsed}")

# Cleanup
avg_time = task.tear_down()
print(f"Average time: {avg_time:.3f}ms")
```

### Processing Multiple Records

```python
from pyriotbench import create_task

task = create_task("kalman_filter")
task.setup()

# Process stream of data
data_stream = [1.2, 1.5, 1.3, 1.8, 1.6]

for value in data_stream:
    result = task.execute(value)
    print(f"Filtered value: {result}")

# Get statistics
avg_time = task.tear_down()
print(f"Average execution time: {avg_time:.3f}ms")
```

### List Available Tasks

```python
from pyriotbench import list_tasks

# Get all task names
tasks = list_tasks()
print(f"Available tasks: {tasks}")
```

### Custom Task Creation

```python
from pyriotbench import BaseTask, register_task

@register_task("my_custom_task")
class MyCustomTask(BaseTask):
    """Custom task that processes data."""
    
    def do_task(self, data):
        # Your processing logic here
        return data.upper()

# Use your custom task
task = create_task("my_custom_task")
task.setup()
result = task.execute("hello world")
print(result)  # "HELLO WORLD"
task.tear_down()
```

---

## Available Benchmarks

PyRIoTBench includes 26+ micro-benchmarks organized by category:

### Parse Tasks
- **`senml_parse`** - Parse SenML (Sensor Markup Language) JSON format
- **`csv_to_senml_parse`** - Convert CSV to SenML format
- *(XML parsing and annotation tasks also available)*

### Filter Tasks
- **`bloom_filter_check`** - Bloom filter membership testing
- **`range_filter_check`** - Range-based filtering

### Statistics Tasks
- **`kalman_filter`** - Kalman filter for sensor data smoothing
- **`accumulator`** - Accumulate values over time
- **`interpolation`** - Linear interpolation
- **`second_order_moment`** - Calculate second-order statistical moments

### Aggregate Tasks
- **`block_window_average`** - Sliding window average
- **`distinct_approx_count`** - Approximate distinct count

### Predictive Tasks
- **`decision_tree_classify`** - Decision tree classification
- *(Linear regression and other ML tasks also available)*

### Math Tasks
- **`pi_by_viete`** - Calculate π using Viete's formula

### Basic Tasks
- **`noop`** - No operation (baseline/testing)

### I/O Tasks
*(Azure Blob/Table Storage, MQTT publishing/subscribing tasks available with respective feature installations)*

To see the complete list with descriptions:
```bash
pyriotbench list-tasks --verbose
```

---

## Configuration

PyRIoTBench supports configuration through YAML or properties files.

### Configuration File Format

**YAML Configuration (config.yaml):**
```yaml
name: my_benchmark
log_level: INFO
progress_interval: 1000

# Platform configuration
platform_config:
  platform: standalone
  parallelism: 4

# Task-specific configuration
tasks:
  - task_name: senml_parse
    enabled: true
    config_params:
      PARSE.SENML_ENABLED: true
      PARSE.VALIDATION: true
  
  - task_name: kalman_filter
    enabled: true
    config_params:
      STATISTICS.KALMAN.PROCESS_NOISE: 0.1
      STATISTICS.KALMAN.MEASUREMENT_NOISE: 0.5
```

**Properties Configuration (config.properties):**
```properties
# Parse configuration
PARSE.SENML_ENABLED=true
PARSE.VALIDATION=true

# Statistics configuration
STATISTICS.KALMAN.PROCESS_NOISE=0.1
STATISTICS.KALMAN.MEASUREMENT_NOISE=0.5

# Filter configuration
FILTER.BLOOM.SIZE=10000
FILTER.BLOOM.HASH_FUNCTIONS=3
```

### Using Configuration Files

```bash
# With YAML config
pyriotbench run senml_parse data.csv -c config.yaml -o output.txt

# With properties config
pyriotbench run kalman_filter sensor.txt -c config.properties -o filtered.txt
```

### Common Configuration Parameters

**Parse Tasks:**
- `PARSE.SENML_ENABLED` - Enable SenML parsing (boolean)
- `PARSE.VALIDATION` - Enable validation (boolean)

**Filter Tasks:**
- `FILTER.BLOOM.SIZE` - Bloom filter size (integer)
- `FILTER.BLOOM.HASH_FUNCTIONS` - Number of hash functions (integer)
- `FILTER.RANGE.MIN` - Minimum value for range filter (float)
- `FILTER.RANGE.MAX` - Maximum value for range filter (float)

**Statistics Tasks:**
- `STATISTICS.KALMAN.PROCESS_NOISE` - Process noise covariance (float)
- `STATISTICS.KALMAN.MEASUREMENT_NOISE` - Measurement noise covariance (float)
- `STATISTICS.WINDOW.SIZE` - Window size for aggregation (integer)

**Predictive Tasks:**
- `PREDICT.MODEL_PATH` - Path to trained model file (string)
- `PREDICT.FEATURES` - Feature column names (list)

---

## Common Use Cases

### Use Case 1: Process Sensor Data

```bash
# Parse SenML sensor data
pyriotbench run senml_parse sensors.json -o parsed.txt

# Apply Kalman filter for noise reduction
pyriotbench run kalman_filter parsed.txt -o filtered.txt

# Calculate statistics
pyriotbench run block_window_average filtered.txt -o stats.txt
```

### Use Case 2: Benchmark Performance

```bash
# Run benchmark with metrics
pyriotbench benchmark senml_parse large_dataset.csv \
    -o output.txt \
    -m metrics.json \
    --progress-interval 10000

# View metrics
cat metrics.json | jq '.summary'
```

### Use Case 3: Batch Processing

```bash
# Process all CSV files in a directory
pyriotbench batch senml_parse data/*.csv \
    -o processed/ \
    -m metrics/ \
    -c config.yaml
```

### Use Case 4: Pipeline with Python API

```python
from pyriotbench import create_task

# Create pipeline
parser = create_task("senml_parse")
filter_task = create_task("kalman_filter")
accumulator = create_task("accumulator")

# Setup tasks
parser.setup()
filter_task.setup()
accumulator.setup()

# Process data through pipeline
raw_data = '{"bn": "sensor1", "e": [{"n": "temp", "v": 23.5}]}'
parsed = parser.execute(raw_data)
filtered = filter_task.execute(parsed)
result = accumulator.execute(filtered)

print(f"Final result: {result}")

# Cleanup
parser.tear_down()
filter_task.tear_down()
accumulator.tear_down()
```

### Use Case 5: Custom Configuration

```bash
# Create custom config
cat > my_config.yaml << EOF
tasks:
  - task_name: kalman_filter
    config_params:
      STATISTICS.KALMAN.PROCESS_NOISE: 0.05
      STATISTICS.KALMAN.MEASUREMENT_NOISE: 0.3
EOF

# Run with custom config
pyriotbench run kalman_filter sensor_data.txt -c my_config.yaml -o output.txt
```

---

## Troubleshooting

### Issue: Module Not Found

**Symptom:**
```
ModuleNotFoundError: No module named 'pyriotbench'
```

**Solution:**
Ensure PyRIoTBench is properly installed:
```bash
pip install pyriotbench
# Or for development
pip install -e ".[dev]"
```

---

### Issue: Missing Optional Dependencies

**Symptom:**
```
ModuleNotFoundError: No module named 'pydantic'
ModuleNotFoundError: No module named 'apache_beam'
```

**Solution:**
Install with all dependencies:
```bash
pip install pyriotbench[all]
```

Or install specific features:
```bash
pip install pyriotbench[ml]      # For ML tasks
pip install pyriotbench[beam]    # For Beam tasks
pip install pyriotbench[azure]   # For Azure tasks
```

---

### Issue: Task Not Found

**Symptom:**
```
Task 'my_task' not found
```

**Solution:**
- Check available tasks: `pyriotbench list-tasks`
- Verify task name spelling (use exact name from list)
- Ensure required feature dependencies are installed

---

### Issue: File Not Found

**Symptom:**
```
Error: Invalid value for 'input_file': Path 'file.txt' does not exist.
```

**Solution:**
- Verify the input file path is correct
- Use absolute paths if relative paths don't work
- Check file permissions

---

### Issue: Slow Performance

**Symptom:**
Processing is slower than expected.

**Solution:**
- Use `--no-progress` to disable progress reporting for faster execution
- Increase `--progress-interval` to reduce overhead
- Check input data size and format
- Consider batch processing for multiple files

---

### Issue: Permission Denied on Output

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: 'output.txt'
```

**Solution:**
- Check write permissions on output directory
- Ensure output file is not open in another program
- Use a different output location

---

### Issue: Configuration Not Applied

**Symptom:**
Configuration parameters don't seem to take effect.

**Solution:**
- Verify configuration file format (YAML vs properties)
- Check parameter names match exactly (case-sensitive)
- Use `-v` flag for verbose logging to see configuration loading
- Ensure configuration file path is correct

---

### Getting Help

If you encounter issues not covered here:

1. **Check Verbose Logging:**
   ```bash
   pyriotbench run task_name input.txt -v
   ```

2. **Check GitHub Issues:**
   Visit: https://github.com/edmondsylar/riot-bench/issues

3. **View Documentation:**
   - Main README: `pyriotbench/README.md`
   - Quick Start: `pyriotbench/QUICKSTART.md`
   - Architecture: `pyDocs/01-ARCHITECTURE-DETAILS.md`

4. **Run Examples:**
   ```bash
   cd pyriotbench/examples
   python 03_cli_usage.py
   ```

---

## Additional Resources

### Documentation
- **Main README**: Overview and architecture
- **QUICKSTART.md**: Creating custom tasks
- **pyDocs/**: Detailed planning and architecture docs
- **examples/**: Usage examples and sample code

### Links
- **GitHub Repository**: https://github.com/edmondsylar/riot-bench
- **Original RIoTBench**: https://github.com/anshuiisc/riot-bench
- **Research Paper**: http://onlinelibrary.wiley.com/doi/10.1002/cpe.4257/abstract

---

## Summary

**Basic Workflow:**
1. Install PyRIoTBench: `pip install pyriotbench[all]`
2. List tasks: `pyriotbench list-tasks`
3. Run benchmark: `pyriotbench run <task> <input> -o <output>`
4. Collect metrics: `pyriotbench benchmark <task> <input> -m metrics.json`
5. Batch process: `pyriotbench batch <task> file*.txt -o output_dir/`

**Key Commands:**
- `list-tasks` - List available benchmarks
- `run` - Execute single benchmark
- `benchmark` - Execute with metrics collection
- `batch` - Process multiple files

**Configuration:**
- YAML or properties files
- Task-specific parameters
- Pass with `-c config.yaml`

**Python API:**
- `create_task(name)` - Create task instance
- `task.setup()` - Initialize
- `task.execute(data)` - Process data
- `task.tear_down()` - Cleanup

---

**Ready to benchmark?** Start with `pyriotbench list-tasks` and explore! 🚀

---

**Document Version**: 1.0  
**Last Updated**: October 14, 2025  
**Status**: Complete
