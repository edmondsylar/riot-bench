"""
Helper script to run our custom examples from within TTPython environment.
Run this from the ticktalkpython directory.
"""

import sys
import os

# Ensure tt module is in path (should already be set by __init__.py)
sys.path.insert(0, os.path.abspath('./tt'))

# Import our example  (we'll execute it by importing)
print("=" * 70)
print("TTPython Example Runner")
print("=" * 70)
print()

example_name = input("Which example? (1 for temperature, 2 for weather): ").strip()

if example_name == "1":
    print("\nRunning Example 01: Temperature Monitor")
    print("=" * 70)
    exec(open('../examples/01_hello_ttpython_simple.py').read())
elif example_name == "2":
    print("\nRunning Example 02: Weather Station")
    print("=" * 70)
    exec(open('../examples/02_multi_sensor_simple.py').read())
else:
    print("Invalid choice. Please choose 1 or 2.")
