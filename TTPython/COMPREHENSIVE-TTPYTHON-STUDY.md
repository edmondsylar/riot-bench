# Comprehensive TTPython Study & Installation Plan

**Date:** October 15, 2025  
**Project:** riot-bench TTPython Integration Research  
**Status:** Initial Study & Installation Planning

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [What is TTPython?](#what-is-ttpython)
3. [Key Nature and Fundamental Concepts](#key-nature-and-fundamental-concepts)
4. [Core Language Features](#core-language-features)
5. [Architecture Overview](#architecture-overview)
6. [Converting Python to TTPython](#converting-python-to-ttpython)
7. [Installation Plan](#installation-plan)
8. [Comparison with RIoTBench](#comparison-with-riotbench)
9. [Next Steps](#next-steps)

---

## Executive Summary

TTPython is a Domain Specific Language (DSL) built on Python3 that fundamentally reimagines how we program **distributed time-sensitive applications** for IoT and Cyber-Physical Systems (CPS). Its revolutionary approach integrates **time as a foundational language concept**, enabling developers to focus on *what* to do with time rather than *how* to implement complex timing mechanisms.

### Key Innovation
TTPython separates **program logical correctness** from **optimal mapping onto heterogeneous computing elements**, dramatically simplifying the development of large-scale IoT sensor/actuator networks while maintaining statistical precision and large-scale time accuracy.

---

## What is TTPython?

### Project Origins
- Part of the **TickTalk (TT) project** from Carnegie Mellon University (CCE/CMU)
- Designed for loosely-timed systems like smart cities
- Conceived in January 2021
- MIT License

### Problem Domain
TTPython addresses challenges in systems where:
- ⏰ **Time matters** critically
- ⚡ **Parallelism is inherent**
- 🖥️ **Hardware elements are heterogeneous**
- 🔋 **Power may be scarce**

### Target Users
- Non-specialist programmers developing IoT solutions
- Developers building massive sensor/actuator networks
- Teams working on distributed CPS applications
- Those needing statistical precision over hard real-time guarantees

---

## Key Nature and Fundamental Concepts

### 1. **Time as a First-Class Citizen**

TTPython doesn't just track time—it makes time a **foundational language concept**. This means:

```
Traditional Approach: Manually manage timestamps, synchronization, protocols
TTPython Approach: Declare temporal requirements; runtime handles implementation
```

**Key Insight:** Programs express "what to do with time" rather than "how to do it"

### 2. **Separation of Concerns**

```
┌─────────────────────────────────────┐
│  Program Logical Correctness       │  ← Developer focuses here
│  (Application Logic)                │
└─────────────────────────────────────┘
              ↓ (Decoupled)
┌─────────────────────────────────────┐
│  Optimal Mapping to Hardware        │  ← Runtime handles this
│  (Distributed Execution)            │
└─────────────────────────────────────┘
```

### 3. **Single Program, Distributed Execution**

- Write one coherent program for the entire distributed application
- No extensive interface/protocol descriptions needed
- Temporal and mapping requirements consolidated in one place

### 4. **Statistical Precision Model**

❌ **Not for:** Hard real-time systems, worst-case execution time guarantees  
✅ **Perfect for:** Large-scale IoT with statistical precision, loosely-timed systems

---

## Core Language Features

### 1. **Stream Queries (SQs) - The Fundamental Unit**

**Definition:** SQs are the basic computational units in TTPython, representing nodes in a dataflow graph.

**Structure:**
```
┌──────────────────────────────────────┐
│  1. Input Collection                 │  ← Synchronization barrier
│     (Wait for complete set)          │
├──────────────────────────────────────┤
│  2. Code Execution                   │  ← Your Python function
│     (Process inputs, produce outputs)│
├──────────────────────────────────────┤
│  3. Output Forwarding                │  ← Distribute results
│     (Send to connected SQs)          │
└──────────────────────────────────────┘
```

**Key Properties:**
- Operate as functions with persistent (static) state
- No direct memory sharing between SQs (except returned values)
- Pass-by-value semantics for all data
- Each SQ can maintain its own `sq_state` (isolated persistent state)

### 2. **Timed Dataflow Graph Compilation**

TTPython programs compile to **timed dataflow graphs**:
- **Nodes:** SQs (computational units)
- **Arcs:** Implicit communication links (no protocol specification needed)
- **Timing Semantics:** Time-intervals for synchronization, not point timestamps

**Time-Interval Philosophy:**
```
❌ Traditional: Exact timestamp matching (unrealistic in distributed systems)
✅ TTPython: Time-intervals with overlap detection (realistic concurrency)

Example: Two temperature sensors at 12:00 PM
  Sensor A: [12:00:00, 12:00:05] ← 5-second validity window
  Sensor B: [11:59:58, 12:00:03] ← Overlaps with A
  → These can be processed together (concurrent samples)
```

### 3. **Ensembles - The Runtime Environment**

**Ensemble Definition:** A device (or simulated device) that can run Python3 and participate in the TTPython distributed system.

**Can be:**
- Servers
- Personal computers
- Mobile phones
- Industrial controllers
- Embedded systems
- Simulated devices

**Requirements:**
- Must run Python ≥ 3.8
- Can have heterogeneous hardware (CPU, GPU, sensors, actuators)

### 4. **Key Language Constructs**

| Construct | Purpose |
|-----------|---------|
| `@SQify` | Convert Python functions to Stream Queries |
| `@GRAPHify` | Define the main program graph structure |
| `TTClock.root()` | Establish synchronized clock contexts |
| `sq_state` | Maintain persistent state within an SQ |
| Deadlines & Plan B | Handle timing constraint violations |
| Mapping directives | Specify where code runs (e.g., GPU required) |

---

## Architecture Overview

### The Three-Component System

```
┌─────────────────────────────────────────────────────────────┐
│                    TTPython SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. LANGUAGE (DSL)                                          │
│     - Pythonic syntax + time constructs                     │
│     - @SQify, @GRAPHify decorators                         │
│     - TTClock, Deadlines, Streams                          │
│                                                              │
│                         ↓ compiles to                       │
│                                                              │
│  2. COMPILER                                                │
│     - Analyzes code structure                               │
│     - Generates timed dataflow graph                        │
│     - Determines SQ connections                             │
│     - Optional: Graphviz visualization                      │
│                                                              │
│                         ↓ executes on                       │
│                                                              │
│  3. RUNTIME ENVIRONMENT                                     │
│     - Distributed execution across Ensembles                │
│     - Token-based communication (values + tags)             │
│     - Time-interval synchronization                         │
│     - Dynamic mapping optimization                          │
│     - Optional: Physics simulation backend                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Token Structure

Every piece of data flowing through the system is a **token** containing:

```python
Token = {
    'value': <actual_data>,           # The payload
    'tag': {
        'destination': <SQ_id>,        # Where it goes
        'ensemble': <ensemble_id>,     # Which device
        'app_id': <application_id>,    # Context identifier
        'time_interval': [start, end]  # Validity period
    }
}
```

### Mapping Intelligence

The runtime system performs **intelligent mapping** of SQs to Ensembles:

**Hard Constraints (programmer-specified):**
- Run acoustic generator on device with microphone
- Run image processing on device with GPU
- Run sensor reading on device with that sensor

**Soft Objectives (runtime-optimized):**
- Minimize power consumption on battery devices
- Minimize end-to-end latency
- Balance CPU utilization
- Adapt to network congestion

⚠️ **Note:** Optimal mapping is generally NP-hard; TTPython uses best-effort heuristics

---

## Converting Python to TTPython

### The Two-Decorator Pattern

Every TTPython program follows this structure:

```python
# 1. Define computational units with @SQify
@SQify
def computational_unit(input_data):
    # Standard Python code (no TTPython constructs here!)
    global sq_state  # Persistent state (local to this SQ instance)
    
    # Your logic here
    result = process(input_data)
    
    return result

# 2. Define program structure with @GRAPHify
@GRAPHify
def main_program(trigger):
    with TTClock.root() as root_clock:
        # Call @SQify functions - this creates the dataflow
        data = computational_unit(trigger)
        # Continue building the graph...
```

### Detailed Example: Camera Processing Pipeline

```python
# ============================================
# STEP 1: Define Stream Query for Camera Sampling
# ============================================
@SQify
def camera_sampler(trigger):
    """
    Samples camera frames from a video stream.
    This is a standard Python function made TTPython-aware via @SQify.
    """
    import sys, time
    sys.path.insert(0, '/content/ticktalkpython/libraries')
    import camera_recognition
    
    global sq_state  # Persistent state (isolated to this SQ instance)
    
    # Initialize camera on first run
    if sq_state.get('camera', None) == None:
        camera_specifications = camera_recognition.Settings()
        camera_specifications.darknetPath = '/content/darknet/'
        camera_specifications.useCamera = False
        camera_specifications.inputFilename = '/content/yolofiles/cav1/live_test_output.avi'
        camera_specifications.camTimeFile = '/content/yolofiles/cav1/cam_output.txt'
        camera_specifications.cameraHeight = .2
        camera_specifications.cameraAdjustmentAngle = 0.0
        camera_specifications.fps = 60
        camera_specifications.width = 1280
        camera_specifications.height = 720
        camera_specifications.flip = 2
        sq_state['camera'] = camera_recognition.Camera(camera_specifications)
    
    # Package 5 frames
    output_package = []
    for idx in range(5):
        frame_read, camera_timestamp = sq_state['camera'].takeCameraFrame()
        output_package.append([frame_read, camera_timestamp])
    
    return [output_package, time.time()]

# ============================================
# STEP 2: Define Stream Query for Frame Processing
# ============================================
@SQify
def process_camera(cam_sample):
    """
    Processes camera frames to extract coordinates.
    Another @SQify function - can be called from @GRAPHify.
    """
    import sys, time
    sys.path.insert(0, '/content/ticktalkpython/libraries')
    import camera_recognition
    
    global sq_state
    
    for each in cam_sample:
        camera_frame = each[0]
        camera_timestamp = each[1]
        
        # Initialize processor on first run
        if sq_state.get('camera_recognition', None) == None:
            camera_specifications = camera_recognition.Settings()
            # ... (setup code similar to above)
            sq_state['camera_recognition'] = camera_recognition.ProcessCamera(camera_specifications)
        
        coordinates, processed_timestamp = sq_state['camera_recognition'].processCameraFrame(
            camera_frame, camera_timestamp
        )
    
    return coordinates

# ============================================
# STEP 3: Define Graph Structure
# ============================================
@GRAPHify
def example_1_test(trigger):
    """
    Main program that orchestrates the dataflow.
    This defines the connections between SQs.
    """
    with TTClock.root() as root_clock:
        # Implicit dataflow: camera_sampler → process_camera
        cam_sample = camera_sampler(trigger)
        processed_camera = process_camera(cam_sample)
        
        # The return value of camera_sampler automatically becomes
        # the input to process_camera. TTPython handles the token
        # passing, synchronization, and potential network communication.
```

### Critical Rules for @SQify Functions

✅ **Allowed:**
- Any standard Python code
- Standard library imports
- Third-party package usage
- `sq_state` for persistent state
- `**kwargs` if defined in function signature

❌ **Not Allowed:**
- TTPython constructs inside the function
- `*args` in function definitions (must have statically known argument count)
- Direct memory sharing between SQs
- Calling non-@SQify functions from @GRAPHify

### Critical Rules for @GRAPHify Functions

✅ **Required:**
- Must accept at least one argument (the trigger)
- Can only call @SQify-decorated functions
- Establishes dataflow connections via function calls

❌ **Not Allowed:**
- Calling regular (non-@SQify) Python functions
- Complex control flow that obscures dataflow structure

---

## Installation Plan

### Prerequisites

**System Requirements:**
- Python ≥ 3.8 (tested on 3.7-3.9)
- Git
- (Optional) Conda or Python venv for environment isolation
- (Optional) Graphviz for graph visualization

**Recommended Tools:**
- Anaconda/Miniconda
- Jupyter Notebook
- Visual Studio Code

### Installation Method 1: Google Colab (Quickest)

**Best for:** Quick experimentation, no local setup

1. Open the tutorial notebook:
   ```
   https://bitbucket.org/ccsg-res/ticktalkpython/src/tutorial/CAVExamples.ipynb
   ```

2. Run "Step 1" to install dependencies automatically

3. Follow along with the tutorials

### Installation Method 2: Local Installation (Recommended for Development)

#### Step 1: Clone Repository

```powershell
# Navigate to your workspace
cd "Z:\Edmond Musiitwa Research\Riot\riot-bench\TTPython"

# Clone the TTPython repository
git clone https://bitbucket.org/ccsg-res/ticktalkpython.git

# Navigate to the repository
cd ticktalkpython

# Checkout the tutorial branch
git checkout tutorial
```

#### Step 2: Create Virtual Environment

**Option A: Using Conda (Recommended)**
```powershell
# Create environment
conda create -n ttpython python=3.9

# Activate environment
conda activate ttpython
```

**Option B: Using Python venv**
```powershell
# Create environment
python -m venv ttpython_env

# Activate environment (PowerShell)
.\ttpython_env\Scripts\Activate.ps1
```

#### Step 3: Install Dependencies

```powershell
# Install core dependencies
pip install -r requirements.txt

# Install ast_scope explicitly (conda doesn't have it)
pip install ast_scope
```

#### Step 4: (Optional) Install Graphviz Support

**For graph visualization during compilation:**

```powershell
# If using conda:
conda install python-graphviz
conda install pydot

# For the base graphviz (required for pygraphviz):
# On Windows: Download from https://graphviz.org/download/
# Install and add to PATH
```

**Notes:**
- Graphviz visualization is optional but helpful for debugging
- On macOS, use `brew install graphviz` before pip installs
- `pygraphviz` requires system-level graphviz installation

#### Step 5: Basic Testing

```powershell
# Start Jupyter Notebook
jupyter notebook TickTalkTest.ipynb
```

**In the notebook:**
1. Run Block 1: Compiles example program `streaming_merge`
   - Produces two sinusoid streams sampled every 500ms
   - Adds them together
   - Computes moving average

2. Run Block 2: Simulates the compiled graph
   - ⚠️ May take 30-40 seconds in Jupyter (much faster in terminal)
   - Produces output graphs if successful

#### Step 6: Verify Installation

Expected output:
- ✅ Regression tests pass
- ✅ Example compiles without errors
- ✅ Simulation produces two graphs (sinusoid addition + moving average)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `No module named 'ast_scope'` | `pip install ast_scope` |
| `No module named 'graphviz'` | Install system graphviz + `pip install graphviz` |
| Conda environment issues | Check Python version: `python --version` |
| Slow Jupyter simulation | Normal (2 orders of magnitude slower than terminal) |
| Import errors in notebook | Verify all `requirements.txt` packages installed |

---

## Comparison with RIoTBench

### RIoTBench Overview
- **Java-based** benchmark suite for distributed stream processing
- **Targets:** Apache Storm and similar platforms
- **Purpose:** Performance evaluation of stream processing infrastructure

### Relationship to TTPython

| Aspect | RIoTBench | TTPython |
|--------|-----------|----------|
| **Language** | Java | Python3 + DSL |
| **Purpose** | Benchmark performance | Simplify programming |
| **Focus** | "How fast/efficient?" | "What to compute?" |
| **Abstraction** | Low-level (Storm topologies) | High-level (time-aware graphs) |
| **Use Case** | Testing platforms | Building applications |

### Complementary Nature

```
┌────────────────────────────────────────────────────────┐
│  Application Development Layer                         │
│  ┌──────────────────────────────────────────────┐     │
│  │  TTPython: Simplified Programming            │     │
│  │  - Focus on logic, not distribution          │     │
│  │  - Time as first-class concept               │     │
│  └──────────────────────────────────────────────┘     │
│                       ↓                                │
│  ┌──────────────────────────────────────────────┐     │
│  │  Distributed Stream Processing Platform      │     │
│  │  (e.g., Apache Storm, Flink, etc.)          │     │
│  └──────────────────────────────────────────────┘     │
│                       ↓                                │
│  ┌──────────────────────────────────────────────┐     │
│  │  RIoTBench: Performance Evaluation           │     │
│  │  - Measure throughput, latency               │     │
│  │  - Test micro-benchmarks                     │     │
│  └──────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

**Synergy:**
- TTPython abstracts away complexity RIoTBench measures
- RIoTBench validates performance of platforms TTPython targets
- Both address distributed time-sensitive IoT applications
- TTPython could potentially compile to Storm (RIoTBench's target)

---

## Next Steps

### Phase 1: Installation & Basic Understanding ✅ (Current Phase)
- [x] Comprehensive study of TTPython concepts
- [ ] Clone repository
- [ ] Set up local environment
- [ ] Run basic tests
- [ ] Complete TickTalkTest.ipynb

### Phase 2: Tutorial Completion
- [ ] Work through car position tracking tutorial
- [ ] Understand `@SQify` and `@GRAPHify` patterns
- [ ] Learn stream generation (`@STREAMify`)
- [ ] Study mapping directives
- [ ] Explore deadlines and Plan B mechanisms
- [ ] Complete "Intersecting Concepts" tutorial

### Phase 3: RIoTBench Integration Analysis
- [ ] Compare RIoTBench benchmarks with TTPython capabilities
- [ ] Identify micro-benchmarks that could be implemented in TTPython
- [ ] Analyze mapping between Storm topologies and TTPython graphs
- [ ] Design hybrid testing approach

### Phase 4: Prototype Development
- [ ] Port a simple RIoTBench benchmark to TTPython
- [ ] Implement common IoT patterns (e.g., sensor aggregation)
- [ ] Test distributed execution
- [ ] Performance comparison study

### Phase 5: Advanced Topics
- [ ] Custom simulation backends
- [ ] Advanced mapping strategies
- [ ] Integration with real hardware (if available)
- [ ] Scalability testing

---

## Key Takeaways

### TTPython's Unique Value Proposition

1. **Time Integration:** First language to make time a foundational concept
2. **Abstraction Level:** Separates correctness from mapping (unique in IoT space)
3. **Accessibility:** Non-specialists can write distributed time-sensitive apps
4. **Python Base:** Leverage existing Python ecosystem and knowledge
5. **Unified Specification:** Single program defines entire distributed application

### When to Use TTPython

✅ **Perfect for:**
- Large-scale IoT sensor networks
- Smart city applications
- Distributed CPS with statistical timing requirements
- Heterogeneous hardware environments
- Applications where power is a concern

❌ **Not suitable for:**
- Hard real-time systems (safety-critical)
- Applications requiring worst-case execution time guarantees
- Single-device, non-distributed applications
- Systems needing microsecond precision

### Critical Success Factors

1. **Mindset Shift:** Think in terms of dataflow, not imperative control flow
2. **State Management:** Understand `sq_state` isolation vs. Python globals
3. **Time Intervals:** Work with validity windows, not point timestamps
4. **Decorator Discipline:** Strictly follow @SQify/@GRAPHify rules
5. **Graph Thinking:** Visualize your application as connected SQs

---

## Resources

### Official Documentation
- Main Site: https://ccsg.ece.cmu.edu/ttpython/
- Overview: https://ccsg.ece.cmu.edu/ttpython/overview.html
- Core Concepts: https://ccsg.ece.cmu.edu/ttpython/coreconcepts.html
- Tutorial Index: https://ccsg.ece.cmu.edu/ttpython/tutorial-index.html
- Installation: https://ccsg.ece.cmu.edu/ttpython/tutorial/tutorial-install.html

### Repository
- Bitbucket: https://bitbucket.org/ccsg-res/ticktalkpython/
- Tutorial Branch: https://bitbucket.org/ccsg-res/ticktalkpython/src/tutorial/

### Additional Resources
- TickTalk Project Page: http://ccsg.ece.cmu.edu/wp/home/ticktalk/
- Demo Video: https://www.youtube.com/watch?v=xCLy89LLpaw
- CAV Examples Notebook: https://bitbucket.org/ccsg-res/ticktalkpython/src/tutorial/CAVExamples.ipynb

### Related Work
- RIoTBench Repository: https://github.com/dream-lab/riot-bench
- Apache Storm: https://storm.apache.org/
- MIT Tagged-Token Dataflow: (Historical context in TTPython advanced docs)

---

## Questions for Further Exploration

1. How does TTPython's runtime perform compared to hand-coded Storm topologies?
2. Can we create a TTPython-to-Storm compiler backend?
3. What is the overhead of time-interval synchronization vs. traditional timestamps?
4. How well does TTPython scale to 1000+ node networks?
5. Can RIoTBench benchmarks serve as validation tests for TTPython implementations?
6. What mapping strategies work best for battery-constrained devices?
7. How does TTPython handle network partitions and device failures?

---

**Document Status:** Initial comprehensive study completed  
**Next Action:** Proceed with local installation (Phase 1)  
**Owner:** Edmond Musiitwa Research Team  
**Last Updated:** October 15, 2025
