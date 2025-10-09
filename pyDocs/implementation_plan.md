# PyRIoTBench Implementation Plan

**Created**: October 9, 2025  
**Status**: Active Development  
**Philosophy**: Time is just a construct - we focus on progress, not deadlines

---

## 🎯 Implementation Strategy

We're porting RIoTBench from Java/Storm to Python with multi-platform support (Beam, Flink, Ray). The key is preserving the brilliant **task abstraction architecture** while modernizing the stack.

---

## 📋 Phase 1: Foundation & Proof of Concept

**Goal**: Core abstractions + 2 working benchmarks + standalone runner

### 1.1 Project Setup
- [ ] Create `pyriotbench` directory structure
- [ ] Setup `pyproject.toml` with dependencies
- [ ] Configure dev tools (black, ruff, mypy, pytest)
- [ ] Initialize git repository
- [ ] Create .gitignore

**Files to Create**:
```
pyriotbench/
├── pyproject.toml
├── README.md
├── .gitignore
├── pyriotbench/
│   └── __init__.py
└── tests/
    └── __init__.py
```

---

### 1.2 Core Task Abstraction
- [ ] `pyriotbench/core/task.py`
  - [ ] ITask Protocol (setup, do_task, get_last_result, tear_down)
  - [ ] BaseTask abstract class with template method
  - [ ] Automatic timing instrumentation
  - [ ] Error handling
  
**Key Pattern**: Template method - child classes only implement `do_task_logic()`

---

### 1.3 Task Registry
- [ ] `pyriotbench/core/registry.py`
  - [ ] TaskRegistry singleton
  - [ ] register() and get() methods
  - [ ] list_tasks() for discovery
  - [ ] @register_task decorator

**Purpose**: Dynamic task loading without manual factory code

---

### 1.4 Configuration System
- [ ] `pyriotbench/core/config.py`
  - [ ] TaskConfig with Pydantic models
  - [ ] Load from YAML
  - [ ] Load from .properties (backward compat)
  - [ ] Load from environment variables
  - [ ] to_flat_dict() for task.setup()

**Improvement**: Type-safe config with validation vs plain properties

---

### 1.5 Metrics & Instrumentation
- [ ] `pyriotbench/core/metrics.py`
  - [ ] TaskMetrics dataclass
  - [ ] Timing statistics (total, count, avg, errors)
  - [ ] Properties for computed values

---

### 1.6 First Benchmark: NoOperation
- [ ] `pyriotbench/tasks/__init__.py`
- [ ] `pyriotbench/tasks/noop.py`
  - [ ] NoOperationTask implementation
  - [ ] @register_task("noop") decorator
  - [ ] do_task_logic() returns 0.0 (success)

**Purpose**: Baseline testing, validate core abstractions work

---

### 1.7 Second Benchmark: SenML Parse
- [ ] `pyriotbench/tasks/parse/__init__.py`
- [ ] `pyriotbench/tasks/parse/senml_parse.py`
  - [ ] SenMLParse implementation
  - [ ] JSON parsing with error handling
  - [ ] Validate SenML structure (bn, e fields)
  - [ ] Store parsed result via _set_last_result()
  - [ ] @register_task("senml_parse")

**Purpose**: First real benchmark with actual computation

---

### 1.8 Standalone Runner
- [ ] `pyriotbench/platforms/__init__.py`
- [ ] `pyriotbench/platforms/standalone/__init__.py`
- [ ] `pyriotbench/platforms/standalone/runner.py`
  - [ ] StandaloneRunner class
  - [ ] run_file() method (process line by line)
  - [ ] Logging setup
  - [ ] Output writing (optional)

**Purpose**: Fast iteration, no distributed framework needed

---

### 1.9 CLI Interface
- [ ] `pyriotbench/cli/__init__.py`
- [ ] `pyriotbench/cli/main.py`
  - [ ] Click-based CLI
  - [ ] `list-tasks` command
  - [ ] `run <task> <input>` command
  - [ ] Config file support (--config)
  - [ ] Output file support (--output)

