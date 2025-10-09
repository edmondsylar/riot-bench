# 📖 Complete Documentation Index

## 🎯 Quick Navigation

### 📚 Documentation Files (In Reading Order)

| # | Document | Purpose | Target Audience |
|---|----------|---------|----------------|
| 📋 | [README.md](README.md) | Documentation home page | Everyone |
| 📊 | [00-summary.md](00-summary.md) | Complete documentation summary | Everyone |
| 📖 | [01-overview.md](01-overview.md) | What is RIoTBench? | Researchers, Students |
| 🔧 | [02-micro-benchmarks.md](02-micro-benchmarks.md) | All 26 micro-benchmarks | Developers, Researchers |
| 🏗️ | [03-application-benchmarks.md](03-application-benchmarks.md) | 4 complete dataflows | System Architects |
| 🏛️ | [04-architecture.md](04-architecture.md) | System design & patterns | Developers, Contributors |
| 🚀 | [05-getting-started.md](05-getting-started.md) | Installation & first run | Everyone |
| ⚙️ | [06-configuration.md](06-configuration.md) | All config options | Sysadmins, Developers |
| 💾 | [07-datasets.md](07-datasets.md) | Data formats & datasets | Data Engineers |
| 🎨 | [08-visual-guide.md](08-visual-guide.md) | Diagrams & visuals | Everyone |
| 📇 | [INDEX.md](INDEX.md) | This file | Everyone |

---

## 🔍 Find What You Need

### I want to...

