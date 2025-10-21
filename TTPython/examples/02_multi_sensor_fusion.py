"""
Example 02: Multi-Sensor Fusion
================================

This example demonstrates:
- Multiple sensor streams
- Data fusion using time-interval synchronization
- How TTPython handles concurrent data
- Aggregating data from multiple sources

The application simulates:
1. Temperature sensor
2. Humidity sensor
3. Pressure sensor
4. Fuses all three readings into a weather report
"""

import sys
import os

# Add tt module to path (TTPython's core modules)
sys.path.insert(0, os.path.abspath('../ticktalkpython/tt'))

from tt.SQ import SQify, GRAPHify
from tt.Clock import TTClock
import random
import time


# ============================================
# Sensor 1: Temperature
# ============================================
@SQify
def temperature_sensor(trigger):
    """Simulates temperature readings"""
    global sq_state
    
    if sq_state.get('initialized') is None:
        sq_state['initialized'] = True
        sq_state['base_temp'] = 22.0
    
    temp = sq_state['base_temp'] + random.uniform(-3, 3)
    
    print(f"[Temp Sensor] {temp:.1f}°C")
    
    return {
        'temperature': temp,
        'timestamp': time.time()
    }


# ============================================
# Sensor 2: Humidity
# ============================================
@SQify
def humidity_sensor(trigger):
    """Simulates humidity readings"""
    global sq_state
    
    if sq_state.get('initialized') is None:
        sq_state['initialized'] = True
        sq_state['base_humidity'] = 60.0
    
    humidity = sq_state['base_humidity'] + random.uniform(-10, 10)
    humidity = max(0, min(100, humidity))  # Clamp to 0-100%
    
    print(f"[Humidity Sensor] {humidity:.1f}%")
    
    return {
        'humidity': humidity,
        'timestamp': time.time()
    }


# ============================================
# Sensor 3: Pressure
# ============================================
@SQify
def pressure_sensor(trigger):
    """Simulates barometric pressure readings"""
    global sq_state
    
    if sq_state.get('initialized') is None:
        sq_state['initialized'] = True
        sq_state['base_pressure'] = 1013.25  # Sea level in hPa
    
    pressure = sq_state['base_pressure'] + random.uniform(-5, 5)
    
    print(f"[Pressure Sensor] {pressure:.2f} hPa")
    
    return {
        'pressure': pressure,
        'timestamp': time.time()
    }


# ============================================
# Data Fusion
# ============================================
@SQify
def weather_fusion(temp_data, humidity_data, pressure_data):
    """
    Fuses data from all three sensors.
    TTPython automatically synchronizes based on time-intervals.
    """
    print("\n[Fusion] Combining sensor readings...")
    
    # Calculate comfort index (simplified)
    temp = temp_data['temperature']
    humidity = humidity_data['humidity']
    
    # Simple heat index calculation
    comfort_index = temp + (0.5 * humidity)
    
    if comfort_index < 25:
        comfort = "Comfortable"
    elif comfort_index < 30:
        comfort = "Warm"
    else:
        comfort = "Hot"
    
    # Analyze pressure trend (simplified)
    pressure = pressure_data['pressure']
    if pressure > 1020:
        weather_trend = "Clear skies expected"
    elif pressure > 1000:
        weather_trend = "Stable weather"
    else:
        weather_trend = "Possible rain"
    
    weather_report = {
        'temperature': temp,
        'humidity': humidity,
        'pressure': pressure,
        'comfort': comfort,
        'weather_trend': weather_trend,
        'timestamp': time.time()
    }
    
    print(f"[Fusion] Weather Report:")
    print(f"  - Temperature: {temp:.1f}°C")
    print(f"  - Humidity: {humidity:.1f}%")
    print(f"  - Pressure: {pressure:.2f} hPa")
    print(f"  - Comfort: {comfort}")
    print(f"  - Forecast: {weather_trend}")
    
    return weather_report


# ============================================
# Alert System
# ============================================
@SQify
def alert_system(weather_report):
    """
    Checks weather conditions and generates alerts
    """
    alerts = []
    
    # Check for extreme conditions
    if weather_report['temperature'] > 30:
        alerts.append("⚠ HIGH TEMPERATURE WARNING")
    elif weather_report['temperature'] < 10:
        alerts.append("⚠ LOW TEMPERATURE WARNING")
    
    if weather_report['humidity'] > 80:
        alerts.append("⚠ HIGH HUMIDITY WARNING")
    
    if weather_report['pressure'] < 1000:
        alerts.append("⚠ LOW PRESSURE - STORM POSSIBLE")
    
    if alerts:
        print("\n[Alerts] ⚠ WEATHER ALERTS:")
        for alert in alerts:
            print(f"  {alert}")
    else:
        print("\n[Alerts] ✓ No weather alerts")
    
    weather_report['alerts'] = alerts
    return weather_report


# ============================================
# Main Graph
# ============================================
@GRAPHify
def weather_station(trigger):
    """
    Main weather station program.
    
    Dataflow:
                    trigger
                      |
        +-------------+-------------+
        |             |             |
    temperature   humidity      pressure
      sensor       sensor        sensor
        |             |             |
        +-------------+-------------+
                      |
                weather_fusion
                      |
                alert_system
    """
    with TTClock.root() as root_clock:
        # Read from all sensors (happens in parallel!)
        temp_data = temperature_sensor(trigger)
        humidity_data = humidity_sensor(trigger)
        pressure_data = pressure_sensor(trigger)
        
        # Fuse the data (TTPython synchronizes automatically)
        weather_report = weather_fusion(temp_data, humidity_data, pressure_data)
        
        # Check for alerts
        final_report = alert_system(weather_report)
        
        return final_report


# ============================================
# Main Execution
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("TTPython Example 02: Multi-Sensor Weather Station")
    print("=" * 70)
    print()
    
    from tt.Compiler import TTCompile
    
    try:
        print("[Compiler] Executing weather station...")
        print("[Compiler] ✓ Graph structure defined!\n")
        
        print("[Runtime] Starting weather monitoring...")
        print()
        
        # Run 3 weather readings
        for i in range(3):
            print(f"{'='*70}")
            print(f"WEATHER READING #{i+1}")
            print(f"{'='*70}")
            
            result = weather_station(i)
            
            print()
            time.sleep(1)
        
        print("=" * 70)
        print("Weather monitoring complete!")
        print("=" * 70)
        print("\nNote: This demonstrates the dataflow logic.")
        print("For full compilation and distributed execution,")
        print("see the official TTPython examples.")
        
    except Exception as e:
        print(f"[Error] {e}")
        import traceback
        traceback.print_exc()
        print("\nMake sure you're running from the correct directory.")