**Usage**:
```bash
pyriotbench list-tasks
pyriotbench run noop input.txt
pyriotbench run senml_parse data.json --output parsed.txt
```

---

### 1.10 Testing Infrastructure
- [ ] `tests/test_core/__init__.py`
- [ ] `tests/test_core/test_task.py`
  - [ ] Test BaseTask lifecycle
  - [ ] Test timing instrumentation
  - [ ] Test error handling
  
- [ ] `tests/test_core/test_registry.py`
  - [ ] Test task registration
  - [ ] Test task retrieval
  - [ ] Test duplicate registration error
  
- [ ] `tests/test_core/test_config.py`
  - [ ] Test YAML loading
  - [ ] Test properties loading
  - [ ] Test Pydantic validation

- [ ] `tests/test_tasks/__init__.py`
- [ ] `tests/test_tasks/test_noop.py`
  - [ ] Test NoOpTask execution
  
- [ ] `tests/test_tasks/test_senml_parse.py`
  - [ ] Test valid SenML parsing
  - [ ] Test invalid JSON handling
  - [ ] Test result retrieval

- [ ] `tests/fixtures/`
  - [ ] config.yaml
  - [ ] sample_data.txt
  - [ ] sample_senml.json

---

### 1.11 Documentation
- [ ] `pyriotbench/README.md`
  - [ ] Quick start guide
  - [ ] Installation instructions
  - [ ] Example usage
  
- [ ] `examples/01_simple_task.py`
- [ ] `examples/02_senml_parsing.py`
- [ ] `examples/config/example.yaml`

---

### Phase 1 Success Criteria
- [ ] Can run: `pyriotbench run noop input.txt`
- [ ] Can run: `pyriotbench run senml_parse sample.json`
- [ ] All tests pass: `pytest`
- [ ] Type checking passes: `mypy pyriotbench`
- [ ] Linting passes: `ruff check pyriotbench`
- [ ] Code formatted: `black pyriotbench`
- [ ] Test coverage >80%

---

## 📋 Phase 2: Core Benchmarks (5 Tasks)

**Goal**: One representative benchmark per category

### 2.1 Parse Category: DONE
- [x] SenMLParse (completed in Phase 1)

### 2.2 Filter Category: Bloom Filter
- [ ] `pyriotbench/tasks/filter/__init__.py`
- [ ] `pyriotbench/tasks/filter/bloom_filter.py`
  - [ ] BloomFilterCheck implementation
  - [ ] Load pre-trained Bloom filter model
  - [ ] Check membership
  - [ ] Return 1.0 (pass) or None (filtered)
  - [ ] @register_task("bloom_filter")

**Dependencies**: pybloom-live or implement with bitarray

---

### 2.3 Statistics Category: Block Window Average
- [ ] `pyriotbench/tasks/statistics/__init__.py`
- [ ] `pyriotbench/tasks/statistics/average.py`
  - [ ] BlockWindowAverage implementation
  - [ ] Window state management (sum, count)
  - [ ] Emit average when window full
  - [ ] Reset state after emission
  - [ ] @register_task("average")

**Key Feature**: Stateful task with windowing logic

---

### 2.4 Predictive Category: Decision Tree Classify
- [ ] `pyriotbench/tasks/predict/__init__.py`
- [ ] `pyriotbench/tasks/predict/decision_tree_classify.py`
  - [ ] DecisionTreeClassify implementation
  - [ ] Load sklearn model (pickle/joblib)
  - [ ] Parse CSV features
  - [ ] Make prediction
  - [ ] @register_task("decision_tree_classify")

**Dependencies**: scikit-learn

---

### 2.5 I/O Category: Azure Blob Download
- [ ] `pyriotbench/tasks/io/__init__.py`
- [ ] `pyriotbench/tasks/io/azure_blob.py`
  - [ ] AzureBlobDownload implementation
  - [ ] Azure connection setup
  - [ ] Download blob by name
  - [ ] Return blob content
  - [ ] @register_task("azure_blob_download")

