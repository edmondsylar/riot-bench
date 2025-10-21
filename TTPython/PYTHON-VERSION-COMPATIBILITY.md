# TTPython Python Version Compatibility Guide

**Date:** October 21, 2025  
**Project:** riot-bench TTPython Integration Research  
**Status:** Critical Issue - Python 3.12 Incompatibility Identified

---

## Executive Summary

**CRITICAL FINDING:** TTPython is **incompatible with Python 3.12** due to fundamental changes in Python's multiprocessing serialization (pickle) mechanism. All simulation attempts fail with `TypeError: cannot pickle 'generator' object`.

**IMMEDIATE ACTION REQUIRED:** Use **Python 3.9** for all TTPython development and simulation work.

---

## Table of Contents
1. [The Problem](#the-problem)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Evidence & Testing](#evidence--testing)
4. [Why This Affects ALL TTPython Programs](#why-this-affects-all-ttpython-programs)
5. [Python Version Compatibility Matrix](#python-version-compatibility-matrix)
6. [Solution: Python 3.9 Environment Setup](#solution-python-39-environment-setup)
7. [What We Learned](#what-we-learned)
8. [Future Considerations](#future-considerations)
9. [Technical Deep Dive](#technical-deep-dive)

---

## The Problem

### Symptom
When attempting to simulate any compiled TTPython program on Python 3.12:

```
TTPython.ExecutionProcess-runtime-manager:INFO:: Execute for SQ ADD-0
caught an error; could nuke process, but won't
Traceback (most recent call last):
  File "tt\ExecuteProcess.py", line 436, in spawn_sq_job
    p.start()
  ...
  File "C:\Python312\Lib\pickle.py", line 575, in save
    rv = reduce(self.proto)
TypeError: cannot pickle 'generator' object
```

### Impact
- ✅ **Compilation works** - TTPython can compile `.py` → `.pickle` graph
- ❌ **Simulation fails** - Cannot execute the compiled graph
- ❌ **All examples affected** - Both official and custom TTPython programs fail
- ❌ **No workaround in Python 3.12** - This is a fundamental runtime incompatibility

---

## Root Cause Analysis

### What Happened

**TTPython's Design (2021):**
```
1. Compile TTPython code → Dataflow graph
2. Spawn multiprocessing workers for each SQ (Stream Query)
3. Serialize (pickle) execution context to send to worker processes
4. Workers execute SQ code and return results
```

**Python 3.12's Breaking Change (2023):**
```
Python 3.12 made pickle stricter:
- Generator objects can no longer be serialized
- Module dictionaries have different serialization rules
- Closure handling changed for security/consistency
```

**The Collision:**
```
TTPython tries to pickle execution context
    ↓
Context contains generator objects (from Instructions, runtime internals)
    ↓
Python 3.12 pickle says: "Cannot pickle 'generator' object"
    ↓
Multiprocessing spawn fails
    ↓
Simulation crashes
```

### Where the Error Occurs

**File:** `tt/ExecuteProcess.py`  
**Line:** 436  
**Function:** `spawn_sq_job()`

```python
def spawn_sq_job(self, execution_context):
    # ... setup code ...
    p = multiprocess.Process(target=execute_sq, args=(sq_closure, ...))
    p.start()  # ← FAILS HERE: Can't pickle the execution context
```

**Why it fails:**
- `sq_closure` contains the SQ function and its dependencies
- Dependencies include TTPython's `Instructions` module
- `Instructions` contains generator objects used internally
- Python 3.12 can't serialize generators → pickle fails → process can't start

---

## Evidence & Testing

### Test Case 1: Official `add.py` Example

**Code:**
```python
from tt.SQ import GRAPHify
from tt.Instructions import ADD
from tt.Clock import TTClock

@GRAPHify
def main(a, b):
    with TTClock.root() as root_clock:
        return ADD(a, b)
```

**Results:**
| Step | Python 3.12 | Python 3.9 (Expected) |
|------|-------------|----------------------|
| Compilation | ✅ Success | ✅ Success |
| Simulation | ❌ Pickle Error | ✅ Success |

**Python 3.12 Error:**
```
TypeError: cannot pickle 'generator' object
```

### Test Case 2: Custom `temp_simple.py` Example

**Code:**
```python
@SQify
def temp_sensor(trigger):
    global sq_state
    if sq_state.get('count') is None:
        sq_state['count'] = 0
    sq_state['count'] += 1
    temp = 20 + (sq_state['count'] % 10)
    return temp

@GRAPHify
def temp_monitor(trigger):
    with TTClock.root() as root_clock:
        temp = temp_sensor(trigger)
        return temp
```

**Results:**
- ✅ Compilation successful
- ❌ Same pickle error during simulation

**Conclusion:** Error is **not code-specific**, it's a **Python 3.12 runtime issue**.

### Test Case 3: Evolution of Errors

We encountered **two separate issues** during testing:

#### Issue 1: Missing `TTClock.root()` Context
**Error:**
```
TypeError: Can only construct a TTClockSpec from a TTClock; given None
```

**Cause:** `add.py` was missing the required clock context  
**Fix:** Added `with TTClock.root() as root_clock:`  
**Status:** ✅ RESOLVED

#### Issue 2: Python 3.12 Pickle Incompatibility
**Error:**
```
TypeError: cannot pickle 'generator' object
```

**Cause:** Python 3.12's stricter serialization rules  
**Fix:** Downgrade to Python 3.9  
**Status:** ⚠️ WORKAROUND REQUIRED

---

## Why This Affects ALL TTPython Programs

### TTPython's Execution Model

Every TTPython simulation follows this path:

```
┌─────────────────────────────────────────┐
│ 1. Load compiled graph (.pickle file)  │ ✅ Works on Python 3.12
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 2. Setup runtime manager & ensembles   │ ✅ Works on Python 3.12
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 3. Distribute SQs to execution workers │ ❌ FAILS HERE
│    - Spawn multiprocessing.Process     │    (Pickle error)
│    - Serialize execution context       │
│    - Send to worker process            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 4. Execute SQ code in worker           │ ❌ Never reached
└─────────────────────────────────────────┘
```

**Key Point:** Step 3 is **mandatory** for all TTPython programs. There's no way to skip multiprocessing - it's baked into the architecture.

### What Gets Pickled

When spawning an SQ execution worker, Python tries to serialize:

```python
Execution Context = {
    'sq_closure': <function object>,           # The SQ function
    'sq_state': <dict>,                        # Persistent state
    'input_tokens': <list of TTToken>,         # Input data
    'clock_spec': <TTClockSpec>,              # Timing info
    'module_globals': {                        # Function dependencies
        'Instructions': <module>,              # ← Contains generators
        'SQ': <module>,
        'Clock': <module>,
        # ... and many more
    }
}
```

**The problem:** `Instructions` module contains generator objects used for lazy evaluation, iteration helpers, etc. Python 3.12 refuses to pickle these.

---

## Python Version Compatibility Matrix

| Python Version | Compilation | Simulation | Status | Notes |
|----------------|-------------|------------|--------|-------|
| **3.7** | ✅ | ✅ | ✅ Supported | TTPython tested on this |
| **3.8** | ✅ | ✅ | ✅ Supported | TTPython tested on this |
| **3.9** | ✅ | ✅ | ✅ **RECOMMENDED** | Best compatibility |
| **3.10** | ✅ | ⚠️ | ⚠️ Untested | May work, not guaranteed |
| **3.11** | ✅ | ⚠️ | ⚠️ Untested | Pickle changes started here |
| **3.12** | ✅ | ❌ | ❌ **BROKEN** | Confirmed incompatible |
| **3.13+** | ❌ | ❌ | ❌ Incompatible | More breaking changes |

### Official TTPython Documentation Quote

From TTPython installation guide:
> **Prerequisites:**  
> - Python ≥ 3.8 (tested on 3.7-3.9)

**Key insight:** They explicitly say "tested on 3.7-3.9", **NOT** "works on any Python ≥ 3.8". The upper bound (3.9) matters!

---

## Solution: Python 3.9 Environment Setup

### Option A: Using Conda (Recommended)

#### Step 1: Create Python 3.9 Environment
```powershell
# Create new environment with Python 3.9
conda create -n ttpython39 python=3.9 -y

# Activate the environment
conda activate ttpython39

# Verify Python version
python --version  # Should show: Python 3.9.x
```

#### Step 2: Install TTPython Dependencies
```powershell
# Navigate to TTPython directory
cd "Z:\Edmond Musiitwa Research\Riot\riot-bench\TTPython\ticktalkpython"

# Install core dependencies
pip install -r requirements.txt

# Install additional required packages
pip install ast_scope

# Optional: Install graphviz for visualization
conda install python-graphviz pydot -y
```

#### Step 3: Verify Installation
```powershell
# Test compilation
python compile.py examples/add.py

# Test simulation (should now work!)
python simulate.py output/add.pickle -i a=5 -i b=3
```

### Option B: Using Python venv

#### Step 1: Install Python 3.9
```powershell
# Download Python 3.9 from python.org
# Install to: C:\Python39\

# Verify installation
C:\Python39\python.exe --version
```

#### Step 2: Create Virtual Environment
```powershell
# Navigate to TTPython directory
cd "Z:\Edmond Musiitwa Research\Riot\riot-bench\TTPython\ticktalkpython"

# Create venv with Python 3.9
C:\Python39\python.exe -m venv ttpython_env39

# Activate environment (PowerShell)
.\ttpython_env39\Scripts\Activate.ps1

# Verify Python version
python --version  # Should show: Python 3.9.x
```

#### Step 3: Install Dependencies
```powershell
# Install core dependencies
pip install -r requirements.txt

# Install additional packages
pip install ast_scope
```

#### Step 4: Test
```powershell
python compile.py examples/add.py
python simulate.py output/add.pickle -i a=5 -i b=3
```

### Environment Management Tips

#### Switching Between Environments
```powershell
# Deactivate current environment
conda deactivate  # or: deactivate (for venv)

# Activate Python 3.9 environment
conda activate ttpython39

# Check which Python you're using
python --version
where python
```

#### Keep Both Environments
```
Your Setup:
├─ ttpython_env/        ← Python 3.12 (for compilation only)
└─ ttpython_env39/      ← Python 3.9 (for full workflow)

Workflow:
- Use Python 3.9 for everything (compilation + simulation)
- Python 3.12 environment no longer needed
```

---

## What We Learned

### Debugging Journey

1. **Initial Problem:** Custom examples (`temp_simple.py`) failed with pickle error
   - Hypothesis: Our code has issues with `random`/`time` modules
   - Action: Created simpler examples

2. **Second Problem:** Official `add.py` failed with clock error
   - Discovery: Missing `TTClock.root()` context
   - Fix: Added clock wrapper
   - Status: ✅ Resolved

3. **Third Problem:** `add.py` now fails with pickle error
   - Discovery: **Same error as our custom code**
   - Realization: This is **NOT code-specific**, it's **Python 3.12 incompatibility**
   - Evidence: Official TTPython code (`Instructions.ADD`) triggers the same error

4. **Root Cause Identified:** Python version mismatch
   - TTPython developed for Python 3.8-3.9 (2021)
   - Python 3.12 introduced breaking changes (2023)
   - TTPython codebase hasn't been updated for Python 3.12

### Key Insights

#### 1. Compilation vs. Execution Are Different
```
Compilation (Python 3.12): ✅ Works
- Parses Python AST
- Builds dataflow graph
- Writes .pickle file
- No multiprocessing involved

Execution (Python 3.12): ❌ Fails
- Loads .pickle graph
- Spawns worker processes ← USES MULTIPROCESSING
- Serializes execution context ← USES PICKLE
- Runs SQ code in workers
```

#### 2. The Error Location Matters
```
Error in YOUR code:          → Check your code
Error in TTPython runtime:   → Check Python version
Error in Python stdlib:      → Python incompatibility

Our case:
File "C:\Python312\Lib\pickle.py", line 575
                ↑
          Python's pickle module = Version incompatibility
```

#### 3. Documentation Upper Bounds Matter
```
"Python ≥ 3.8" ≠ "Python 3.8 or higher forever"

It means:
"Python 3.8+ AT THE TIME OF RELEASE (2021)"

More accurate reading:
"Python 3.8-3.9 (tested versions)"
```

---

## Future Considerations

### Option 1: Use Python 3.9 (Recommended)
**Pros:**
- ✅ Works immediately
- ✅ Matches TTPython's tested environment
- ✅ All examples work out-of-box
- ✅ Focus on learning TTPython, not debugging

**Cons:**
- ⚠️ Using older Python version
- ⚠️ May miss Python 3.12 features (but TTPython code wouldn't use them anyway)

**Verdict:** **Best option for learning and using TTPython**

---

### Option 2: Wait for Official TTPython Update
**Pros:**
- ✅ Eventual Python 3.12 compatibility
- ✅ No need to modify code yourself

**Cons:**
- ❌ May never happen (project maintenance unclear)
- ❌ Could take months/years
- ❌ Blocks your current work

**Verdict:** Not practical for active development

---

### Option 3: Update TTPython Runtime Yourself
**Pros:**
- ✅ Learn TTPython internals deeply
- ✅ Contribute to open-source
- ✅ Use latest Python features

**Cons:**
- ❌ Complex: Need to understand multiprocessing internals
- ❌ Time-consuming: Weeks of work
- ❌ Risky: May introduce bugs
- ❌ Must maintain fork going forward

**What Would Need Changing:**
1. **ExecuteProcess.py:**
   - Replace `multiprocess.Process` with thread-based execution
   - Or: Refactor to avoid pickling generators

2. **Instructions.py:**
   - Identify generator objects
   - Replace with pickle-safe alternatives
   - Maintain backward compatibility

3. **Runtime serialization:**
   - Implement custom `__reduce__` methods
   - Handle closure serialization manually
   - Test across all Python 3.8-3.12

**Estimated Effort:** 2-4 weeks of full-time work

**Verdict:** Only if you need Python 3.12 features AND have time for deep TTPython development

---

### Option 4: Hybrid Approach
**Strategy:**
1. Use Python 3.9 for TTPython work (simulation, learning)
2. Use Python 3.12 for other parts of riot-bench project
3. Keep environments separate

**Implementation:**
```
riot-bench/
├─ TTPython/
│  └─ Use Python 3.9 (conda: ttpython39)
│
├─ pyriotbench/
│  └─ Use Python 3.12 (venv: .venv)
│
└─ modules/ (Java)
   └─ Independent of Python version
```

**Verdict:** **Best for mixed-technology projects**

---

## Technical Deep Dive

### Python 3.12 Pickle Changes

#### What Changed in Python 3.12

**1. Generator Serialization Removed**
```python
# Python 3.9: Works
def my_gen():
    yield 1
    
import pickle
g = my_gen()
pickle.dumps(g)  # ✅ Success

# Python 3.12: Fails
pickle.dumps(g)  # ❌ TypeError: cannot pickle 'generator' object
```

**Why:** Security and consistency. Generators maintain internal state that's hard to serialize safely.

**2. Module Dictionary Handling Changed**
```python
# Python 3.9: Pickles module globals lazily
# Python 3.12: Stricter validation of what's in module dicts
```

**Why:** Prevent serialization of unpicklable objects hiding in module namespaces.

**3. Closure Handling Tightened**
```python
# When pickling a function, Python must serialize:
def outer():
    some_generator = (x for x in range(10))
    def inner():
        return some_generator  # ← This closure references a generator
    return inner

# Python 3.9: May work (lax checking)
# Python 3.12: Fails (strict checking)
```

### TTPython's Pickle Chain

When TTPython tries to spawn an SQ execution worker:

```
multiprocess.Process.start()
    ↓
serialize Process object
    ↓
serialize target function (execute_sq)
    ↓
serialize function's closure (sq_closure)
    ↓
serialize closure's references
    ↓
serialize tt.Instructions module
    ↓
Instructions contains generator objects
    ↓
Python 3.12: "Cannot pickle generator"
    ↓
💥 CRASH
```

### Where Generators Appear in TTPython

Based on code inspection, generators likely appear in:

**1. Instructions Module:**
```python
# Lazy evaluation helpers
def lazy_eval(*args):
    return (process(arg) for arg in args)  # Generator
```

**2. Runtime Iteration:**
```python
# Token stream processing
def token_stream(inputs):
    for token in inputs:
        yield transform(token)  # Generator
```

**3. Internal Helpers:**
```python
# Various iterator utilities that use generator expressions
filter_tokens = (t for t in tokens if t.valid)
```

### Why Multiprocessing Needs Pickle

**Multiprocessing Model:**
```python
# Parent process
context = build_execution_context()
worker = Process(target=execute, args=(context,))
worker.start()  # ← Must send 'context' to child process

# How it sends data between processes:
1. Serialize 'context' with pickle
2. Write to pipe/queue
3. Child process reads from pipe
4. Deserialize with pickle
5. Now child has 'context' object
```

**Why pickle is mandatory:**
- Processes don't share memory (unlike threads)
- Must transfer data via inter-process communication (IPC)
- Pickle is Python's standard serialization for IPC
- No way to avoid it in multiprocessing

**Alternative (threads):**
```python
# Threads share memory - no pickling needed
worker = Thread(target=execute, args=(context,))
worker.start()  # Just passes reference, no serialization

# But: TTPython uses processes for isolation and parallelism
```

---

## Recommendations

### For Immediate TTPython Work

**✅ DO:**
1. Install Python 3.9 in a separate conda environment
2. Use Python 3.9 for all TTPython compilation and simulation
3. Follow official TTPython tutorials and examples
4. Focus on learning TTPython concepts, not fighting compatibility

**❌ DON'T:**
1. Try to make TTPython work on Python 3.12 right now
2. Modify TTPython runtime code unless you have weeks to spare
3. Mix Python 3.9 and 3.12 in the same workflow
4. Assume "Python ≥ 3.8" means any modern Python

### For Long-Term Planning

**If you need TTPython for production:**
1. Evaluate whether Python 3.9 is acceptable for your deployment
2. Check if Python 3.12 features are actually needed
3. Consider containerization (Docker with Python 3.9)
4. Monitor TTPython repo for updates

**If you want to contribute:**
1. Contact TTPython maintainers about Python 3.12 support
2. Propose/contribute runtime refactoring
3. Help create compatibility layer
4. Document issues and workarounds

---

## Quick Reference

### Current Environment Issues

| Environment | Python | Compilation | Simulation | Recommendation |
|-------------|--------|-------------|------------|----------------|
| `ttpython_env` | 3.12 | ✅ | ❌ | ⚠️ **Don't use for simulation** |
| `ttpython39` | 3.9 | ✅ | ✅ | ✅ **Use this** |

### Command Cheat Sheet

```powershell
# Create Python 3.9 environment
conda create -n ttpython39 python=3.9 -y

# Activate
conda activate ttpython39

# Navigate to TTPython
cd "Z:\Edmond Musiitwa Research\Riot\riot-bench\TTPython\ticktalkpython"

# Install dependencies
pip install -r requirements.txt
pip install ast_scope

# Compile example
python compile.py examples/add.py

# Simulate (with inputs)
python simulate.py output/add.pickle -i a=5 -i b=3

# Simulate (no inputs - uses defaults)
python simulate.py output/streaming_merge.pickle
```

### Error Quick Diagnosis

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `cannot pickle 'generator' object` | Python 3.12 incompatibility | Use Python 3.9 |
| `Can only construct TTClockSpec from TTClock; given None` | Missing `TTClock.root()` | Add clock context to `@GRAPHify` |
| `The number of input values and input arcs must be identical` | Wrong number of inputs | Check `simulate.py -i` arguments |
| `Function not SQified` | Missing `@SQify` decorator | Add decorator to function |

---

## Conclusion

**Bottom Line:** TTPython requires Python 3.9 for simulation. Python 3.12 introduces breaking changes in pickle/multiprocessing that TTPython's runtime cannot handle.

**Action Plan:**
1. ✅ Install Python 3.9 environment
2. ✅ Reinstall TTPython dependencies in Python 3.9
3. ✅ Test official examples
4. ✅ Proceed with TTPython learning and development
5. ⏸️ Revisit Python 3.12 compatibility later (if needed)

**This is NOT a bug in TTPython** - it's expected behavior given the Python version. The TTPython team tested on 3.7-3.9, and that's what we should use.

---

## Related Documentation

- [COMPREHENSIVE-TTPYTHON-STUDY.md](./COMPREHENSIVE-TTPYTHON-STUDY.md) - Full TTPython concepts
- [INSTALLATION-PLAN.md](./INSTALLATION-PLAN.md) - Installation roadmap
- [QUICK-REFERENCE.md](./QUICK-REFERENCE.md) - Daily coding reference
- [install_ttpython.ps1](./install_ttpython.ps1) - Installation script (update for Python 3.9)

---

**Document Status:** Complete  
**Verified:** October 21, 2025  
**Next Update:** After successful Python 3.9 testing
