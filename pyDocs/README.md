# PyRIoTBench Planning Documentation

**Purpose**: Comprehensive planning and architecture documentation for porting RIoTBench from Java/Storm to Python

**Status**: Planning Phase  
**Created**: October 9, 2025

---

## 📚 Documentation Index

| Document | Purpose | Audience | Status |
|----------|---------|----------|--------|
| **[00-PORTING-PLAN.md](00-PORTING-PLAN.md)** | Master porting strategy, roadmap, risk analysis | Everyone | ✅ Complete |
| **[01-ARCHITECTURE-DETAILS.md](01-ARCHITECTURE-DETAILS.md)** | Deep dive into architecture patterns to preserve/improve | Developers | ✅ Complete |
| **[02-PHASE1-PROTOTYPE.md](02-PHASE1-PROTOTYPE.md)** | Concrete implementation guide for first prototype | Developers | ✅ Complete |
| **[03-VISUAL-SUMMARY.md](03-VISUAL-SUMMARY.md)** | Visual diagrams and quick reference | Everyone | ✅ Complete |
| **[04-KEY-DECISIONS.md](04-KEY-DECISIONS.md)** | Architecture Decision Records (ADRs) | Architects | ✅ Complete |

---

## 🎯 Quick Start

### For Project Managers
→ Read **00-PORTING-PLAN.md** 
- Executive summary
- Timeline (16 weeks)
- Resource requirements
- Success metrics

### For Architects
→ Read **01-ARCHITECTURE-DETAILS.md**
- Why RIoTBench is portable
- Key patterns to preserve
- Proposed improvements
- State management strategies

### For Developers
→ Read **02-PHASE1-PROTOTYPE.md**
- Concrete code examples
- Project structure
- Day-by-day implementation plan
- Testing strategy

### For Quick Reference
→ Read **03-VISUAL-SUMMARY.md**
- Architecture diagrams
- Decision trees
- Visual guides
- File location reference

### For Decision Rationale
→ Read **04-KEY-DECISIONS.md**
- Why we chose Python 3.10+
- Why Apache Beam
- Why scikit-learn over Weka
- All major design decisions

---

## 🏗️ What Makes RIoTBench Special?

RIoTBench has a **brilliant modular architecture** that makes it extremely portable:

### 1. **Task Abstraction** 
Platform-agnostic `ITask` interface:
- No Storm/Flink/Beam dependencies
- Simple lifecycle: `setup()` → `doTask()` → `tearDown()`
- Tasks are pure computation units

### 2. **Adapter Pattern**
Platform-specific adapters wrap tasks:
- `BaseTaskBolt` for Storm (Java)
- `TaskDoFn` for Beam (Python)
- `TaskMapFunction` for Flink (Python)
- Same task code runs everywhere

### 3. **Configuration System**
Externalized properties:
- No hardcoded values
- Same config for all platforms
- Easy to tune for experiments

### 4. **Clean State Management**
Clear separation:
- Static: Shared configuration (immutable)
- Instance: Per-task state (mutable)
- Thread-safe initialization

---

## 🎯 Porting Goals

### Must Preserve ✅
1. **Portability**: Task code platform-agnostic
2. **Modularity**: Clear separation of concerns
3. **Extensibility**: Easy to add new benchmarks
4. **Comparability**: Results match Java version

### Improvements 🚀
1. **Multi-Platform**: Beam, Flink, Ray, Standalone
2. **Modern Libraries**: scikit-learn, PyTorch, async I/O
3. **Type Safety**: Type hints + Pydantic validation
4. **Observability**: OpenTelemetry metrics
5. **Developer Experience**: Better docs, testing, CLI

---

## 📊 Project Overview

### Scope
- **26 Micro-Benchmarks**: Port all tasks (parse, filter, stats, predict, I/O, viz)
- **4 Application Benchmarks**: ETL, STATS, TRAIN, PRED topologies
- **5 Datasets**: TAXI, SYS, FIT, CITY, GRID
- **3+ Platforms**: Beam (primary), Flink, Ray

