# PyRIoTBench: Visual Architecture Summary

**Quick Reference**: Visual diagrams and decision trees for the Python port

---

## 🎯 Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────────────┐
│                        PYRIOTBENCH ARCHITECTURE                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 1: BENCHMARKS (Platform-Agnostic)                             │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│  │ Parse  │ │ Filter │ │ Stats  │ │Predict │ │  I/O   │ │ Visual │ │
│  │ (4)    │ │ (2)    │ │ (6)    │ │ (6)    │ │ (7)    │ │ (1)    │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ │
│                      26 Micro-Benchmarks                              │
│                    All implement ITask protocol                       │
└──────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ ITask Protocol
                                    │ (setup, do_task, teardown)
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 2: CORE ABSTRACTIONS (Portability Layer)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   ITask      │  │  BaseTask    │  │ TaskRegistry │               │
│  │  Protocol    │  │  Template    │  │   Factory    │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└──────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ Platform Adapters
                                    │ (Beam, Flink, Ray)
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 3: PLATFORM ADAPTERS (Framework Integration)                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │ TaskDoFn   │  │TaskMapFunc │  │ TaskActor  │  │Standalone  │    │
│  │  (Beam)    │  │  (Flink)   │  │   (Ray)    │  │  Runner    │    │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 4: STREAMING PLATFORMS                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Apache Beam    │  │  PyFlink        │  │  Ray            │     │
│  │  (Primary)      │  │  (Secondary)    │  │  (Secondary)    │     │
│  │                 │  │                 │  │                 │     │
│  │ • DirectRunner  │  │ • Local Mode    │  │ • Distributed   │     │
│  │ • DataflowRunner│  │ • Cluster Mode  │  │ • Multi-node    │     │
│  │ • FlinkRunner   │  │                 │  │                 │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Task Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      TASK LIFECYCLE                              │
└─────────────────────────────────────────────────────────────────┘

   User Initiates Pipeline
            │
            ▼
   ┌─────────────────┐
   │  Platform Setup │  ← Beam/Flink creates workers
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │  Task Creation  │  ← task = TaskClass()
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │  setup()        │  ← Load config, models, initialize state
   └────────┬────────┘
            │
            ▼
        ╔═══════════════════╗
        ║  Processing Loop  ║
        ╚═══════════════════╝
            │
            ├──────────────┐
            │              │
            ▼              │
   ┌─────────────────┐    │
   │  Element In     │    │
   └────────┬────────┘    │
            │              │
            ▼              │
   ┌─────────────────┐    │  Repeat for each
   │  do_task()      │    │  element in stream
   │  ┌───────────┐  │    │
   │  │Start Timer│  │    │
   │  └─────┬─────┘  │    │
   │        ▼        │    │
   │  ┌───────────┐  │    │
   │  │Task Logic │  │    │  ← Child class implements
   │  └─────┬─────┘  │    │
   │        ▼        │    │
   │  ┌───────────┐  │    │
   │  │Stop Timer │  │    │
   │  └─────┬─────┘  │    │
   │        ▼        │    │
   │  ┌───────────┐  │    │
   │  │ Return    │  │    │
   │  │ Result    │  │    │
   │  └─────┬─────┘  │    │
   └────────┼────────┘    │
            │              │
            ▼              │
   ┌─────────────────┐    │
   │  Element Out    │    │
   └────────┬────────┘    │
            │              │
            ├──────────────┘
            │
            ▼
        Stream Ends
            │
            ▼
   ┌─────────────────┐
   │  tear_down()    │  ← Emit metrics, cleanup
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │  Platform       │  ← Worker shutdown
   │  Cleanup        │
   └─────────────────┘
