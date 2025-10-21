"""
Example 01: Hello TTPython - Simple Temperature Sensor
======================================================

This is a simple TTPython application that demonstrates:
- Creating Stream Queries with @SQify
- Building a dataflow graph with @GRAPHify
- Using sq_state for persistent state
- Basic sensor simulation

The application simulates a temperature sensor that:
1. Reads temperature values
2. Converts Celsius to Fahrenheit
3. Checks if temperature is in safe range
4. Logs the results
"""

import sys
import os

# Add tt module to path (TTPython's core modules)
# This assumes we're running from within the ticktalkpython directory structure
current_dir = os.path.dirname(os.path.abspath(__file__))
ttpython_root = os.path.join(current_dir, '..', 'ticktalkpython')
tt_path = os.path.join(ttpython_root, 'tt')

if os.path.exists(tt_path):
    sys.path.insert(0, tt_path)
else:
    # Try alternative path if running from ticktalkpython directory
    sys.path.insert(0, os.path.abspath('./tt'))

from tt.SQ import SQify, GRAPHify
from tt.Clock import TTClock
import random
import time


# ============================================
# STEP 1: Create a temperature sensor SQ
# ============================================
@SQify
def temperature_sensor(trigger):
    """
    Simulates a temperature sensor reading.
    Uses sq_state to keep track of reading count.
    """
    global sq_state
    
    # Initialize state on first run
    if sq_state.get('reading_count') is None:
        sq_state['reading_count'] = 0
        sq_state['base_temp'] = 20.0  # Base temperature in Celsius
    
    # Increment reading count
    sq_state['reading_count'] += 1
    
    # Simulate temperature reading with some random variation
    temperature_c = sq_state['base_temp'] + random.uniform(-5, 5)
    
    print(f"[Sensor] Reading #{sq_state['reading_count']}: {temperature_c:.2f}°C")
    
    return {
        'reading_id': sq_state['reading_count'],
        'temperature_c': temperature_c,
        'timestamp': time.time()
    }


# ============================================
# STEP 2: Create a temperature converter SQ
# ============================================
@SQify
def celsius_to_fahrenheit(sensor_data):
    """
    Converts Celsius to Fahrenheit.
    This shows how SQs can transform data.
    """
    temp_c = sensor_data['temperature_c']
    temp_f = (temp_c * 9/5) + 32
    
    print(f"[Converter] {temp_c:.2f}°C = {temp_f:.2f}°F")
    
    # Add Fahrenheit value to the data
    sensor_data['temperature_f'] = temp_f
    return sensor_data


# ============================================
# STEP 3: Create a safety checker SQ
# ============================================
@SQify
def safety_checker(temperature_data):
    """
    Checks if temperature is within safe range.
    Safe range: 15-25°C (59-77°F)
    """
    temp_c = temperature_data['temperature_c']
    temp_f = temperature_data['temperature_f']
    
    # Define safe range
    safe_min_c = 15.0
    safe_max_c = 25.0
    
    is_safe = safe_min_c <= temp_c <= safe_max_c
    status = "✓ SAFE" if is_safe else "⚠ WARNING"
    
    print(f"[Safety] {status} - Temperature: {temp_c:.2f}°C / {temp_f:.2f}°F")
    
    temperature_data['is_safe'] = is_safe
    temperature_data['status'] = status
    
    return temperature_data


# ============================================
# STEP 4: Create a logger SQ
# ============================================
@SQify
def logger(final_data):
    """
    Logs the final processed data.
    This demonstrates the end of the pipeline.
    """
    global sq_state
    
    # Initialize log list on first run
    if sq_state.get('log') is None:
        sq_state['log'] = []
    
    # Add to log
    log_entry = {
        'reading_id': final_data['reading_id'],
        'temperature_c': final_data['temperature_c'],
        'temperature_f': final_data['temperature_f'],
        'is_safe': final_data['is_safe'],
        'timestamp': final_data['timestamp']
    }
    sq_state['log'].append(log_entry)
    
    print(f"[Logger] Logged reading #{final_data['reading_id']}")
    print(f"[Logger] Total readings logged: {len(sq_state['log'])}")
    print("-" * 60)
    
    return final_data


# ============================================
# STEP 5: Define the dataflow graph
# ============================================
@GRAPHify
def temperature_monitor(trigger):
    """
    Main program that connects all SQs into a pipeline.
    
    Dataflow:
    trigger → temperature_sensor → celsius_to_fahrenheit 
           → safety_checker → logger
    """
    with TTClock.root() as root_clock:
        # Build the pipeline by calling SQified functions
        # Each function call creates a connection in the dataflow graph
        
        sensor_data = temperature_sensor(trigger)
        converted_data = celsius_to_fahrenheit(sensor_data)
        checked_data = safety_checker(converted_data)
        final_data = logger(checked_data)
        
        # The return value can be used for testing/verification
        return final_data


# ============================================
# MAIN: Run the application
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("TTPython Example 01: Temperature Monitoring System")
    print("=" * 60)
    print()
    
    # Compile the TTPython graph
    print("[Compiler] Compiling TTPython graph...")
    from tt.Compiler import TTCompile
    
    try:
        # Note: TTPython compiles to a graph file, not a Python object
        # For now, we'll just execute the function directly to see the logic
        print("[Compiler] ✓ Executing temperature monitor...")
        print()
        
        print("[Runtime] Starting simulation...")
        print()
        
        # Run 5 sensor readings by calling the function directly
        # (In a real TTPython deployment, this would be compiled and distributed)
        for i in range(5):
            print(f"=== TRIGGER {i+1} ===")
            
            # Call the main function - TTPython will handle the dataflow
            result = temperature_monitor(i)
            
            print()
            time.sleep(0.5)  # Small delay between readings
        
        print("=" * 60)
        print("Simulation complete!")
        print("=" * 60)
        print("\nNote: This is a simplified execution.")
        print("For full TTPython compilation and distributed execution,")
        print("see the official examples in ticktalkpython/examples/")
        
    except Exception as e:
        print(f"[Error] {e}")
        import traceback
        traceback.print_exc()
        print("\nNote: Make sure you're running from the correct directory.")
        print("Try: cd ticktalkpython && python ../examples/01_hello_ttpython.py")