### Timeline
- **Phase 1** (Weeks 1-2): Core abstractions + proof of concept
- **Phase 2** (Weeks 3-4): 5 core benchmarks (1 per category)
- **Phase 3** (Weeks 5-6): Beam integration + ETL application
- **Phase 4** (Weeks 7-10): Complete all 26 benchmarks
- **Phase 5** (Weeks 11-12): Multi-platform (Flink, Ray)
- **Phase 6** (Weeks 13-14): All 4 applications
- **Phase 7** (Weeks 15-16): Polish, docs, packaging

**Total**: 16 weeks (4 months)

### Technology Stack

| Component | Java (Original) | Python (Proposed) |
|-----------|----------------|-------------------|
| Language | Java 7+ | Python 3.10+ |
| Primary Platform | Apache Storm | Apache Beam |
| Secondary | - | PyFlink, Ray |
| ML Library | Weka | scikit-learn |
| Config | .properties | YAML + Pydantic |
| Testing | JUnit | pytest |
| Type Checking | javac | mypy |
| Observability | Log4j | OpenTelemetry |

---

## 🔍 Key Architectural Patterns

### Pattern 1: Task Interface
```python
class ITask(Protocol):
    def setup(self, logger, config) -> None: ...
    def do_task(self, data: Dict) -> Optional[float]: ...
    def get_last_result(self) -> Optional[Any]: ...
    def tear_down(self) -> float: ...
```

### Pattern 2: Template Method
```python
class BaseTask(ABC):
    def do_task(self, data):
        start = time.perf_counter()
        result = self.do_task_logic(data)  # Child implements
        self._record_metrics(time.perf_counter() - start)
        return result
    
    @abstractmethod
    def do_task_logic(self, data): pass
```

### Pattern 3: Platform Adapter
```python
# Beam
class TaskDoFn(beam.DoFn):
    def __init__(self, task_class, config):
        self.task = task_class()
    
    def process(self, element):
        result = self.task.do_task({"D": element})
        if result: yield result

# Flink
class TaskMapFunction(MapFunction):
    def map(self, value):
        return self.task.do_task({"D": value})
```

### Pattern 4: Registry
```python
@register_task("bloom_filter")
class BloomFilterCheck(BaseTask): ...

# Dynamic loading
task_class = TaskRegistry.get("bloom_filter")
```

---

## 🧪 Validation Strategy

### Correctness
- [ ] Unit tests for all 26 tasks
- [ ] Integration tests for applications
- [ ] Compare outputs with Java version
- [ ] Validate ML predictions match

### Performance
- [ ] Benchmark throughput (events/sec)
- [ ] Measure latency (p50, p95, p99)
- [ ] Compare with Java/Storm baseline
- [ ] Target: Within 30% of Java performance

### Portability
- [ ] Same task code runs on Beam/Flink/Ray
- [ ] No platform-specific logic in tasks
- [ ] Configuration works across platforms

---

## 📝 Documentation Structure

```
pyDocs/
├── README.md (this file)           # Overview & navigation
│
├── 00-PORTING-PLAN.md              # Master plan (50+ pages)
│   ├── Part 1: Architecture Analysis
│   ├── Part 2: Framework Evaluation
│   ├── Part 3: Proposed Architecture
│   ├── Part 4: Roadmap
│   ├── Part 5: Design Decisions
│   ├── Part 6: Risk Mitigation
│   └── Appendices: Stack, Estimates, Checklist
│
├── 01-ARCHITECTURE-DETAILS.md      # Technical deep dive (35+ pages)
│   ├── Part 1: Portability Patterns
│   ├── Part 2: State Management
│   └── Part 3: Configuration Architecture
│
├── 02-PHASE1-PROTOTYPE.md          # Implementation guide (25+ pages)
│   ├── Project Structure
│   ├── Implementation Checklist
│   ├── Code Examples
│   └── Testing Strategy
│
├── 03-VISUAL-SUMMARY.md            # Visual guide (15+ pages)
│   ├── Architecture Diagrams
│   ├── Decision Trees
│   ├── Flow Charts
│   └── Quick Reference
│
└── 04-KEY-DECISIONS.md             # ADRs (12+ pages)
    ├── ADR-001: Python 3.10+
    ├── ADR-002: Apache Beam
    ├── ADR-003: Protocol-based interface
    └── ... (12 total ADRs)
```