```

---

## 🏗️ Module Organization

```
pyriotbench/
│
├─── core/                          [LAYER 1: Abstractions]
│    ├── task.py                    • ITask protocol
│    │                              • BaseTask template
│    ├── registry.py                • TaskRegistry
│    │                              • @register_task decorator
│    ├── config.py                  • Configuration management
│    │                              • Pydantic models
│    └── metrics.py                 • TaskMetrics dataclass
│
├─── tasks/                         [LAYER 2: Benchmarks]
│    ├── parse/
│    │   ├── annotate.py            [ANN]  Add metadata
│    │   ├── csv_to_senml.py        [C2S]  CSV → SenML
│    │   ├── senml_parse.py         [SML]  Parse SenML JSON
│    │   └── xml_parse.py           [XML]  Parse XML
│    │
│    ├── filter/
│    │   ├── bloom_filter.py        [BLF]  Probabilistic filter
│    │   └── range_filter.py        [RGF]  Range check
│    │
│    ├── statistics/
│    │   ├── accumulator.py         [ACC]  Window accumulation
│    │   ├── average.py             [AVG]  Moving average
│    │   ├── distinct_count.py      [DAC]  HyperLogLog
│    │   ├── kalman_filter.py       [KAL]  Noise filtering
│    │   ├── interpolation.py       [INP]  Fill missing values
│    │   └── second_moment.py       [SOM]  Variance
│    │
│    ├── predict/
│    │   ├── decision_tree_classify.py    [DTC]  DT classification
│    │   ├── decision_tree_train.py       [DTT]  DT training
│    │   ├── linear_regression_predict.py [MLR]  LR prediction
│    │   ├── linear_regression_train.py   [MLT]  LR training
│    │   └── sliding_linear_regression.py [SLR]  Window LR
│    │
│    ├── io/
│    │   ├── azure_blob.py          [ABD, ABU]  Blob storage
│    │   ├── azure_table.py         [ATI, ATR]  Table storage
│    │   └── mqtt.py                [MQP, MQS]  MQTT pub/sub
│    │
│    └── visualize/
│        └── plot.py                [PLT]  Real-time charts
│
├─── platforms/                     [LAYER 3: Adapters]
│    ├── beam/
│    │   ├── adapter.py             • TaskDoFn
│    │   ├── runner.py              • Pipeline builder
│    │   └── options.py             • Beam config
│    │
│    ├── flink/
│    │   ├── adapter.py             • TaskMapFunction
│    │   ├── runner.py              • Job builder
│    │   └── options.py             • Flink config
│    │
│    ├── ray/
│    │   ├── adapter.py             • TaskActor
│    │   └── runner.py              • Ray pipeline
│    │
│    └── standalone/
│        └── runner.py              • File-based runner
│
├─── applications/                  [LAYER 4: Topologies]
│    ├── etl.py                     8-stage data pipeline
│    ├── stats.py                   Parallel analytics
│    ├── train.py                   Online learning
│    └── predict.py                 Real-time inference
│
└─── cli/                           [User Interface]
     └── main.py                    Command-line tool
```

---

## 🔀 Decision Tree: Which Platform?

```
                    Starting PyRIoTBench
                            │
                            ▼
                  ┌──────────────────┐
                  │ What's your goal?│
                  └────────┬─────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   ┌─────────┐       ┌─────────┐       ┌─────────┐
   │ Testing │       │Research │       │Production│
   │ Develop │       │Benchmark│       │Deployment│
   └────┬────┘       └────┬────┘       └────┬────┘
        │                 │                  │
        ▼                 ▼                  ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │ STANDALONE  │   │    BEAM     │   │    CLOUD    │
   │   Runner    │   │ DirectRunner│   │   Platform  │
   └─────────────┘   └─────────────┘   └─────────────┘
        │                 │                  │
        ▼                 ▼                  ▼
   • Fast iteration  • Local testing   • GCP: Dataflow
   • No cluster      • Full features   • AWS: Kinesis
   • Easy debug      • Compare results • Azure: Stream Analytics
   • Unit tests      • Publications    • Flink cluster
                                        • Ray cluster


Need maximum        Need true           Need advanced
  simplicity?      portability?       stream features?
      │                 │                     │
      ▼                 ▼                     ▼
  Standalone        Apache Beam           PyFlink
   Runner          (Primary Choice)      (Secondary)
      │                 │                     │
      • Files           • Multi-runner        • Sophisticated state
      • No deps         • Cloud-native        • Event time
      • Testing         • Batch+Stream        • Low latency
                        • Best docs           • Performance
