# RIoTBench Visual Guide

## System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      RIoTBench Architecture                       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    LAYER 1: Data Sources                         │
├──────────────────────────────────────────────────────────────────┤
│  📊 TAXI Dataset  │  🌆 SYS Dataset  │  💪 FIT Dataset  │ ...   │
│  (1.7M events)    │  (2.3M events)   │  (1M events)     │       │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│                LAYER 2: Storm Spouts (Data Ingestion)            │
├──────────────────────────────────────────────────────────────────┤
│  • SampleSpout           • SampleSenMLSpout                      │
│  • MQTTSubscribeSpout    • TimerSpout                           │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│             LAYER 3: Storm Bolts (Processing)                    │
├──────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │ Parse Bolts   │  │ Filter Bolts  │  │  Stats Bolts  │       │
│  │ • SenMLParse  │  │ • BloomFilter │  │ • Kalman      │       │
│  │ • XMLParse    │  │ • RangeFilter │  │ • Interpolate │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                                                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   ML Bolts    │  │   I/O Bolts   │  │   Viz Bolts   │       │
│  │ • DecisionTree│  │ • AzureBlob   │  │ • MultiPlot   │       │
│  │ • LinearReg   │  │ • MQTT        │  │               │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│            LAYER 4: Task Abstraction (Core Logic)                │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌──────────────────────────────────────────────────┐          │
│   │          ITask<T, U> Interface                    │          │
│   │  • setup(Logger, Properties)                      │          │
│   │  • doTask(Map<String, T>) : Float                │          │
│   │  • getLastResult() : U                            │          │
│   │  • tearDown() : float                             │          │
│   └──────────────────────────────────────────────────┘          │
│                         ↓                                         │
│   ┌──────────────────────────────────────────────────┐          │
│   │        AbstractTask<T, U> (Base Class)           │          │
│   │  • Timing instrumentation                        │          │
│   │  • Counter management                             │          │
│   │  • Template method pattern                        │          │
│   └──────────────────────────────────────────────────┘          │
│                         ↓                                         │
│   ┌────────┬────────┬────────┬────────┬────────┬────────┐       │
│   │ Parse  │ Filter │ Stats  │ ML     │  I/O   │  Viz   │       │
│   │ Tasks  │ Tasks  │ Tasks  │ Tasks  │ Tasks  │ Tasks  │       │
│   └────────┴────────┴────────┴────────┴────────┴────────┘       │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│           LAYER 5: External Dependencies                         │
├──────────────────────────────────────────────────────────────────┤
│  📦 Weka ML     │  ☁️ Azure SDK   │  📡 MQTT Client │  📊 XChart │
│  🔢 Commons Math│  🎯 Guava       │  📝 OpenCSV     │           │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│                   LAYER 6: Output & Storage                      │
├──────────────────────────────────────────────────────────────────┤
│  • Sink Bolt (Logging)    • Azure Storage    • MQTT Topics      │
│  • Metrics Collection     • Model Files      • Result Files     │
└──────────────────────────────────────────────────────────────────┘


══════════════════════════════════════════════════════════════════════

## Application Dataflow Diagrams

### ETL (Extract, Transform, Load)

    [CSV/SenML Input]
           ↓
    ┌─────────────┐
    │ SenML Parse │ ─── Parse sensor messages
    └─────────────┘
           ↓
    ┌─────────────┐
    │Range Filter │ ─── Remove outliers
    └─────────────┘
           ↓
    ┌─────────────┐
    │Bloom Filter │ ─── Filter invalid sensors
    └─────────────┘
           ↓
    ┌─────────────┐
    │Interpolation│ ─── Fill missing values
    └─────────────┘
           ↓
    ┌─────────────┐
    │    Join     │ ─── Add metadata
    └─────────────┘
           ↓
    ┌─────────────┐
    │  Annotate   │ ─── Add semantic labels
    └─────────────┘
           ↓
    ┌─────────────┐
    │CSV→SenML    │ ─── Convert format
    └─────────────┘
           ↓
    ┌─────────────┐
    │MQTT Publish │ ─── Publish results
    └─────────────┘

### STATS (Statistical Summarization)

    [Sensor Stream]
           ↓
    ┌─────────────┐
    │Parse+Project│
    └─────────────┘
           ↓
    ┌─────────────┐
    │Bloom Filter │
    └─────────────┘
           ├───────────┬───────────┬───────────┐
           ↓           ↓           ↓           ↓
    ┌──────────┐ ┌──────────┐ ┌──────┐ ┌──────────┐
    │  Kalman  │ │   SLR    │ │ SOM  │ │   DAC    │
    │  Filter  │ │Predictor │ │      │ │  Count   │
    └──────────┘ └──────────┘ └──────┘ └──────────┘
           └───────────┴───────────┴───────────┘
                         ↓
                  ┌─────────────┐
                  │MQTT Publish │
                  └─────────────┘

