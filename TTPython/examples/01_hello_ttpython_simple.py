"""
Example 01: Hello TTPython - Simple Temperature Sensor
======================================================
Run this file from the ticktalkpython directory:
    python run_example.py
    # Or execute directly from tt environment
"""

# These imports work when running from ticktalkpython directory
from SQ import SQify, GRAPHify
from Clock import TTClock
import random
import time


# Temperature Sensor SQ
@SQify
def temperature_sensor(trigger):
    """Simulates a temperature sensor"""
    global sq_state
    
    if sq_state.get('reading_count') is None:
        sq_state['reading_count'] = 0
        sq_state['base_temp'] = 20.0
    
    sq_state['reading_count'] += 1
    temperature_c = sq_state['base_temp'] + random.uniform(-5, 5)
    
    print(f"[Sensor] Reading #{sq_state['reading_count']}: {temperature_c:.2f}°C")
    
    return {
        'reading_id': sq_state['reading_count'],
        'temperature_c': temperature_c,
        'timestamp': time.time()
    }


# Converter SQ
@SQify
def celsius_to_fahrenheit(sensor_data):
    """Converts Celsius to Fahrenheit"""
    temp_c = sensor_data['temperature_c']
    temp_f = (temp_c * 9/5) + 32
    
    print(f"[Converter] {temp_c:.2f}°C = {temp_f:.2f}°F")
    
    sensor_data['temperature_f'] = temp_f
    return sensor_data


# Safety Checker SQ
@SQify
def safety_checker(temperature_data):
    """Checks if temperature is safe (15-25°C)"""
    temp_c = temperature_data['temperature_c']
    temp_f = temperature_data['temperature_f']
    
    is_safe = 15.0 <= temp_c <= 25.0
    status = "✓ SAFE" if is_safe else "⚠ WARNING"
    
    print(f"[Safety] {status} - Temperature: {temp_c:.2f}°C / {temp_f:.2f}°F")
    
    temperature_data['is_safe'] = is_safe
    temperature_data['status'] = status
    
    return temperature_data


# Logger SQ
@SQify
def logger(final_data):
    """Logs the processed data"""
    global sq_state
    
    if sq_state.get('log') is None:
        sq_state['log'] = []
    
    log_entry = {
        'reading_id': final_data['reading_id'],
        'temperature_c': final_data['temperature_c'],
        'temperature_f': final_data['temperature_f'],
        'is_safe': final_data['is_safe']
    }
    sq_state['log'].append(log_entry)
    
    print(f"[Logger] Logged reading #{final_data['reading_id']}")
    print(f"[Logger] Total readings: {len(sq_state['log'])}")
    print("-" * 60)
    
    return final_data


# Main Graph
@GRAPHify
def temperature_monitor(trigger):
    """
    Main program - defines the dataflow pipeline:
    trigger → sensor → converter → checker → logger
    """
    with TTClock.root() as root_clock:
        sensor_data = temperature_sensor(trigger)
        converted_data = celsius_to_fahrenheit(sensor_data)
        checked_data = safety_checker(converted_data)
        final_data = logger(checked_data)
        
        return final_data


# Run the application
if __name__ == "__main__":
    print("=" * 60)
    print("TTPython Example 01: Temperature Monitoring System")
    print("=" * 60)
    print()
    
    print("[Runtime] Starting simulation...")
    print()
    
    # Run 5 sensor readings
    for i in range(5):
        print(f"=== TRIGGER {i+1} ===")
        result = temperature_monitor(i)
        print()
        time.sleep(0.5)
    
    print("=" * 60)
    print("Simulation complete!")
    print("=" * 60)