```

---

## 📊 Implementation Priority Matrix

```
┌────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION PHASES                        │
└────────────────────────────────────────────────────────────────┘

PHASE 1 (Weeks 1-2): Foundation ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░ 50%
├─ Core abstractions (ITask, BaseTask)
├─ Task registry
├─ Configuration system
├─ Standalone runner
└─ NoOpTask + 1 benchmark

PHASE 2 (Weeks 3-4): Core Benchmarks ▓▓▓▓▓▓▓▓▓░░░░░░░ 40%
├─ SenMLParse [Parse]
├─ BloomFilter [Filter]
├─ Average [Statistics]
├─ DecisionTreeClassify [Predict]
└─ AzureBlobDownload [I/O]

PHASE 3 (Weeks 5-6): Beam Integration ▓▓▓▓▓▓░░░░░ 30%
├─ TaskDoFn adapter
├─ Pipeline builder
├─ Beam metrics
└─ ETL application

PHASE 4 (Weeks 7-10): All Benchmarks ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 70%
├─ Complete Parse (4)
├─ Complete Filter (2)
├─ Complete Statistics (6)
├─ Complete Predict (6)
├─ Complete I/O (7)
└─ Complete Visualize (1)

PHASE 5 (Weeks 11-12): Multi-Platform ▓▓▓▓░░░ 25%
├─ PyFlink adapter
├─ Ray adapter
└─ Platform comparison

PHASE 6 (Weeks 13-14): Applications ▓▓▓▓░░░ 25%
├─ STATS topology
├─ TRAIN topology
└─ PRED topology

PHASE 7 (Weeks 15-16): Polish ▓▓▓░░░ 15%
├─ Performance tuning
├─ Documentation
├─ CI/CD setup
└─ PyPI package

Legend: ▓ Weeks of work  ░ Buffer time
```

---

## 🎨 Task State Management Pattern

```
┌──────────────────────────────────────────────────────────────┐
│              STATELESS vs STATEFUL TASKS                      │
└──────────────────────────────────────────────────────────────┘

STATELESS TASKS                    STATEFUL TASKS
(No memory between events)         (Accumulate across events)

┌─────────────────┐                ┌─────────────────┐
│  Parse (SML)    │                │  Average (AVG)  │
│  ┌───────────┐  │                │  ┌───────────┐  │
│  │ Event 1   │  │                │  │ Event 1   │  │
│  │  Parse    │  │                │  │  sum += v │  │
│  │  → JSON   │  │                │  │  cnt++    │  │
│  └───────────┘  │                │  └─────┬─────┘  │
│                 │                │        │        │
│  ┌───────────┐  │                │  ┌─────▼─────┐  │
│  │ Event 2   │  │                │  │ Event 2   │  │
│  │  Parse    │  │                │  │  sum += v │  │
│  │  → JSON   │  │                │  │  cnt++    │  │
│  └───────────┘  │                │  └─────┬─────┘  │
│                 │                │        │        │
│  Each event     │                │  ┌─────▼─────┐  │
│  independent    │                │  │ Window    │  │
│                 │                │  │ Complete? │  │
│                 │                │  └─────┬─────┘  │
│                 │                │        │        │
│                 │                │        ▼        │
│                 │                │  ┌───────────┐  │
│                 │                │  │Emit avg   │  │
│                 │                │  │Reset state│  │
│                 │                │  └───────────┘  │
└─────────────────┘                └─────────────────┘

IMPLEMENTATION                     IMPLEMENTATION

class SenMLParse(BaseTask):        class BlockWindowAverage(BaseTask):
    def do_task_logic(self, data):     # Class-level (immutable config)
        json_str = data["D"]            _window_size = 100
        parsed = json.loads(json_str)   
        return 1.0                      def __init__(self):
                                            # Instance-level (mutable state)