**Total**: ~140 pages of comprehensive planning

---

## 🚀 Getting Started with Implementation

### Prerequisites
- Python 3.10+
- Git
- Understanding of streaming systems (Storm/Flink/Beam)
- Familiarity with ML (scikit-learn)

### Phase 1 Quick Start (Week 1-2)

```bash
# 1. Setup project
mkdir pyriotbench
cd pyriotbench
git init

# 2. Create structure (see 02-PHASE1-PROTOTYPE.md)
mkdir -p pyriotbench/core
mkdir -p pyriotbench/tasks
mkdir -p pyriotbench/platforms/standalone
mkdir -p tests

# 3. Implement core
# - ITask protocol (core/task.py)
# - BaseTask abstract class
# - TaskRegistry
# - StandaloneRunner

# 4. First benchmarks
# - NoOperationTask
# - SenMLParse

# 5. Validate
pytest
mypy pyriotbench
```

See **02-PHASE1-PROTOTYPE.md** for detailed day-by-day guide.

---

## ❓ FAQ

### Q: Why port to Python?
**A**: Python has richer data science ecosystem (scikit-learn, PyTorch, pandas), better cloud-native support (Beam, Dataflow), and is more accessible to researchers.

### Q: Will it be slower than Java?
**A**: Likely 20-30% slower for CPU-bound tasks, but:
- Still fast enough for benchmarking
- I/O and ML dominate runtime (not language overhead)
- Can optimize hot paths with Cython if needed

### Q: Why Beam as primary platform?
**A**: 
- True portability (runs on Flink, Spark, Dataflow, Direct)
- Mature Python SDK
- Best cloud integration
- Unified batch + streaming

### Q: Can we use existing Weka models?
**A**: No, need to retrain with scikit-learn. But we'll provide:
- Pre-trained sklearn models on same data
- Validation that predictions match
- Conversion tools/documentation

### Q: How do we ensure same results as Java?
**A**:
- Unit tests compare outputs
- Same datasets and configurations
- Deterministic tasks verified identical
- Non-deterministic tasks validated statistically

### Q: What about Storm support?
**A**: Not planned. Storm is legacy (last release 2018). Flink is Storm's successor with better Python support.

---

## 📞 Contact & Resources

### Original RIoTBench
- **Paper**: http://onlinelibrary.wiley.com/doi/10.1002/cpe.4257/abstract
- **GitHub**: https://github.com/anshuiisc/riot-bench
- **Authors**: DREAM Lab, Indian Institute of Science

### PyRIoTBench
- **Planning Docs**: This folder
- **Implementation**: TBD (after plan approval)
- **Team**: Your team here

---

## ✅ Next Steps

1. **Review & Approve** all planning documents
2. **Setup GitHub repo** for pyriotbench
3. **Begin Phase 1** implementation (see 02-PHASE1-PROTOTYPE.md)
4. **Weekly sync** to track progress
5. **First demo** after 2 weeks (NoOpTask + SenMLParse working)

---

**Document Version**: 1.0  
**Last Updated**: October 9, 2025  
**Status**: Ready for review and implementation

---

## 📊 Planning Document Statistics

- **Total Pages**: ~140 pages
- **Code Examples**: 60+ examples
- **Diagrams**: 20+ architecture diagrams
- **Tables**: 30+ comparison tables
- **Checklists**: 12+ actionable checklists
- **ADRs**: 12 Architecture Decision Records

**Coverage**:
- ✅ Complete architecture analysis
- ✅ Technology evaluation
- ✅ Risk assessment
- ✅ Detailed roadmap
- ✅ Concrete implementation guide
- ✅ Testing strategy
- ✅ Success criteria
- ✅ Visual diagrams and flowcharts
- ✅ Decision rationale documented

**Ready to start coding!** 🚀
