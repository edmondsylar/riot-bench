#!/usr/bin/env python
"""
Example: Running NoOpTask with TTPython Platform Adapter
===========================================================

This example demonstrates how to use the TTPython platform adapter to run
PyRIoTBench tasks. This is Goal 1 from the TTPython-PyRIoTBench Integration Plan:
"Run one PyRIoTBench task (e.g., NoOperationTask) as a TTPython SQ"

The adapter wraps PyRIoTBench's class-based tasks as TTPython Stream Queries (SQs).
"""

import sys
import os

# Add pyriotbench to path
sys.path.insert(0, os.path.abspath('.'))

from pyriotbench.tasks.noop import NoOpTask
from pyriotbench.platforms.ttpython import TTPythonRunner, wrap_task_as_sq


def main():
    print("=" * 70)
    print("TTPython-PyRIoTBench Integration Example")
    print("Goal 1: Run NoOpTask as a TTPython Stream Query")
    print("=" * 70)
    print()
    
    # Step 1: Create the TTPython runner
    print("Step 1: Initialize TTPython Runner")
    config = {}
    runner = TTPythonRunner(config=config)
    print("  ✓ Runner created")
    print()
    
    # Step 2: Wrap NoOpTask as a TTPython SQ
    print("Step 2: Wrap NoOpTask as TTPython Stream Query")
    noop_sq = wrap_task_as_sq(NoOpTask, config)
    print(f"  ✓ Created SQ: {noop_sq.__name__}")
    print(f"  ✓ SQ is callable: {callable(noop_sq)}")
    print()
    
    # Step 3: Create a pipeline
    print("Step 3: Create TTPython Pipeline")
    task_sqs, pipeline_func = runner.create_pipeline([NoOpTask])
    print(f"  ✓ Pipeline created: {pipeline_func.__name__}")
    print(f"  ✓ Number of SQs in pipeline: {len(task_sqs)}")
    print()
    
    # Step 4: Execute the pipeline with test data
    print("Step 4: Execute Pipeline with Test Data")
    input_data = [1, 2, 3, 42, 100]
    print(f"  Input: {input_data}")
    
    results = runner.run(task_sqs, pipeline_func, input_data)
    print(f"  Output: {results}")
    print()
    
    # Step 5: Verify results
    print("Step 5: Verify Results")
    if results == input_data:
        print("  ✓ SUCCESS: NoOpTask correctly passed through all values")
        print("  ✓ The TTPython adapter is working correctly!")
    else:
        print("  ✗ ERROR: Results don't match expected output")
        return 1
    
    print()
    print("=" * 70)
    print("✓ Goal 1 COMPLETE: NoOpTask successfully runs as TTPython SQ")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