# No state needed!                       self.sum = 0.0
                                            self.count = 0
                                        
                                        def do_task_logic(self, data):
                                            value = float(data["D"])
                                            self.sum += value
                                            self.count += 1
                                            
                                            if self.count >= self._window_size:
                                                avg = self.sum / self.count
                                                self.sum = 0.0  # Reset
                                                self.count = 0
                                                return avg
                                            return None
```

---

## 🔄 Adapter Pattern Visualization

```
┌──────────────────────────────────────────────────────────────────┐
│           HOW ADAPTERS ENABLE PORTABILITY                         │
└──────────────────────────────────────────────────────────────────┘

                      Same Task Code
                   ┌──────────────────┐
                   │ BloomFilterCheck │
                   │                  │
                   │ def do_task():   │
                   │   return 1.0     │
                   └────────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  TaskDoFn   │ │TaskMapFunc  │ │  TaskActor  │
    │   (Beam)    │ │  (Flink)    │ │   (Ray)     │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           ▼               ▼               ▼
    Beam.DoFn.process   Flink.MapFunction  Ray.remote.method
           │               │               │
           ▼               ▼               ▼
    PCollection         DataStream      ObjectRef
           │               │               │
           ▼               ▼               ▼
    ┌──────────────────────────────────────────┐
    │         Distributed Execution             │
    │  Worker 1   Worker 2   Worker 3  ...     │
    └──────────────────────────────────────────┘

BEAM ADAPTER                FLINK ADAPTER
─────────────               ──────────────
class TaskDoFn(DoFn):       class TaskMapFunction(MapFunction):
    def setup(self):            def open(self, context):
        self.task = Task()          self.task = Task()
        self.task.setup(...)        self.task.setup(...)
    
    def process(self, elem):    def map(self, value):
        data = {"D": elem}          data = {"D": value}
        return self.task            return self.task
               .do_task(data)              .do_task(data)
```

---

## 📈 Performance Comparison Strategy

```
┌──────────────────────────────────────────────────────────────┐
│         JAVA vs PYTHON PERFORMANCE VALIDATION                 │
└──────────────────────────────────────────────────────────────┘

BENCHMARK METRICS

                    Java/Storm       Python/Beam      Acceptable?
                    ──────────       ────────────     ───────────
Throughput          10K events/s     8K events/s      ✅ (80%)
Latency (p50)       5ms              6ms              ✅ (120%)
Latency (p95)       15ms             20ms             ✅ (133%)
Memory              2GB              2.5GB            ✅ (125%)

VALIDATION PROCESS

1. Run Java ETL ──▶ Measure ──▶ Baseline Results
                                 ├─ Throughput
                                 ├─ Latency
                                 └─ Memory

2. Run Python ETL ──▶ Measure ──▶ Python Results
                                  ├─ Throughput
                                  ├─ Latency
                                  └─ Memory

3. Compare ──▶ Python/Java Ratio
              ├─ Throughput: ≥ 70%  ✅
              ├─ Latency: ≤ 150%    ✅
              └─ Memory: ≤ 150%     ✅

4. Correctness ──▶ Compare Outputs
                  └─ ML predictions must match
                     (within numerical precision)

OPTIMIZATION IF NEEDED
──────────────────────
• Profile hot paths (cProfile)
• Optimize data structures
• Use NumPy for math
• Cython for critical loops
• Async I/O for network
```

---

## 🎯 Success Criteria Dashboard

```
┌──────────────────────────────────────────────────────────────┐
│                   PROJECT SUCCESS METRICS                     │
└──────────────────────────────────────────────────────────────┘

FUNCTIONAL
══════════
[▓▓▓▓▓▓▓▓▓░] 90%  All 26 micro-benchmarks implemented
[▓▓▓▓▓▓▓▓▓░] 90%  All 4 application benchmarks working
[▓▓▓▓▓▓▓▓▓▓] 100% Same results as Java (deterministic tasks)
[▓▓▓▓▓▓▓▓░░] 80%  ML predictions match Java (within 5%)

PERFORMANCE
═══════════
[▓▓▓▓▓▓▓▓░░] 80%  Throughput ≥ 70% of Java
[▓▓▓▓▓▓▓░░░] 70%  Latency ≤ 150% of Java
[▓▓▓▓▓▓▓▓░░] 80%  Memory ≤ 150% of Java

