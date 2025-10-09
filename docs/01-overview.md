# RIoTBench Overview

## What is RIoTBench?

**RIoTBench** (Real-time IoT Benchmark) is a comprehensive benchmark suite designed to evaluate the performance of **Distributed Stream Processing Systems (DSPS)** in the context of **Internet of Things (IoT)** applications. It was developed by the DREAM Lab at the Indian Institute of Science, Bangalore.

## Purpose and Motivation

### Why RIoTBench?

IoT applications have unique characteristics that differ from traditional big data workloads:

1. **Real-time Processing**: IoT data must be processed with low latency
2. **High Volume**: Millions of sensors generating continuous streams of data
3. **Variety of Operations**: Mix of parsing, filtering, analytics, and machine learning
4. **Stateful Computations**: Many operations require maintaining state across events
5. **External I/O**: Integration with cloud storage, databases, and messaging systems

Existing benchmarks were not designed with these IoT-specific requirements in mind. RIoTBench fills this gap by providing a realistic set of workloads that mirror actual IoT application patterns.

## Key Features

### 1. Comprehensive Coverage

RIoTBench provides **26 micro-benchmarks** and **4 application benchmarks** that cover:

- **Data Parsing**: CSV, XML, SenML (Sensor Markup Language)
- **Filtering**: Bloom filters, range filters
- **Statistical Analytics**: Moving averages, Kalman filters, interpolation
- **Predictive Analytics**: Decision trees, linear regression
- **I/O Operations**: Azure Blob/Table storage, MQTT publish/subscribe
- **Visualization**: Real-time plotting and charting

### 2. Real IoT Datasets

The benchmark includes real-world datasets from multiple domains:

- **TAXI**: Beijing taxi GPS trajectory data
- **SYS**: Smart city air quality sensor data
- **FIT**: Fitness tracking sensor data
- **CITY**: Urban infrastructure monitoring data
- **GRID**: Smart grid energy consumption data

### 3. Modular Design

- **Task Abstraction**: Each benchmark is implemented as a reusable task component
- **Platform Agnostic**: Core task logic is separated from platform-specific code
- **Composable**: Micro-benchmarks can be combined to create complex dataflows

### 4. Apache Storm Integration

RIoTBench provides complete integration with **Apache Storm**, a popular distributed stream processing platform. The implementation includes:

- Pre-built Storm topologies for all benchmarks
- Custom spouts for data ingestion
- Bolts wrapping benchmark tasks
- Logging and metrics collection

## Benchmark Categories

### Micro-Benchmarks (26 Total)

Micro-benchmarks test individual operations in isolation:

| Category | Count | Examples |
|----------|-------|----------|
| **Parse** | 4 | SenML Parse, XML Parse, CSV Parse, Annotate |
| **Filter** | 2 | Bloom Filter, Range Filter |
| **Statistical** | 5 | Average, Kalman Filter, Interpolation, Second Order Moment, Distinct Count |
| **Predictive** | 6 | Decision Tree Classify/Train, Linear Regression Predict/Train |
| **I/O** | 8 | Azure Blob Upload/Download, Azure Table Insert/Query, MQTT Pub/Sub |
| **Visualization** | 1 | Multi-Line Plot |

### Application Benchmarks (4 Total)

Application benchmarks represent complete end-to-end IoT dataflows:

1. **ETL (Extract, Transform, Load)**: Data ingestion and cleaning pipeline
2. **STATS (Statistical Summarization)**: Real-time analytics dashboard
3. **TRAIN (Model Training)**: Online machine learning model training
4. **PRED (Predictive Analytics)**: Real-time prediction using trained models

## Technology Stack

### Programming Language
- **Java 7+**: Core implementation language

### Distributed Stream Processing
- **Apache Storm 1.0.1**: Primary target platform

