#!/usr/bin/env python3
"""
Example 01: Simple Task Usage

This example demonstrates the basic usage of PyRIoTBench tasks
using the NoOperation task as a simple example.
"""

import logging
from pathlib import Path

from pyriotbench.tasks.noop import NoOpTask
from pyriotbench.platforms.standalone import StandaloneRunner
from pyriotbench.core.metrics import MetricsAggregator


def example_1_direct_task_usage():
    """Example 1: Using a task directly."""
    print("=" * 60)
    print("Example 1: Direct Task Usage")
    print("=" * 60)
    
    # Create task instance
    task = NoOpTask()
    
    # Setup task (optional for noop)
    logger = logging.getLogger('pyriotbench')
    task.setup(logger, config={})
    
    # Execute task multiple times
    test_data = ["line 1", "line 2", "line 3"]
    
    for data in test_data:
        result = task.execute(data)
        print(f"Input: {data:10s} -> Output: {result.value:10s} "
              f"(took {result.execution_time_ms:.3f}ms)")
    
    # Teardown
    task.tear_down()
    print()


def example_2_with_metrics():
    """Example 2: Using task with metrics collection."""
    print("=" * 60)
    print("Example 2: Task with Metrics Collection")
    print("=" * 60)
    
    # Create task and metrics aggregator
    task = NoOpTask()
    task.setup()
    
    aggregator = MetricsAggregator("noop")
    
    # Process data and collect metrics
    test_data = ["data1", "data2", "data3", "data4", "data5"]
    
    for data in test_data:
        result = task.execute(data)
        
        # Create metric from result
        from pyriotbench.core.metrics import create_metric
        metric = create_metric(
            task_name="noop",
            execution_time_us=result.execution_time_us,
            success=result.success
        )
        aggregator.add_metric(metric)
    
    # Print statistics
    print(f"\nStatistics:")
    print(f"  Total executions: {aggregator.count}")
    print(f"  Success rate: {aggregator.success_rate * 100:.1f}%")
    print(f"  Mean time: {aggregator.mean_time_us:.2f}μs")
    print(f"  Median time: {aggregator.median_time_us:.2f}μs")
    print(f"  P95: {aggregator.percentile_us(95):.2f}μs")
    print(f"  P99: {aggregator.percentile_us(99):.2f}μs")
    
    # Export metrics to JSON
    summary = aggregator.summary()
    print(f"\nSummary: {summary}")
    
    task.tear_down()
    print()


def example_3_standalone_runner():
    """Example 3: Using the StandaloneRunner."""
    print("=" * 60)
    print("Example 3: Standalone Runner")
    print("=" * 60)
    
    # Create sample input file
    input_file = Path("example_input.txt")
    output_file = Path("example_output.txt")
    metrics_file = Path("example_metrics.json")
    
    # Write test data
    with open(input_file, "w") as f:
        for i in range(10):
            f.write(f"test record {i}\n")
    
    # Create runner
    runner = StandaloneRunner("noop", progress_interval=5)
    
    # Run with metrics
    stats = runner.run_file(
        input_file=input_file,
        output_file=output_file,
        metrics_file=metrics_file
    )
    
    # Print statistics
    print(f"\nExecution Statistics:")
    print(f"  Total records: {stats.total_records}")
    print(f"  Success: {stats.success_count}")
    print(f"  Failed: {stats.failed_count}")
    print(f"  Total time: {stats.total_time_s:.3f}s")
    print(f"  Throughput: {stats.throughput_per_sec:.2f} records/s")
    
    # Cleanup
    input_file.unlink()
    if output_file.exists():
        output_file.unlink()
    if metrics_file.exists():
        metrics_file.unlink()
    
    print()


def example_4_batch_processing():
    """Example 4: Batch processing multiple files."""
    print("=" * 60)
    print("Example 4: Batch Processing")
    print("=" * 60)
    
    # Create multiple input files
    input_files = []
    for i in range(3):
        file_path = Path(f"example_input_{i}.txt")
        with open(file_path, "w") as f:
            for j in range(5):
                f.write(f"file{i}_record{j}\n")
        input_files.append(file_path)
    
    # Create output directory
    output_dir = Path("example_output")
    output_dir.mkdir(exist_ok=True)
    
    # Create runner and run batch
    runner = StandaloneRunner("noop")
    
    all_stats = runner.run_batch(
        input_files=input_files,
        output_dir=output_dir
    )
    
    # Print results
    print(f"\nProcessed {len(all_stats)} files:")
    for i, stats in enumerate(all_stats):
        print(f"  File {i}: {stats.total_records} records, "
              f"{stats.throughput_per_sec:.2f} rec/s")
    
    # Cleanup
    for file in input_files:
        file.unlink()
    for file in output_dir.glob("*"):
        file.unlink()
    output_dir.rmdir()
    
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("PyRIoTBench - Simple Task Usage Examples")
    print("=" * 60 + "\n")
    
    # Run all examples
    example_1_direct_task_usage()
    example_2_with_metrics()
    example_3_standalone_runner()
    example_4_batch_processing()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