PORTABILITY
═══════════
[▓▓▓▓▓▓▓▓▓▓] 100% Same task code for all platforms
[▓▓▓▓▓▓▓▓▓░] 90%  Runs on Beam (Direct, Dataflow)
[▓▓▓▓▓▓▓▓░░] 80%  Runs on PyFlink
[▓▓▓▓▓▓░░░░] 60%  Runs on Ray

QUALITY
═══════
[▓▓▓▓▓▓▓▓░░] 80%  Test coverage > 80%
[▓▓▓▓▓▓▓▓▓▓] 100% Type hints on all APIs
[▓▓▓▓▓▓▓▓▓▓] 100% Passes mypy strict
[▓▓▓▓▓▓▓▓▓░] 90%  Documentation complete

TIMELINE
════════
[▓▓░░░░░░░░] 20%  Phase 1: Foundation (2 weeks)
[░░░░░░░░░░] 0%   Phase 2: Core benchmarks (2 weeks)
[░░░░░░░░░░] 0%   Phase 3: Beam integration (2 weeks)
[░░░░░░░░░░] 0%   Phase 4: All benchmarks (4 weeks)
[░░░░░░░░░░] 0%   Phase 5: Multi-platform (2 weeks)
[░░░░░░░░░░] 0%   Phase 6: Applications (2 weeks)
[░░░░░░░░░░] 0%   Phase 7: Polish (2 weeks)

Overall Progress: [▓░░░░░░░░░] 10% (Planning complete)
```

---

## 📋 Quick Reference: File Locations

```
┌──────────────────────────────────────────────────────────────┐
│                    WHERE TO FIND THINGS                       │
└──────────────────────────────────────────────────────────────┘

NEED TO...                          → LOOK IN...
──────────────────────────────────────────────────────────────
Understand overall plan             → 00-PORTING-PLAN.md
Learn architecture patterns         → 01-ARCHITECTURE-DETAILS.md
Start implementing                  → 02-PHASE1-PROTOTYPE.md
See visual diagrams                 → 03-VISUAL-SUMMARY.md (this file)
Quick navigation                    → README.md

TASK IMPLEMENTATIONS                → pyriotbench/tasks/
├─ Parsing tasks                    → pyriotbench/tasks/parse/
├─ Filtering tasks                  → pyriotbench/tasks/filter/
├─ Statistical tasks                → pyriotbench/tasks/statistics/
├─ ML tasks                         → pyriotbench/tasks/predict/
├─ I/O tasks                        → pyriotbench/tasks/io/
└─ Visualization                    → pyriotbench/tasks/visualize/

CORE ABSTRACTIONS                   → pyriotbench/core/
├─ Task interface                   → pyriotbench/core/task.py
├─ Registry                         → pyriotbench/core/registry.py
├─ Configuration                    → pyriotbench/core/config.py
└─ Metrics                          → pyriotbench/core/metrics.py

PLATFORM ADAPTERS                   → pyriotbench/platforms/
├─ Apache Beam                      → pyriotbench/platforms/beam/
├─ PyFlink                          → pyriotbench/platforms/flink/
├─ Ray                              → pyriotbench/platforms/ray/
└─ Standalone                       → pyriotbench/platforms/standalone/

TESTS                               → tests/
├─ Core tests                       → tests/test_core/
├─ Task tests                       → tests/test_tasks/
└─ Integration tests                → tests/test_integration/

JAVA REFERENCE                      → Original RIoTBench
├─ Task interface                   → modules/tasks/.../ITask.java
├─ Base task                        → modules/tasks/.../AbstractTask.java
├─ Storm adapter                    → modules/storm/.../BaseTaskBolt.java
└─ All 26 benchmarks                → modules/tasks/.../tasks/
```

---

**This visual guide complements the detailed planning documents. Use it as a quick reference when implementing!**

**Last Updated**: October 9, 2025  
**Status**: Planning complete, ready for implementation

