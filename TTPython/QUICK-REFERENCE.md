# TTPython Quick Reference Guide

## Essential Concepts (One-Pagers)

### What is TTPython?
A Python-based DSL for distributed time-sensitive IoT/CPS applications that treats **time as a first-class language concept**. Write one program, run distributed.

---

## Core Decorators

### `@SQify` - Create Stream Query
Converts Python function → computational unit in dataflow graph

```python
@SQify
def sensor_reader(trigger):
    global sq_state  # Persistent state (local to this SQ)
    
    # Standard Python code (NO TTPython constructs!)
    if sq_state.get('sensor') is None:
        sq_state['sensor'] = initialize_sensor()
    
    data = sq_state['sensor'].read()
    return data
```

**Rules:**
- ✅ Standard Python only inside
- ✅ Use `sq_state` for persistent state
- ✅ Pass-by-value semantics
- ❌ No `*args` (static argument count required)
- ❌ No TTPython constructs inside

---

### `@GRAPHify` - Define Program Structure
Defines main program and dataflow connections

```python
@GRAPHify
def main_program(trigger):
    with TTClock.root() as root_clock:
        # Function calls define dataflow
        sensor_data = sensor_reader(trigger)
        processed = process_data(sensor_data)
        result = aggregate(processed)
```

**Rules:**
- ✅ Must have ≥1 argument (trigger)
- ✅ Only call `@SQify` functions
- ❌ Cannot call regular Python functions

---

## Key Concepts Cheat Sheet

| Concept | Explanation |
|---------|-------------|
| **SQ (Stream Query)** | Basic computational unit; node in dataflow graph |
| **Ensemble** | Device running Python3 participating in system |
| **Token** | Data packet: `{value, tag: {destination, time_interval}}` |
| **Time-Interval** | `[start, end]` validity window (not point timestamp!) |
| **sq_state** | Per-SQ persistent state (isolated, not global) |
| **TTClock** | Synchronized clock context for temporal operations |
| **Dataflow Graph** | Compiled form: SQs (nodes) + implicit comms (arcs) |

---

## Time Philosophy

```
❌ Traditional:    exact_timestamp = 12:00:00.000
✅ TTPython:       time_interval = [11:59:59, 12:00:01]

Why? Distributed systems can't guarantee exact timestamps.
Intervals represent validity periods, enable realistic synchronization.
```

---

## Common Patterns

### Pattern 1: Sensor Initialization
```python
@SQify
def init_once(trigger):
    global sq_state
    if sq_state.get('initialized') is None:
        sq_state['sensor'] = expensive_setup()
        sq_state['initialized'] = True
    return sq_state['sensor'].read()
```

### Pattern 2: Stream Processing Pipeline
```python
@GRAPHify
def pipeline(trigger):
    with TTClock.root() as clock:
        raw = read_sensor(trigger)
        filtered = filter_noise(raw)
        features = extract_features(filtered)
        decision = classify(features)
        actuate(decision)
```

### Pattern 3: Multi-Sensor Fusion
```python
@GRAPHify
def fusion(trigger):
    with TTClock.root() as clock:
        temp = temperature_sensor(trigger)
        humid = humidity_sensor(trigger)
        # TTPython syncs based on time-interval overlap
        combined = fuse_sensors(temp, humid)
```

---

## Installation Quick Start

```powershell
# 1. Clone repo
git clone https://bitbucket.org/ccsg-res/ticktalkpython.git
cd ticktalkpython
git checkout tutorial

# 2. Create environment
python -m venv ttpython_env
.\ttpython_env\Scripts\Activate.ps1

# 3. Install
pip install -r requirements.txt
pip install ast_scope

# 4. Test
jupyter notebook TickTalkTest.ipynb
```

---

## Compilation & Execution

```python
from ticktalk import compile, simulate

# Compile to dataflow graph
graph = compile(
    main_program,           # Your @GRAPHify function
    use_graphviz=True       # Optional visualization
)

# Simulate execution
results = simulate(
    graph,
    trigger_value=initial_input,
    ensembles=ensemble_config
)
```

---

## Debugging Tips

| Problem | Solution |
|---------|----------|
| "Function not SQified" | Add `@SQify` to called function |
| "sq_state not defined" | Use `global sq_state` inside SQ |
| "Graph too slow in Jupyter" | Normal (2x slower); try terminal |
| "Can't find time overlap" | Check time-interval generation |
| Import errors | Verify `requirements.txt` installed |

---

## When to Use TTPython

### ✅ Perfect For:
- IoT sensor networks
- Smart city applications
- Distributed CPS
- Heterogeneous hardware
- Statistical timing requirements

### ❌ Not For:
- Hard real-time systems
- Microsecond precision needs
- Single-device apps
- Safety-critical systems

---

## Key Resources

- **Docs:** https://ccsg.ece.cmu.edu/ttpython/
- **Repo:** https://bitbucket.org/ccsg-res/ticktalkpython/
- **Video:** https://www.youtube.com/watch?v=xCLy89LLpaw
- **Examples:** `CAVExamples.ipynb` in tutorial branch

---

## Mental Model

```
Traditional Distributed Programming:
├─ Manually manage timestamps
├─ Write communication protocols
├─ Handle heterogeneous hardware
├─ Implement synchronization
└─ Map tasks to devices
   → Complex, error-prone, requires expertise

TTPython:
├─ Declare time requirements ("what")
├─ Write one unified program
├─ Runtime handles distribution
└─ Compiler generates dataflow
   → Simple, abstracted, accessible
```

---

## Critical Success Factors

1. **Think Dataflow:** Not imperative, think data transformations
2. **Isolate State:** `sq_state` is per-SQ, not shared
3. **Trust Runtime:** Let TTPython handle distribution
4. **Use Intervals:** Not timestamps, think validity windows
5. **Follow Rules:** Strict decorator discipline required

---

**Last Updated:** October 15, 2025  
**Quick Start:** Run `install_ttpython.ps1` in PowerShell
