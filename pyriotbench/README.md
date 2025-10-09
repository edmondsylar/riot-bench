# PyRIoTBench

**Python port of RIoTBench - A Real-time IoT Benchmark for Distributed Stream Processing Platforms**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Apache License 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Development Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/edmondsylar/riot-bench)

---

## 🎯 Overview

PyRIoTBench is a comprehensive benchmark suite for evaluating **Distributed Stream Processing Systems (DSPS)** in IoT contexts. It's a Python port of the original [RIoTBench](https://github.com/anshuiisc/riot-bench) with expanded platform support and modern Python tooling.

### Key Features

- ✅ **26 Micro-Benchmarks**: Parse, filter, statistics, ML, I/O, visualization
- ✅ **4 Application Benchmarks**: ETL, STATS, TRAIN, PRED (end-to-end dataflows)
- ✅ **Multi-Platform**: Apache Beam, PyFlink, Ray, standalone execution
- ✅ **Real Datasets**: TAXI, SYS, FIT, CITY, GRID (~6.3M IoT events)
- ✅ **Type-Safe**: Full type hints with mypy strict mode
- ✅ **Cloud-Native**: Azure, GCP, AWS integrations
- ✅ **Production-Ready**: Pre-trained models, comprehensive testing

---

## 🚀 Quick Start

### Installation

```bash
# Basic installation
pip install pyriotbench

# With all features
pip install pyriotbench[all]

# Development installation
git clone https://github.com/edmondsylar/riot-bench.git
cd riot-bench/pyriotbench
pip install -e ".[dev]"
```

### Basic Usage

```bash
# List available benchmarks
pyriotbench list-tasks

# Run a benchmark
pyriotbench run noop input.txt

# Run with configuration
pyriotbench run senml_parse data.json --config config.yaml --output parsed.txt
```

### Python API

```python
from pyriotbench.tasks.parse import SenMLParse
from pyriotbench.platforms.standalone import StandaloneRunner
import logging

# Create task
task = SenMLParse()

# Setup
logger = logging.getLogger('pyriotbench')
config = {'PARSE.SENML_ENABLED': True}
task.setup(logger, config)

# Process data
data = {"D": '{"bn": "sensor1", "e": [{"n": "temp", "v": 23.5}]}'}
result = task.do_task(data)

# Get results
parsed = task.get_last_result()
avg_time = task.tear_down()
```

---

## 📊 Architecture

PyRIoTBench uses a **modular, portable architecture** where benchmark tasks are platform-agnostic:

```
Task (Platform-Agnostic)     Platform Adapter           Streaming Platform
┌─────────────────────┐      ┌──────────────┐          ┌───────────────┐
│  ITask Protocol     │◄─────│ TaskDoFn     │◄─────────│ Apache Beam   │
│  • setup()          │      │ (Beam)       │          └───────────────┘
│  • do_task()        │      └──────────────┘          ┌───────────────┐
│  • get_last_result()│      ┌──────────────┐          │ PyFlink       │
│  • tear_down()      │◄─────│TaskMapFunc   │◄─────────│               │
└─────────────────────┘      │ (Flink)      │          └───────────────┘
                             └──────────────┘          ┌───────────────┐
                             ┌──────────────┐          │ Ray           │
                             │ TaskActor    │◄─────────│               │
                             │ (Ray)        │          └───────────────┘
                             └──────────────┘
```

**Key Principles**:
- Tasks have **zero platform dependencies**
- Same task code runs on any platform
- Platform adapters handle distribution, I/O, fault tolerance

---

## 🔧 Benchmarks

### Micro-Benchmarks (26)

| Category | Count | Examples |
|----------|-------|----------|
| **Parse** | 4 | SenML Parse, CSV→SenML, XML Parse, Annotate |
| **Filter** | 2 | Bloom Filter, Range Filter |
| **Statistics** | 6 | Average, Kalman Filter, Interpolation, Accumulator |
| **Predictive** | 6 | Decision Tree (train/predict), Linear Regression |
| **I/O** | 7 | Azure Blob/Table, MQTT Pub/Sub |
| **Visualization** | 1 | Multi-Line Plot |

### Application Benchmarks (4)

- **ETL**: Data ingestion and transformation pipeline
- **STATS**: Real-time statistical summarization
- **TRAIN**: Online machine learning model training
- **PRED**: Real-time predictive analytics

---

## 🧪 Development

### Setup Development Environment

```bash
# Clone and install with dev dependencies
git clone https://github.com/edmondsylar/riot-bench.git
cd riot-bench/pyriotbench
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy pyriotbench

# Linting
ruff check pyriotbench
black pyriotbench
```

### Project Structure

```
pyriotbench/
├── pyriotbench/
│   ├── core/           # Task abstractions, registry, config
│   ├── tasks/          # 26 micro-benchmark implementations
│   ├── platforms/      # Platform adapters (Beam, Flink, Ray)
│   ├── applications/   # 4 application benchmarks
│   └── cli/            # Command-line interface
├── tests/              # Unit and integration tests
├── examples/           # Usage examples
└── docs/               # Documentation
```

---

## 📚 Documentation

- **Planning Docs**: See [pyDocs/](../pyDocs/) for comprehensive planning
- **Implementation Guide**: [implementation_plan.md](../pyDocs/implementation_plan.md)
- **Progress Tracking**: [implementation_progress.md](../pyDocs/implementation_progress.md)
- **Original RIoTBench Paper**: [arXiv:1701.08530](https://arxiv.org/abs/1701.08530)

---

## 🤝 Contributing

Contributions are welcome! Please see our contributing guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run tests and type checking
5. Submit a pull request

---

## 📝 Citation

If you use PyRIoTBench in your research, please cite the original RIoTBench paper:

```bibtex
@article{shukla2017riotbench,
  title={RIoTBench: A Real-time IoT Benchmark for Distributed Stream Processing Platforms},
  author={Shukla, Anshu and Chaturvedi, Shilpa and Simmhan, Yogesh},
  journal={Concurrency and Computation: Practice and Experience},
  volume={29},
  number={21},
  year={2017},
  doi={10.1002/cpe.4257}
}
```

---

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Original RIoTBench by DREAM Lab, Indian Institute of Science, Bangalore
- Apache Beam, PyFlink, and Ray communities
- All contributors to this project

---

## 📞 Contact

- **GitHub Issues**: For bug reports and feature requests
- **Repository**: https://github.com/edmondsylar/riot-bench

---

**Status**: 🚧 Active Development (Alpha)  
**Last Updated**: October 9, 2025
