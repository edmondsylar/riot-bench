#!/usr/bin/env python
"""
Example: Using TTPython CLI to Run Benchmarks
==============================================

This example demonstrates how to use the TTPython CLI (TTPyRIoTBench) to run
PyRIoTBench tasks with TTPython's time-sensitive execution framework.

The CLI provides a convenient way to run benchmarks without writing Python code.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a CLI command and display results."""
    print("=" * 70)
    print(f"EXAMPLE: {description}")
    print("=" * 70)
    print(f"Command: {cmd}")
    print()
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.returncode != 0 and result.stderr:
        print("Error:", result.stderr)
        return False
    
    return True


def main():
    print("\n" + "=" * 70)
    print("TTPyRIoTBench CLI Examples")
    print("TTPython Platform for PyRIoTBench Benchmarks")
    print("=" * 70)
    print()
    
    # Change to pyriotbench directory
    os.chdir('/home/runner/work/riot-bench/riot-bench/pyriotbench')
    
    # Example 1: List all TTPython-compatible tasks
    print("\n")
    run_command(
        "python -c \"import sys; sys.path.insert(0, '.'); from pyriotbench.cli.main import cli; cli(['ttpython', 'list'])\"",
        "List all tasks that can run on TTPython"
    )
    
    # Example 2: Get help for TTPython commands
    print("\n")
    run_command(
        "python -c \"import sys; sys.path.insert(0, '.'); from pyriotbench.cli.main import cli; cli(['ttpython', '--help'])\"",
        "Show TTPython command help"
    )
    
    # Example 3: Create sample data
    print("\n")
    print("=" * 70)
    print("EXAMPLE: Create sample input data")
    print("=" * 70)
    with open('/tmp/sample_data.txt', 'w') as f:
        for i in range(10):
            f.write(f"{i * 10}\n")
    print("Created /tmp/sample_data.txt with 10 values")
    print()
    
    # Example 4: Run NoOpTask with TTPython
    print("\n")
    run_command(
        "python -c \"import sys; sys.path.insert(0, '.'); from pyriotbench.cli.main import cli; cli(['ttpython', 'run', 'noop', '/tmp/sample_data.txt', '-o', '/tmp/output.txt'])\"",
        "Run NoOpTask with TTPython"
    )
    
    # Example 5: Show output
    print("\n")
    print("=" * 70)
    print("EXAMPLE: Verify output")
    print("=" * 70)
    with open('/tmp/output.txt', 'r') as f:
        output = f.read()
    print("Output file contents:")
    print(output)
    
    print("\n" + "=" * 70)
    print("✓ All examples completed successfully!")
    print("=" * 70)
    print()
    print("Key Commands:")
    print("  pyriotbench ttpython list                    - List available tasks")
    print("  pyriotbench ttpython run <task> <input>      - Run a task")
    print("  pyriotbench ttpython run <task> <input> -o <output>  - Save results")
    print()


if __name__ == "__main__":
    main()