#### Understand RIoTBench
- **What is it?** → [Overview - Introduction](01-overview.md#what-is-riotbench)
- **Why use it?** → [Overview - Purpose](01-overview.md#purpose-and-motivation)
- **Key features?** → [Overview - Key Features](01-overview.md#key-features)
- **How it works?** → [Visual Guide - Architecture](08-visual-guide.md#system-architecture-diagram)

#### Run Benchmarks
- **Quick start** → [Getting Started - Quick Start](05-getting-started.md#quick-start-local-mode)
- **Build project** → [Getting Started - Installation](05-getting-started.md#installation)
- **Run micro-benchmark** → [Getting Started - Micro-Benchmarks](05-getting-started.md#running-different-benchmarks)
- **Run application** → [Getting Started - Application Benchmarks](05-getting-started.md#running-different-benchmarks)
- **Deploy to cluster** → [Getting Started - Cluster Deployment](05-getting-started.md#cluster-deployment)

#### Configure Benchmarks
- **All options** → [Configuration Guide](06-configuration.md)
- **Parse settings** → [Configuration - Parse](06-configuration.md#parse-configuration)
- **Filter settings** → [Configuration - Filter](06-configuration.md#filter-configuration)
- **ML settings** → [Configuration - Classification](06-configuration.md#classification-configuration)
- **Azure/MQTT** → [Configuration - I/O](06-configuration.md#io-configuration)
- **Performance tuning** → [Configuration - Tuning](06-configuration.md#performance-tuning)

#### Work with Data
- **Dataset overview** → [Datasets - Catalog](07-datasets.md#dataset-catalog)
- **TAXI data** → [Datasets - TAXI](07-datasets.md#1-taxi-dataset)
- **SYS data** → [Datasets - SYS](07-datasets.md#2-sys-smart-city-dataset)
- **Data formats** → [Datasets - Format Specs](07-datasets.md#data-format-specifications)
- **Create custom data** → [Datasets - Input Preparation](07-datasets.md#input-file-preparation)

#### Understand Architecture
- **System design** → [Architecture - Overview](04-architecture.md#overview)
- **Module structure** → [Architecture - Module Structure](04-architecture.md#module-structure)
- **Task lifecycle** → [Architecture - Task Lifecycle](04-architecture.md#task-lifecycle)
- **State management** → [Architecture - State Management](04-architecture.md#state-management)
- **Design patterns** → [Architecture - Design Patterns](04-architecture.md#core-design-patterns)

#### Extend/Contribute
- **Add new benchmark** → [Architecture - Extensibility](04-architecture.md#adding-new-micro-benchmarks)
- **Port to other platform** → [Architecture - Adapting](04-architecture.md#adapting-to-other-platforms)
- **Task interface** → [Architecture - Task Interface](04-architecture.md#1-task-interface-pattern)

#### Troubleshoot
- **Build errors** → [Getting Started - Build Errors](05-getting-started.md#build-errors)
- **Runtime errors** → [Getting Started - Runtime Errors](05-getting-started.md#runtime-errors)
- **Azure issues** → [Getting Started - Azure Errors](05-getting-started.md#azure-errors)
- **MQTT issues** → [Getting Started - MQTT Errors](05-getting-started.md#mqtt-errors)
- **Performance** → [Getting Started - Performance Issues](05-getting-started.md#performance-issues)

---

## 📚 Content by Topic

### Micro-Benchmarks (26 Total)

#### Parse Operations (4)
- [Annotate (ANN)](02-micro-benchmarks.md#11-annotate-ann) - Add metadata annotations
- [CsvToSenML (C2S)](02-micro-benchmarks.md#12-csvtosenml-c2s) - CSV to SenML conversion
- [SenML Parsing (SML)](02-micro-benchmarks.md#13-senml-parsing-sml) - Parse SenML messages
- [XML Parsing (XML)](02-micro-benchmarks.md#14-xml-parsing-xml) - Parse XML data

#### Filter Operations (2)
- [Bloom Filter (BLF)](02-micro-benchmarks.md#21-bloom-filter-blf) - Probabilistic membership test
- [Range Filter (RGF)](02-micro-benchmarks.md#22-range-filter-rgf) - Range-based filtering

#### Statistical Operations (6)
- [Accumulator (ACC)](02-micro-benchmarks.md#31-accumulator-acc) - Window accumulation
- [Average (AVG)](02-micro-benchmarks.md#32-average-avg) - Moving average
- [Distinct Approx Count (DAC)](02-micro-benchmarks.md#33-distinct-approximate-count-dac) - HyperLogLog counting
- [Kalman Filter (KAL)](02-micro-benchmarks.md#34-kalman-filter-kal) - Noise filtering
- [Second Order Moment (SOM)](02-micro-benchmarks.md#36-second-order-moment-som) - Variance calculation
- [Interpolation (INP)](02-micro-benchmarks.md#35-interpolation-inp) - Missing value interpolation

#### Predictive Operations (6)
- [Decision Tree Classify (DTC)](02-micro-benchmarks.md#41-decision-tree-classify-dtc) - DT classification
- [Decision Tree Train (DTT)](02-micro-benchmarks.md#42-decision-tree-train-dtt) - DT training
- [Linear Regression Predict (MLR)](02-micro-benchmarks.md#43-multi-variate-linear-regression-mlr) - LR prediction
- [Linear Regression Train (MLT)](02-micro-benchmarks.md#44-multi-variate-linear-regression-train-mlt) - LR training
- [Sliding Linear Regression (SLR)](02-micro-benchmarks.md#45-sliding-linear-regression-slr) - Window-based LR

#### I/O Operations (7)
- [Azure Blob Download (ABD)](02-micro-benchmarks.md#51-azure-blob-download-abd) - Download from Azure
- [Azure Blob Upload (ABU)](02-micro-benchmarks.md#52-azure-blob-upload-abu) - Upload to Azure
- [Azure Table Insert (ATI)](02-micro-benchmarks.md#53-azure-table-insert-ati) - Insert to Azure Table
- [Azure Table Range Query (ATR)](02-micro-benchmarks.md#54-azure-table-range-query-atr) - Query Azure Table
- [MQTT Publish (MQP)](02-micro-benchmarks.md#55-mqtt-publish-mqp) - Publish to MQTT
- [MQTT Subscribe (MQS)](02-micro-benchmarks.md#56-mqtt-subscribe-mqs) - Subscribe to MQTT

#### Visualization (1)
- [Multi-Line Plot (PLT)](02-micro-benchmarks.md#61-multi-line-plot-plt) - Real-time plotting

### Application Benchmarks (4 Total)

- [ETL - Extract, Transform, Load](03-application-benchmarks.md#1-etl-extract-transform-load) - Data pipeline
- [STATS - Statistical Summarization](03-application-benchmarks.md#2-stats-statistical-summarization) - Real-time analytics
- [TRAIN - Model Training](03-application-benchmarks.md#3-train-model-training) - Online learning
- [PRED - Predictive Analytics](03-application-benchmarks.md#4-pred-predictive-analytics) - Real-time prediction

### Datasets (5 Total)

- [TAXI Dataset](07-datasets.md#1-taxi-dataset) - Transportation (1.7M events)
- [SYS Dataset](07-datasets.md#2-sys-smart-city-dataset) - Smart City (2.3M events)
- [FIT Dataset](07-datasets.md#3-fit-fitness-dataset) - Fitness (1M events)
- [CITY Dataset](07-datasets.md#4-city-urban-infrastructure-dataset) - Infrastructure (500K events)
- [GRID Dataset](07-datasets.md#5-grid-smart-grid-dataset) - Energy (800K events)

---

## 🎓 Learning Paths

### Path 1: Beginner (First-time User)
1. Read [Overview](01-overview.md) - Understand what RIoTBench is
2. Review [Visual Guide](08-visual-guide.md) - See system diagrams
3. Follow [Getting Started](05-getting-started.md) - Run first benchmark
4. Study [Micro-Benchmarks](02-micro-benchmarks.md) - Learn operations
5. Explore [Datasets](07-datasets.md) - Understand data

### Path 2: Developer (Contributing Code)
1. Review [Architecture](04-architecture.md) - Understand design
2. Study [Micro-Benchmarks](02-micro-benchmarks.md) - Implementation details
3. Read [Application Benchmarks](03-application-benchmarks.md) - Composition patterns
4. Check [Configuration](06-configuration.md) - Parameter reference
5. See [Extensibility](04-architecture.md#extensibility-points) - Add new benchmarks

### Path 3: Researcher (Using for Experiments)
1. Read [Overview](01-overview.md) - Understand capabilities
2. Study [Application Benchmarks](03-application-benchmarks.md) - Use cases
3. Review [Datasets](07-datasets.md) - Data characteristics
4. Follow [Getting Started](05-getting-started.md) - Run experiments
5. Use [Configuration](06-configuration.md) - Tune parameters

### Path 4: System Administrator (Deployment)
1. Review [Getting Started](05-getting-started.md) - Installation
2. Study [Configuration](06-configuration.md) - All settings
3. Read [Cluster Deployment](05-getting-started.md#cluster-deployment) - Production setup
4. Check [Troubleshooting](05-getting-started.md#troubleshooting) - Common issues
5. Review [Performance](06-configuration.md#performance-tuning) - Optimization

---

## 📊 Statistics

### Documentation Metrics
- **Total Documents**: 11 files
- **Total Pages**: ~150+ pages (estimated)
- **Total Words**: ~50,000+ words
- **Code Examples**: 100+ examples
- **Diagrams**: 15+ visual diagrams

### Content Coverage
- **Micro-Benchmarks**: 26 documented
- **Application Benchmarks**: 4 documented
- **Datasets**: 5 documented
- **Configuration Options**: 100+ documented
- **Code Examples**: All major operations
- **Troubleshooting Scenarios**: 15+ documented

---

## 🔗 External Resources

### Official Resources
- **Paper**: http://onlinelibrary.wiley.com/doi/10.1002/cpe.4257/abstract
- **Pre-print**: https://arxiv.org/abs/1701.08530
- **GitHub Repository**: https://github.com/anshuiisc/riot-bench
- **DREAM Lab**: http://dream-lab.in/

### Related Technologies
- **Apache Storm**: https://storm.apache.org/
- **Weka ML**: https://www.cs.waikato.ac.nz/ml/weka/
- **Azure Storage**: https://azure.microsoft.com/services/storage/
- **MQTT**: https://mqtt.org/
- **SenML**: https://tools.ietf.org/html/rfc8428

### Research Papers
1. **RIoTBench Main Paper** (2017)
   - Shukla, A., Chaturvedi, S., & Simmhan, Y.
   - Concurrency and Computation: Practice and Experience
   
2. **Conference Version** (2016)
   - Shukla, A., & Simmhan, Y.
   - TPC Technology Conference (TPCTC)

---

## 🆘 Getting Help

### Documentation Navigation Tips
1. **Use Ctrl+F** (or Cmd+F) to search within documents
2. **Follow links** - Documents are heavily cross-referenced
3. **Check Visual Guide** - Diagrams often clarify concepts
4. **Refer to examples** - Code examples throughout docs

### If You Can't Find Something
1. Check this INDEX.md for topic location
2. Use the "Find What You Need" section above
3. Review the Summary document (00-summary.md)
4. Search across all .md files in the docs/ folder

### Common Questions
- **"How do I run X?"** → [Getting Started](05-getting-started.md)
- **"What does Y mean?"** → [Overview](01-overview.md) or [Visual Guide](08-visual-guide.md)
- **"How do I configure Z?"** → [Configuration Guide](06-configuration.md)
- **"Where is dataset D?"** → [Datasets](07-datasets.md)
- **"How does it work?"** → [Architecture](04-architecture.md)

---

## 📝 Document Conventions

### Symbols Used
- 📖 Documentation file
- 🔧 Technical/detailed content
- 🚀 Getting started/practical content
- ⚙️ Configuration/settings
- 💾 Data-related content
- 🎨 Visual/diagram content
- ⭐ New or highlighted content
- ✅ Complete/verified information

### Code Block Types
```bash
# Shell commands
```

```java
// Java code examples
```

```properties
# Configuration properties
```

```python
# Python scripts (for data prep)
```

### Links
- **[Internal Links]** - Link to other documentation files
- **External Links** - Link to external resources (papers, tools)

---

## 🔄 Version Information

- **Documentation Version**: 1.0
- **RIoTBench Version**: 0.1
- **Last Updated**: 2025
- **Maintained By**: Documentation team

---

## 📞 Contact & Citation

### Citation
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

### Organization
**DREAM Lab**  
Department of Computational and Data Sciences  
Indian Institute of Science  
Bangalore, India

---

**Happy Benchmarking! 🚀**