**Dependencies**: azure-storage-blob

---

### Phase 2 Success Criteria
- [ ] All 5 category representatives working
- [ ] Bloom filter loads models correctly
- [ ] Block window average maintains state
- [ ] Decision tree makes predictions
- [ ] Azure blob downloads work
- [ ] All tests pass
- [ ] Standalone runner executes all tasks

---

## 📋 Phase 3: Apache Beam Integration

**Goal**: First platform adapter + ETL application

### 3.1 Beam Adapter
- [ ] `pyriotbench/platforms/beam/__init__.py`
- [ ] `pyriotbench/platforms/beam/adapter.py`
  - [ ] TaskDoFn class (beam.DoFn wrapper)
  - [ ] setup() lifecycle
  - [ ] process() method
  - [ ] teardown() lifecycle
  - [ ] Beam metrics integration

### 3.2 Beam Runner
- [ ] `pyriotbench/platforms/beam/runner.py`
  - [ ] BeamPipelineBuilder class
  - [ ] Pipeline construction utilities
  - [ ] Input sources (text file, Kafka, Pub/Sub)
  - [ ] Output sinks

### 3.3 Beam Options
- [ ] `pyriotbench/platforms/beam/options.py`
  - [ ] Beam-specific configuration
  - [ ] Runner selection (Direct, Dataflow, Flink)

### 3.4 ETL Application Benchmark
- [ ] `pyriotbench/applications/__init__.py`
- [ ] `pyriotbench/applications/etl.py`
  - [ ] ETL pipeline: Parse → Filter → Interpolate → Join → Annotate → Publish
  - [ ] TAXI dataset support
  - [ ] Multi-stage pipeline construction

### Phase 3 Success Criteria
- [ ] ETL runs on DirectRunner
- [ ] ETL runs on DataflowRunner (cloud)
- [ ] Throughput measured
- [ ] Results validate against Java version

---

## 📋 Phase 4: Complete All 26 Micro-Benchmarks

### 4.1 Parse (3 remaining)
- [ ] Annotate (ANN)
- [ ] CsvToSenML (C2S)
- [ ] XMLParse (XML)

### 4.2 Filter (1 remaining)
- [ ] RangeFilter (RGF)

### 4.3 Statistics (5 remaining)
- [ ] Accumulator (ACC)
- [ ] DistinctApproxCount (DAC)
- [ ] KalmanFilter (KAL)
- [ ] Interpolation (INP)
- [ ] SecondOrderMoment (SOM)

### 4.4 Predictive (5 remaining)
- [ ] DecisionTreeTrain (DTT)
- [ ] LinearRegressionPredict (MLR)
- [ ] LinearRegressionTrain (MLT)
- [ ] SlidingLinearRegression (SLR)

### 4.5 I/O (6 remaining)
- [ ] AzureBlobUpload (ABU)
- [ ] AzureTableInsert (ATI)
- [ ] AzureTableRangeQuery (ATR)
- [ ] MQTTPublish (MQP)
- [ ] MQTTSubscribe (MQS)

### 4.6 Visualization (1 remaining)
- [ ] MultiLinePlot (PLT)

### Phase 4 Success Criteria
- [ ] All 26 benchmarks implemented
- [ ] All pass unit tests
- [ ] All work with Beam adapter
- [ ] Documentation complete

---

## 📋 Phase 5: Additional Platforms

### 5.1 PyFlink Adapter
- [ ] `pyriotbench/platforms/flink/__init__.py`
- [ ] `pyriotbench/platforms/flink/adapter.py`
  - [ ] TaskMapFunction class
  - [ ] open() lifecycle
  - [ ] map() method
  - [ ] close() lifecycle

### 5.2 Ray Adapter
- [ ] `pyriotbench/platforms/ray/__init__.py`
- [ ] `pyriotbench/platforms/ray/adapter.py`
  - [ ] TaskActor class
  - [ ] Ray remote wrapper

### Phase 5 Success Criteria
- [ ] ETL runs on PyFlink
- [ ] ETL runs on Ray
- [ ] Performance comparison across platforms

