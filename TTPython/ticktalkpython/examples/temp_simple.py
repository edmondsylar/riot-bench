# Simple TTPython Temperature Example
# Place this in ticktalkpython/examples/ directory
# Compile: python compile.py examples/temp_simple
# Run: python simulate.py output/temp_simple.pickle

from SQ import SQify, GRAPHify
from Clock import TTClock
from Instructions import *

@SQify
def temp_sensor(trigger):
    """Simple temperature sensor"""
    global sq_state
    if sq_state.get('count') == None:
        sq_state['count'] = 0
    
    sq_state['count'] += 1
    temp = 20 + sq_state['count']  # Simple increment
    
    return temp

@SQify
def temp_checker(temperature):
    """Check if temp is safe"""
    global sq_state
    if sq_state.get('alerts') == None:
        sq_state['alerts'] = 0
    
    if temperature > 25:
        sq_state['alerts'] += 1
        return True  # Alert!
    return False  # OK

@GRAPHify
def temp_monitor(trigger):
    # Main monitoring program
    with TTClock.root() as root_clock:
        temp = temp_sensor(trigger)
        alert = temp_checker(temp)
        return alert
