# Phase 5: Multi-Platform Integration - Kickoff

**Started**: October 12, 2025 (Evening)  
**Goal**: Add PyFlink and Ray platform adapters to enable benchmarking across 3+ streaming platforms  
**Strategy**: Leverage proven Beam integration patterns to rapidly add PyFlink and Ray support

---

## 🎯 Mission Statement

**Enable PyRIoTBench to run on multiple streaming platforms (Apache Beam, PyFlink, Ray) without modifying task implementations.**

This validates our core architectural decision: the ITask protocol truly enables platform-agnostic benchmarking.

---

## 📊 Current State (Phase 5 Entry Point)

### Completed Phases ✅
- ✅ **Phase 1**: Foundation (11/11 tasks - 100%)
- ✅ **Phase 2**: Core Benchmarks (4/5 tasks - 80%, Azure deferred)
- ✅ **Phase 3**: Beam Integration (4/4 tasks - 100%)
- ⏳ **Phase 4**: All Benchmarks (7/21 tasks - 33% - IN PROGRESS)

### Available Benchmarks (13 tasks ready for multi-platform)
1. ✅ NoOperation - Baseline benchmark
2. ✅ SenMLParse - IoT data parsing
3. ✅ BloomFilterCheck - Probabilistic membership testing
4. ✅ KalmanFilter - Stateful noise reduction
5. ✅ DecisionTreeClassify - ML classification
6. ✅ BlockWindowAverage - Windowed aggregation
7. ✅ Accumulator - Windowed data accumulation
8. ✅ Interpolation - Missing value interpolation
9. ✅ SecondOrderMoment - Variance/surprise detection
10. ✅ DistinctApproxCount - Cardinality estimation
11. ✅ PiByViete - Mathematical computation (Viète's formula)
12. ✅ RangeFilterCheck - Sensor value validation
13. ✅ CsvToSenMLParse - CSV to SenML conversion

**Diversity**: 7 categories covered (noop, parse, filter, statistics, aggregate, predict, math)

### Existing Platform Adapters
- ✅ **Standalone**: StandaloneRunner (direct Python execution)
- ✅ **Apache Beam**: BeamTaskDoFn + BeamRunner (88-93% coverage)

---

## 🎯 Phase 5 Goals

### Task 5.1: PyFlink Adapter (Week 1)
**Deliverables**:
- [ ] Install PyFlink: `pip install apache-flink`
- [ ] Create `pyriotbench/platforms/flink/__init__.py`
- [ ] Create `pyriotbench/platforms/flink/adapter.py` - FlinkTaskMapFunction
- [ ] Create `pyriotbench/platforms/flink/runner.py` - FlinkRunner
- [ ] Test with 5+ benchmarks
- [ ] Write 15+ integration tests
- [ ] Add CLI commands: `pyriotbench flink run-file`, `flink run-batch`
- [ ] Documentation: examples/05_flink_integration.py

**Success Criteria**:
- ✅ At least 5 benchmarks run successfully on PyFlink
- ✅ 80%+ test coverage on adapter code
- ✅ Performance metrics collected and comparable
- ✅ Stateful tasks work correctly (KalmanFilter, BlockWindowAverage)
- ✅ CLI integration working

### Task 5.2: Ray Adapter (Week 2)
**Deliverables**:
- [ ] Install Ray: `pip install ray`
- [ ] Create `pyriotbench/platforms/ray/__init__.py`
- [ ] Create `pyriotbench/platforms/ray/adapter.py` - Ray actor wrapper
- [ ] Create `pyriotbench/platforms/ray/runner.py` - RayRunner
- [ ] Test with 5+ benchmarks
- [ ] Write 15+ integration tests
- [ ] Add CLI commands: `pyriotbench ray run-file`, `ray run-batch`
- [ ] Documentation: examples/06_ray_integration.py

**Success Criteria**:
- ✅ At least 5 benchmarks run successfully on Ray
- ✅ 80%+ test coverage on adapter code
- ✅ Performance metrics collected and comparable
- ✅ Distributed execution working
- ✅ CLI integration working

---

## 🏗️ Architecture Design (Reuse Beam Patterns)

### Proven Pattern from Phase 3 (Beam)
```
ITask (interface)
  ↓
BeamTaskDoFn (DoFn wrapper)
  ↓
BeamRunner (pipeline construction)
  ↓
DirectRunner (local execution)
```

**Key Learnings**:
- ✅ DoFn wrapper handles lifecycle (setup/process/teardown)
- ✅ Metrics collected via platform counters
- ✅ None filtering for windowed tasks
- ✅ Per-worker task instantiation (thread-safe)

### PyFlink Pattern (To Implement)
```
ITask (interface)
  ↓
FlinkTaskMapFunction (MapFunction wrapper)
  ↓
FlinkRunner (job construction)
  ↓
LocalStreamEnvironment (local execution)
```

**PyFlink Considerations**:
- Use DataStream API (lower-level, like Beam)
- MapFunction for stateless tasks
- KeyedProcessFunction for stateful tasks
- Flink state backend for persistence
- Flink metrics for counters

### Ray Pattern (To Implement)
```
ITask (interface)
  ↓
RayTaskActor (Ray actor wrapper)
  ↓
RayRunner (pipeline construction)
  ↓
Ray local cluster (local execution)
```

**Ray Considerations**:
- Use Ray actors for task execution
- Ray object store for data passing
- Ray metrics for monitoring
- Parallel task execution
- Fault tolerance via Ray

---

## 📦 Dependencies to Add

### PyFlink
```toml
[project.optional-dependencies]
flink = [
    "apache-flink>=1.18.0",
]
```

### Ray
```toml
[project.optional-dependencies]
ray = [
    "ray>=2.9.0",
]
```

### Combined Multi-Platform
```toml
[project.optional-dependencies]
all-platforms = [
    "apache-beam[gcp]>=2.53.0",
    "apache-flink>=1.18.0",
    "ray>=2.9.0",
]
```

---

## 🧪 Testing Strategy

### Test Pyramid for Each Platform

**Unit Tests** (per adapter):
- Task wrapping/unwrapping
- Lifecycle management (setup/process/teardown)
- Metrics collection
- Error handling

**Integration Tests** (per platform):
- Run with NoOperation (baseline)
- Run with stateless task (SenMLParse)
- Run with stateful task (KalmanFilter)
- Run with ML task (DecisionTreeClassify)
- Run with windowed task (BlockWindowAverage)
- Batch processing (multiple files)
- Metrics aggregation

**Cross-Platform Tests**:
- Same benchmark on all 3 platforms
- Compare metrics (throughput, latency)
- Verify results consistency
- Performance benchmarking

---

## 📈 Success Metrics

### Phase 5 Complete When:
- ✅ PyFlink adapter implemented with 80%+ coverage
- ✅ Ray adapter implemented with 80%+ coverage
- ✅ 5+ benchmarks run on each platform (15+ total platform-task combos)
- ✅ 30+ new tests passing (15 per adapter)
- ✅ CLI supports all 3 platforms
- ✅ Performance comparable across platforms (within 2x)
- ✅ Documentation and examples complete

### Overall Progress Impact:
- Phase 5: 0% → 100% (2/2 tasks)
- Overall: 50% (25/50) → 54% (27/50)

---

## 🚀 Kickoff Checklist

### Pre-Implementation Research ✅
- [x] Review PyFlink DataStream API documentation
- [x] Review Ray Core API documentation
- [x] Study Beam adapter implementation patterns
- [x] Identify reusable patterns

### Environment Setup (Next)
- [ ] Install PyFlink locally
- [ ] Install Ray locally
- [ ] Verify installations
- [ ] Test simple PyFlink job
- [ ] Test simple Ray job

### Implementation Order (Next)
1. **PyFlink First** (simpler, more similar to Beam)
   - Streaming engine like Beam
   - Similar concepts (DataStream, operators)
   - Mature Python API
   
2. **Ray Second** (different paradigm)
   - Actor-based model (different from Beam/Flink)
   - More flexible, less structured
   - Excellent for distributed Python

---

## 🎓 Learning Resources

### PyFlink
- [PyFlink DataStream Tutorial](https://nightlies.apache.org/flink/flink-docs-master/docs/dev/python/datastream_tutorial/)
- [PyFlink Examples](https://github.com/apache/flink/tree/master/flink-python/pyflink/examples)
- [Flink State Management](https://nightlies.apache.org/flink/flink-docs-master/docs/dev/datastream/fault-tolerance/state/)

### Ray
- [Ray Core Walkthrough](https://docs.ray.io/en/latest/ray-core/walkthrough.html)
- [Ray Actors](https://docs.ray.io/en/latest/ray-core/actors.html)
- [Ray Tasks](https://docs.ray.io/en/latest/ray-core/tasks.html)

---

## 🎯 Next Immediate Steps

1. **Install PyFlink** (5 min)
   ```bash
   cd pyriotbench
   pip install apache-flink
   ```

2. **Create Flink Directory Structure** (2 min)
   ```bash
   mkdir -p pyriotbench/platforms/flink
   touch pyriotbench/platforms/flink/__init__.py
   touch pyriotbench/platforms/flink/adapter.py
   touch pyriotbench/platforms/flink/runner.py
   ```

3. **Test PyFlink Installation** (5 min)
   - Run simple "hello world" PyFlink job
   - Verify LocalStreamEnvironment works

4. **Start FlinkTaskMapFunction Implementation** (2 hours)
   - Model after BeamTaskDoFn
   - Implement open(), map(), close() methods
   - Add metrics collection

5. **Iterate and Test** (ongoing)

---

**Status**: Phase 5 kickoff complete! Ready to implement PyFlink adapter.  
**Next**: Install PyFlink and create directory structure.  
**Target**: PyFlink adapter complete by end of week.