---

## 📋 Phase 6: Application Benchmarks

### 6.1 STATS Application
- [ ] `pyriotbench/applications/stats.py`
  - [ ] Parallel statistics computation
  - [ ] Multiple aggregation windows

### 6.2 TRAIN Application
- [ ] `pyriotbench/applications/train.py`
  - [ ] Batch model training
  - [ ] Model checkpointing

### 6.3 PRED Application
- [ ] `pyriotbench/applications/predict.py`
  - [ ] Real-time prediction pipeline
  - [ ] Model loading/serving

### Phase 6 Success Criteria
- [ ] All 4 applications work on Beam
- [ ] Results match Java versions
- [ ] Documentation complete

---

## 📋 Phase 7: Production Polish

### 7.1 Performance Optimization
- [ ] Profile hot paths
- [ ] Optimize serialization
- [ ] Add caching where appropriate

### 7.2 Testing & CI/CD
- [ ] Comprehensive unit tests
- [ ] Integration tests
- [ ] Performance regression tests
- [ ] GitHub Actions CI

### 7.3 Documentation
- [ ] API documentation (Sphinx)
- [ ] User guide
- [ ] Migration guide (Java → Python)
- [ ] Performance comparison report

### 7.4 Packaging
- [ ] PyPI package
- [ ] Docker images
- [ ] Helm charts for Kubernetes

---

## 🎯 Current Focus

**Active Phase**: Phase 1 - Foundation  
**Current Task**: Project Setup  
**Next Milestone**: NoOpTask + SenMLParse working in standalone mode

---

## 📊 Progress Overview

| Phase | Status | Completed | Total | Progress |
|-------|--------|-----------|-------|----------|
| **Phase 1** | 🔄 In Progress | 0 | 11 tasks | 0% |
| **Phase 2** | ⏳ Pending | 0 | 5 tasks | 0% |
| **Phase 3** | ⏳ Pending | 0 | 4 tasks | 0% |
| **Phase 4** | ⏳ Pending | 0 | 21 tasks | 0% |
| **Phase 5** | ⏳ Pending | 0 | 2 tasks | 0% |
| **Phase 6** | ⏳ Pending | 0 | 3 tasks | 0% |
| **Phase 7** | ⏳ Pending | 0 | 4 tasks | 0% |
| **Total** | - | 0 | 50 tasks | 0% |

---

## 🔍 Quick Reference

### Project Structure (Target)
```
pyriotbench/
├── pyproject.toml
├── README.md
├── pyriotbench/
│   ├── __init__.py
│   ├── core/           # ITask, BaseTask, Registry, Config
│   ├── tasks/          # 26 micro-benchmarks
│   ├── platforms/      # Beam, Flink, Ray, Standalone
│   ├── applications/   # ETL, STATS, TRAIN, PRED
│   └── cli/            # Command-line interface
├── tests/              # Unit and integration tests
├── examples/           # Usage examples
└── docs/               # Sphinx documentation
```

### Key Commands (Once Implemented)
```bash
# List tasks
pyriotbench list-tasks

# Run benchmark
pyriotbench run <task_name> <input_file>

# With config
pyriotbench run senml_parse data.json --config config.yaml

# With output
pyriotbench run average stream.txt --output results.txt

# Testing
pytest                          # Run all tests
pytest tests/test_core/         # Run specific tests
pytest --cov=pyriotbench        # With coverage

# Type checking & linting
mypy pyriotbench
ruff check pyriotbench
black pyriotbench
```

---

## 📝 Notes

- **Philosophy**: Progress over deadlines - focus on quality implementations
- **Testing First**: Write tests alongside code, not after
- **Type Safety**: Use mypy strict mode, type hints everywhere
- **Documentation**: Update docs as we go, not at the end
- **Git Commits**: Frequent, small commits with clear messages

---

**Last Updated**: October 9, 2025  
**Maintained By**: Development Team  
**Reference**: See pyDocs folder for detailed planning documents