### TRAIN (Model Training)

    [Timer Trigger]
           ↓
    ┌──────────────────┐
    │Azure Table Query │ ─── Fetch training batch
    └──────────────────┘
           ├──────────────────┬──────────────────┐
           ↓                  ↓                  ↓
    ┌────────────┐   ┌─────────────┐   ┌──────────┐
    │ DT Train   │   │  LR Train   │   │ Annotate │
    └────────────┘   └─────────────┘   └──────────┘
           └──────────────────┴──────────────────┘
                         ↓
                  ┌─────────────┐
                  │ Azure Blob  │ ─── Store models
                  │   Upload    │
                  └─────────────┘
                         ↓
                  ┌─────────────┐
                  │MQTT Publish │ ─── Notify update
                  └─────────────┘

### PRED (Predictive Analytics)

    [Sensor Stream]          [Model Updates]
           ↓                       ↓
    ┌─────────────┐      ┌──────────────────┐
    │ SenML Parse │      │  MQTT Subscribe  │
    └─────────────┘      └──────────────────┘
           ├──────────┐           ↓
           ↓          ↓    ┌─────────────┐
    ┌──────────┐ ┌────────┤Azure Blob   │
    │ DT       │ │  LR    │  Download   │ ─── Fetch new models
    │ Classify │ │ Predict│             │
    └──────────┘ └────────┘└─────────────┘
           └──────────┘
                ↓
         ┌────────────┐
         │Block Window│ ─── Compute actual
         │  Average   │
         └────────────┘
                ↓
         ┌────────────┐
         │   Error    │ ─── Compare prediction
         │ Estimation │     vs actual
         └────────────┘
                ↓
         ┌────────────┐
         │   MQTT     │ ─── Publish results
         │  Publish   │
         └────────────┘


══════════════════════════════════════════════════════════════════════

## Module Organization

riot-bench/
│
├── 📁 modules/
│   │
│   ├── 📁 tasks/                      [Core benchmark logic]
│   │   ├── 📄 pom.xml
│   │   └── 📁 src/
│   │       ├── 📁 main/
│   │       │   ├── 📁 java/
│   │       │   │   └── in.dream_lab.bm.stream_iot.tasks/
│   │       │   │       ├── 🔧 ITask.java
│   │       │   │       ├── 🔧 AbstractTask.java
│   │       │   │       ├── 📂 parse/        [4 tasks]
│   │       │   │       ├── 📂 filter/       [2 tasks]
│   │       │   │       ├── 📂 statistics/   [6 tasks]
│   │       │   │       ├── 📂 predict/      [6 tasks]
│   │       │   │       ├── 📂 io/           [7 tasks]
│   │       │   │       ├── 📂 aggregate/    [2 tasks]
│   │       │   │       └── 📂 visualize/    [1 task]
│   │       │   │
│   │       │   └── 📁 resources/
│   │       │       ├── 📋 tasks.properties
│   │       │       ├── 📋 tasks_TAXI.properties
│   │       │       ├── 🤖 *.model (ML models)
│   │       │       ├── 📊 *.arff (Weka headers)
│   │       │       └── 📄 *.csv (Sample data)
│   │       │
│   │       └── 📁 test/                [Unit tests]
│   │
│   ├── 📁 storm/                       [Storm integration]
│   │   ├── 📄 pom.xml
│   │   └── 📁 src/main/java/
│   │       └── in.dream_lab.bm.stream_iot.storm/
│   │           ├── 📂 bolts/
│   │           │   ├── ETL/
│   │           │   ├── IoTStatsBolt/
│   │           │   ├── IoTPredictionBolts/
│   │           │   └── TRAIN/
│   │           ├── 📂 spouts/
│   │           ├── 📂 sinks/
│   │           ├── 📂 topo/
│   │           │   ├── apps/       [ETL, STATS, TRAIN, PRED]
│   │           │   └── micro/      [Micro-benchmark driver]
│   │           └── 📂 genevents/
│   │
│   └── 📁 distribution/                [Packaging]
│       └── 📄 pom.xml
│
├── 📁 docs/                            [📚 THIS DOCUMENTATION]
│   ├── 📖 README.md
│   ├── 📖 00-summary.md
│   ├── 📖 01-overview.md
│   ├── 📖 02-micro-benchmarks.md
│   ├── 📖 03-application-benchmarks.md
│   ├── 📖 04-architecture.md
│   ├── 📖 05-getting-started.md
│   ├── 📖 06-configuration.md
│   ├── 📖 07-datasets.md
│   └── 📖 08-visual-guide.md (this file)
│
├── 📄 pom.xml                          [Root Maven config]
└── 📄 README.md                        [Quick start]