### Dependencies
- **Apache Commons Math**: Statistical computations
- **Weka 3.6.6**: Machine learning algorithms
- **Azure SDK**: Cloud storage integration
- **Eclipse Paho**: MQTT messaging
- **Google Guava**: Bloom filters and utilities
- **XChart**: Data visualization

### Build System
- **Maven**: Project management and dependency resolution

## Project Structure

```
riot-bench/
├── modules/
│   ├── tasks/              # Core benchmark task implementations
│   │   └── src/
│   │       ├── main/java/  # Task logic (platform-agnostic)
│   │       └── resources/  # Models, schemas, sample data
│   │
│   ├── storm/              # Apache Storm integration
│   │   └── src/
│   │       └── main/java/  # Bolts, Spouts, Topologies
│   │
│   └── distribution/       # Packaging and assembly
│
├── docs/                   # Documentation (this folder)
├── pom.xml                # Root Maven configuration
└── README.md              # Quick start guide
```

## How It Works

### Task Execution Flow

1. **Setup**: Task is initialized with configuration properties
2. **Processing**: For each input event:
   - Timer starts
   - Task logic executes
   - Timer pauses
   - Result is returned
3. **Teardown**: Task finalizes and reports average execution time

### Integration with Storm

```
Spout → Parse Bolt → Filter Bolt → Analytics Bolt → Sink Bolt
  ↓         ↓            ↓              ↓             ↓
(Read)   (Transform)  (Filter)      (Analyze)    (Store/Log)
```

Each bolt wraps a benchmark task and handles:
- Data marshalling from Storm tuples
- Task invocation
- Result emission to downstream bolts
- Error handling and logging

## Performance Metrics

RIoTBench helps measure:

1. **Throughput**: Events processed per second
2. **Latency**: End-to-end processing time
3. **Task Execution Time**: Time spent in individual operations
4. **Scalability**: Performance under varying load
5. **Resource Utilization**: CPU, memory, network usage

## Use Cases

### 1. Platform Comparison
Compare different stream processing platforms (Storm, Flink, Spark Streaming, etc.) using the same workloads.

### 2. Performance Tuning
Identify bottlenecks and optimize configuration for specific workloads.

### 3. Research
Study scheduling algorithms, resource allocation strategies, and fault tolerance mechanisms.

### 4. Education
Learn stream processing concepts through realistic IoT examples.

## Advantages of RIoTBench

✅ **Realistic Workloads**: Based on actual IoT application patterns  
✅ **Real Data**: Uses authentic datasets from multiple domains  
✅ **Comprehensive**: Covers all major IoT processing operations  
✅ **Reproducible**: Consistent workload characteristics  
✅ **Extensible**: Easy to add new tasks or adapt to other platforms  
✅ **Well-Documented**: Detailed papers and implementation guides  

## Limitations

⚠️ **Storm-Centric**: Primary implementation focuses on Apache Storm  
⚠️ **External Dependencies**: Requires Azure accounts for some benchmarks  
⚠️ **Java Only**: No implementations in other languages yet  
⚠️ **Setup Complexity**: Requires proper configuration of models and paths  

## Next Steps

- Read about [Micro-Benchmarks](02-micro-benchmarks.md) to understand individual operations
- Learn about [Application Benchmarks](03-application-benchmarks.md) for complete dataflow examples
- Explore the [Architecture & Design](04-architecture.md) to understand the implementation
- Follow the [Getting Started Guide](05-getting-started.md) to run your first benchmark

## References

1. **Main Paper**: Shukla, A., Chaturvedi, S., & Simmhan, Y. (2017). RIoTBench: A Real-time IoT Benchmark for Distributed Stream Processing Platforms. *Concurrency and Computation: Practice and Experience*, 29(21).

2. **Conference Paper**: Shukla, A., & Simmhan, Y. (2016). Benchmarking Distributed Stream Processing Platforms for IoT Applications. *TPC Technology Conference on Performance Evaluation & Benchmarking (TPCTC)*.

3. **Pre-print**: https://arxiv.org/abs/1701.08530
