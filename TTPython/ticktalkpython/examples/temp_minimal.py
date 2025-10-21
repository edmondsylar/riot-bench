# Minimal TTPython example with no imports in SQ functions
from SQ import SQify, GRAPHify
from Clock import TTClock

@SQify
def temp_sensor(trigger):
    global sq_state
    
    # Use simple math instead of random
    if sq_state.get('count') is None:
        sq_state['count'] = 0
    
    sq_state['count'] += 1
    # Simple calculation without any imports
    temp = 20.0 + (sq_state['count'] % 10)
    
    return temp

@SQify
def temp_checker(temp):
    if temp > 25:
        return "HOT"
    elif temp < 15:
        return "COLD"
    else:
        return "OK"

@GRAPHify
def temp_monitor(trigger):
    # No docstring in GRAPHify!
    with TTClock.root() as root_clock:
        temp = temp_sensor(trigger)
        alert = temp_checker(temp)
        return alert