══════════════════════════════════════════════════════════════════════

## Task Execution Flow

┌────────────────────────────────────────────────────────────────┐
│                    Task Lifecycle                              │
└────────────────────────────────────────────────────────────────┘

1. INITIALIZATION
   ┌─────────────────┐
   │ Topology Submit │
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │  Bolt.prepare() │ ← Called by Storm
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │ task = new Task │
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │ task.setup(...)  │ ← Initialize resources
   └─────────────────┘

2. EXECUTION LOOP
   ┌─────────────────┐
   │ Tuple arrives   │
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │ Bolt.execute()  │
   └────────┬────────┘
            ↓
   ┌─────────────────────────────┐
   │ Convert tuple → Map         │
   └────────┬────────────────────┘
            ↓
   ┌─────────────────────────────┐
   │ result = task.doTask(map)   │
   │                             │
   │  Inside doTask():           │
   │  • sw.resume()              │
   │  • doTaskLogic()            │
   │  • sw.suspend()             │
   │  • counter++                │
   └────────┬────────────────────┘
            ↓
   ┌─────────────────────────────┐
   │ Convert result → tuple      │
   └────────┬────────────────────┘
            ↓
   ┌─────────────────────────────┐
   │ collector.emit(output)      │
   └────────┬────────────────────┘
            ↓
   ┌─────────────────────────────┐
   │ collector.ack(input)        │
   └────────┬────────────────────┘
            ↓
   [Loop back for next tuple]

3. TERMINATION
   ┌─────────────────┐
   │ Topology killed │
   └────────┬────────┘
            ↓
   ┌─────────────────┐
   │ Bolt.cleanup()  │
   └────────┬────────┘
            ↓
   ┌─────────────────────────────┐
   │ avgTime = task.tearDown()   │
   │                             │
   │  Returns: totalTime/counter │
   └─────────────────────────────┘


══════════════════════════════════════════════════════════════════════

## Benchmark Categories Visual

┌─────────────────────────────────────────────────────────────────┐
│                  26 MICRO-BENCHMARKS                            │
└─────────────────────────────────────────────────────────────────┘

📝 PARSE (4)
├─ ANN  Annotate
├─ C2S  CsvToSenML
├─ SML  SenML Parsing
└─ XML  XML Parsing

🔍 FILTER (2)
├─ BLF  Bloom Filter
└─ RGF  Range Filter

📊 STATISTICAL (6)
├─ ACC  Accumulator
├─ AVG  Average
├─ DAC  Distinct Approx Count
├─ KAL  Kalman Filter
├─ SOM  Second Order Moment
└─ INP  Interpolation

🤖 PREDICTIVE (6)
├─ DTC  Decision Tree Classify
├─ DTT  Decision Tree Train
├─ MLR  Multi-var Linear Regression
├─ MLT  Multi-var Linear Regression Train
└─ SLR  Sliding Linear Regression

💾 I/O (7)
├─ ABD  Azure Blob Download
├─ ABU  Azure Blob Upload
├─ ATL  Azure Table Lookup
├─ ATR  Azure Table Range
├─ ATI  Azure Table Insert
├─ MQP  MQTT Publish
└─ MQS  MQTT Subscribe

📈 VISUALIZATION (1)
└─ PLT  Multi-Line Plot

┌─────────────────────────────────────────────────────────────────┐
│              4 APPLICATION BENCHMARKS                           │
└─────────────────────────────────────────────────────────────────┘

🔄 ETL    Extract, Transform, Load
          8-stage pipeline for data ingestion

📊 STATS  Statistical Summarization
          Parallel real-time analytics

🎓 TRAIN  Model Training
          Online machine learning

🔮 PRED   Predictive Analytics
          Real-time prediction with dynamic models


══════════════════════════════════════════════════════════════════════

## Dataset Overview

📊 TAXI Dataset (Transportation)
    Size: 1.7M events | Frequency: 1 min | Duration: 7 days
    ├─ GPS trajectories
    ├─ Speed & direction
    └─ Occupancy status
    Use: Traffic analysis, trip prediction

