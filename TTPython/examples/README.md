# TTPython Examples

This folder contains simple TTPython applications to help you learn the framework.

## Examples List

### 01_hello_ttpython.py
**Difficulty:** Beginner  
**Concepts:** Basic SQs, dataflow pipeline, state management

A simple temperature monitoring system that demonstrates:
- Creating Stream Queries with `@SQify`
- Building a dataflow graph with `@GRAPHify`
- Using `sq_state` for persistent state
- Basic sensor simulation and data transformation

**Run:**
```bash
cd ticktalkpython
python ../examples/01_hello_ttpython.py
```

---

### 02_multi_sensor_fusion.py
**Difficulty:** Intermediate  
**Concepts:** Multiple sensors, data fusion, time synchronization

A weather station that fuses data from multiple sensors:
- Temperature, humidity, and pressure sensors
- Automatic time-interval synchronization
- Data aggregation and alert generation
- Parallel sensor reading

**Run:**
```bash
cd ticktalkpython
python ../examples/02_multi_sensor_fusion.py
```

---

## How to Run Examples

1. **Activate your environment:**
   ```bash
   # If using venv:
   .\ttpython_env\Scripts\Activate.ps1
   
   # If using conda:
   conda activate ttpython
   ```

2. **Navigate to TTPython directory:**
   ```bash
   cd ticktalkpython
   ```

3. **Run an example:**
   ```bash
   python ../examples/01_hello_ttpython.py
   ```

## Example Output

### Example 01: Temperature Monitor
```
[Sensor] Reading #1: 22.34°C
[Converter] 22.34°C = 72.21°F
[Safety] ✓ SAFE - Temperature: 22.34°C / 72.21°F
[Logger] Logged reading #1
[Logger] Total readings logged: 1
```

### Example 02: Weather Station
```
[Temp Sensor] 21.5°C
[Humidity Sensor] 65.3%
[Pressure Sensor] 1015.42 hPa

[Fusion] Weather Report:
  - Temperature: 21.5°C
  - Humidity: 65.3%
  - Pressure: 1015.42 hPa
  - Comfort: Comfortable
  - Forecast: Stable weather
```

## Key Concepts Demonstrated

### @SQify Decorator
Converts Python functions into Stream Queries (computational units):
```python
@SQify
def my_sensor(trigger):
    global sq_state
    # Your code here
    return data
```

### @GRAPHify Decorator
Defines the main program and dataflow connections:
```python
@GRAPHify
def main_program(trigger):
    with TTClock.root() as clock:
        data = my_sensor(trigger)
        result = process(data)
        return result
```

### sq_state
Persistent state that's isolated to each SQ instance:
```python
global sq_state
if sq_state.get('initialized') is None:
    sq_state['initialized'] = True
    sq_state['counter'] = 0
```

## Troubleshooting

**Import Error:**
```
ModuleNotFoundError: No module named 'ticktalk'
```
→ Make sure you're running from inside the `ticktalkpython` directory

**Compilation Error:**
```
Error: Function not SQified
```
→ Make sure all functions called in `@GRAPHify` have `@SQify` decorator

**State Not Persisting:**
```
sq_state values resetting
```
→ Make sure you're using `global sq_state` at the start of your function

## Next Steps

1. Run both examples to see TTPython in action
2. Modify the examples (change sensor ranges, add new processing steps)
3. Create your own simple application
4. Explore the official tutorials in the TTPython repository

## Resources

- **Documentation:** https://ccsg.ece.cmu.edu/ttpython/
- **Quick Reference:** ../QUICK-REFERENCE.md
- **Full Study:** ../COMPREHENSIVE-TTPYTHON-STUDY.md