🌆 SYS Dataset (Smart City)
    Size: 2.3M events | Frequency: 5 min | Duration: 60 days
    ├─ Temperature & humidity
    ├─ Light & dust
    └─ Air quality
    Use: Environmental monitoring, quality forecasting

💪 FIT Dataset (Fitness)
    Size: 1M events | Frequency: 1 sec | Duration: Multiple sessions
    ├─ Accelerometer (x,y,z)
    ├─ Heart rate
    └─ Skin temperature
    Use: Activity recognition, health monitoring

🏙️ CITY Dataset (Urban Infrastructure)
    Size: 500K events | Frequency: Varies | Duration: 30 days
    ├─ Traffic sensors
    ├─ Parking sensors
    └─ Street lighting
    Use: Smart city management

⚡ GRID Dataset (Smart Grid)
    Size: 800K events | Frequency: 15 min | Duration: 30 days
    ├─ Voltage & current
    ├─ Power consumption
    └─ Power factor
    Use: Energy demand forecasting


══════════════════════════════════════════════════════════════════════

## Storm Grouping Strategies

┌────────────────────────────────────────────────────────────────┐
│              Storm Tuple Grouping Patterns                     │
└────────────────────────────────────────────────────────────────┘

SHUFFLE GROUPING (Random Distribution)
    Spout                    Bolts
     [S] ─────┬─────────→  [B1]  Stateless operations
              ├─────────→  [B2]  Equal load distribution
              └─────────→  [B3]  Good for parsing

FIELDS GROUPING (Key-based Routing)
    Bolt                     Bolts
     [B] ─────────────────→ [B1]  sensor_1, sensor_4
          ↘──────────────→ [B2]  sensor_2, sensor_5
           ↘─────────────→ [B3]  sensor_3, sensor_6
    
    Same key always goes to same bolt
    Required for stateful operations

ALL GROUPING (Broadcast)
    Bolt                     Bolts
     [B] ─────┬──────────→ [B1]  All receive
              ├──────────→ [B2]  same tuple
              └──────────→ [B3]  (e.g., config updates)

GLOBAL GROUPING (Single Instance)
    Bolt                     Bolts
     [B] ──────────────────→[B1]  All tuples
              ×────────────×[B2]  to one bolt
              ×────────────×[B3]  (e.g., aggregation)


══════════════════════════════════════════════════════════════════════

## Performance Characteristics

┌────────────────────────────────────────────────────────────────┐
│           Latency vs Throughput by Category                   │
└────────────────────────────────────────────────────────────────┘

         THROUGHPUT (events/sec)
         LOW        MEDIUM       HIGH
         │           │           │
PARSE    │           ██████████████  Very high throughput
FILTER   │           ████████████    High throughput
STATS    │      ██████████           Medium throughput
ML       │   ████                    Lower throughput
I/O      ██                          Low throughput

         LATENCY (ms)
         │
   LOW   ██ Parse, Filter           < 1ms
         ████ Statistics             1-10ms
  MED    ████████ ML                 10-100ms
  HIGH   ████████████ I/O            > 100ms


Resource Usage:
┌────────┬─────────┬────────────┬────────────┐
│Category│   CPU   │   Memory   │   Network  │
├────────┼─────────┼────────────┼────────────┤
│ Parse  │  Low    │    Low     │    Low     │
│ Filter │Very Low │  Low-Med   │    Low     │
│ Stats  │ Medium  │   Medium   │    Low     │
│ ML     │  High   │    High    │    Low     │
│ I/O    │  Low    │    Low     │    High    │
└────────┴─────────┴────────────┴────────────┘


══════════════════════════════════════════════════════════════════════

## Technology Stack

┌────────────────────────────────────────────────────────────────┐
│                   Technology Dependencies                       │
└────────────────────────────────────────────────────────────────┘

CORE
    ☕ Java 7+
    📦 Maven 3.0.4+

STREAM PROCESSING
    🌪️ Apache Storm 1.0.1

MACHINE LEARNING
    🤖 Weka 3.6.6
    🔢 Apache Commons Math 3.5

CLOUD & I/O
    ☁️ Azure SDK 4.0.0
    📡 Eclipse Paho MQTT 1.0.2
    📝 OpenCSV 3.3

UTILITIES
    🎯 Google Guava 19.0
    📊 XChart 3.2.0
    🕐 Joda-Time 2.7
    📋 JSON-simple 1.1

BUILD & TEST
    🔨 Maven Assembly Plugin
    ✅ JUnit 4.11


══════════════════════════════════════════════════════────════════════

This visual guide provides diagrams and visual representations to help
understand the RIoTBench architecture, dataflows, and organization.

For detailed information, refer to the corresponding documentation files.
