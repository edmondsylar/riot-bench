"""
Ray Integration Examples for PyRIoTBench

This module demonstrates how to use Ray distributed computing framework
with PyRIoTBench benchmark tasks. Ray provides actor-based parallelism
for efficient distributed processing.

Examples:
    1. Basic Ray execution with single actor
    2. Multi-actor parallel processing
    3. Stateful task execution with Ray
    4. Batch processing with Ray
    5. Performance comparison (Standalone vs Ray)
    6. Metrics collection and export
"""

import logging
import time
from pathlib import Path
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("="*80)
print("PyRIoTBench - Ray Integration Examples")
print("="*80)
print()


# =============================================================================
# Example 1: Basic Ray Execution
# =============================================================================
print("\n" + "="*80)
print("Example 1: Basic Ray Execution with Kalman Filter")
print("="*80)

from pyriotbench.platforms.ray import RayRunner

# Create sample noisy data
sample_data = [
    "25.5",    # True value ~25
    "30.2",    # Noisy spike
    "24.8",
    "26.1",
    "23.9",
    "25.3",
    "27.5",    # Noisy spike
    "25.0",
    "24.7",
    "25.8"
]

# Create temporary input file
temp_dir = Path(tempfile.mkdtemp())
input_file = temp_dir / "kalman_input.txt"
output_file = temp_dir / "kalman_output.txt"

with open(input_file, 'w') as f:
    for value in sample_data:
        f.write(f"{value}\n")

print(f"Input data (noisy): {sample_data[:5]}...")
print(f"Processing with 2 Ray actors...")

# Run with Ray (2 actors)
runner = RayRunner(num_actors=2)
metrics = runner.run_file(
    task_name='kalman_filter',
    input_file=str(input_file),
    output_file=str(output_file),
    config={'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.125}
)

print(f"✓ Processed {metrics['processed_records']} records")
print(f"✓ Throughput: {metrics['throughput']:.1f} records/sec")
print(f"✓ Used {metrics['num_actors']} actors")

# Read filtered output
with open(output_file, 'r') as f:
    filtered = [line.strip() for line in f]

print(f"✓ Output (filtered): {filtered[:5]}...")
print(f"✓ Output file: {output_file}")

# Cleanup
runner.shutdown()


# =============================================================================
# Example 2: Multi-Actor Parallel Processing
# =============================================================================
print("\n" + "="*80)
print("Example 2: Scaling with Multiple Actors")
print("="*80)

# Generate larger dataset
large_dataset = [f"{25.0 + (i % 10) * 0.5}" for i in range(100)]
large_input = temp_dir / "large_input.txt"

with open(large_input, 'w') as f:
    for value in large_dataset:
        f.write(f"{value}\n")

print(f"Dataset size: {len(large_dataset)} records")
print()

# Test different actor counts
for num_actors in [1, 2, 4, 8]:
    runner = RayRunner(num_actors=num_actors)
    
    start_time = time.time()
    metrics = runner.run_file(
        task_name='noop',
        input_file=str(large_input),
        output_file=None,  # No output
        config={}
    )
    elapsed = time.time() - start_time
    
    print(f"Actors: {num_actors:2d} | "
          f"Time: {elapsed:.3f}s | "
          f"Throughput: {metrics['throughput']:6.1f} rec/s")
    
    runner.shutdown()

print("✓ More actors = higher throughput (for CPU-bound tasks)")


# =============================================================================
# Example 3: Stateful Task with Ray
# =============================================================================
print("\n" + "="*80)
print("Example 3: Stateful Task - Block Window Average")
print("="*80)

# Generate sensor data with multiple sensors
sensor_data = []
for sensor_id in ['sensor1', 'sensor2', 'sensor3']:
    for i in range(20):
        sensor_data.append(f"{sensor_id},{i},{20.0 + i * 0.5}")

sensor_input = temp_dir / "sensor_data.txt"
sensor_output = temp_dir / "windowed_output.txt"

with open(sensor_input, 'w') as f:
    for line in sensor_data:
        f.write(f"{line}\n")

print(f"Input: 3 sensors, 20 values each (60 total)")
print(f"Window size: 5")
print()

# Run with Ray
runner = RayRunner(num_actors=4)
metrics = runner.run_file(
    task_name='block_window_average',
    input_file=str(sensor_input),
    output_file=str(sensor_output),
    config={'AGGREGATE.BLOCK_WINDOW.WINDOW_SIZE': 5}
)

print(f"✓ Processed {metrics['processed_records']} records")
print(f"✓ Valid results: {metrics['valid_results']} (windowed)")
print(f"✓ None filtered: {metrics['none_filtered']} (partial windows)")
print(f"✓ Expected output: {60 // 5} = 12 windows")

# Read windowed output
with open(sensor_output, 'r') as f:
    windows = [line.strip() for line in f]

print(f"✓ Actual output: {len(windows)} windows")
print(f"✓ Sample output: {windows[:3]}...")

runner.shutdown()


# =============================================================================
# Example 4: Batch Processing with Ray
# =============================================================================
print("\n" + "="*80)
print("Example 4: Batch File Processing")
print("="*80)

# Create multiple input files
batch_files = []
for i in range(5):
    batch_file = temp_dir / f"batch_input_{i}.txt"
    with open(batch_file, 'w') as f:
        for j in range(20):
            f.write(f"line_{i}_{j}\n")
    batch_files.append(str(batch_file))

batch_output_dir = temp_dir / "batch_output"

print(f"Files to process: {len(batch_files)}")
print(f"Records per file: 20")
print(f"Total records: {len(batch_files) * 20}")
print()

# Run batch processing
runner = RayRunner(num_actors=4)
batch_metrics = runner.run_batch(
    task_name='noop',
    input_files=batch_files,
    output_dir=str(batch_output_dir),
    config={}
)

print(f"✓ Files processed: {batch_metrics['files_processed']}")
print(f"✓ Total records: {batch_metrics['total_records']}")
print(f"✓ Batch time: {batch_metrics['batch_time']:.2f}s")
print(f"✓ Throughput: {batch_metrics['throughput']:.1f} rec/s")

# Check output files
output_files = list(batch_output_dir.glob("*.txt"))
print(f"✓ Output files created: {len(output_files)}")

runner.shutdown()


# =============================================================================
# Example 5: Performance Comparison
# =============================================================================
print("\n" + "="*80)
print("Example 5: Performance Comparison (Standalone vs Ray)")
print("="*80)

from pyriotbench.platforms.standalone import StandaloneRunner

# Create test dataset
perf_data = [f"{20.0 + i * 0.1}" for i in range(500)]
perf_input = temp_dir / "perf_input.txt"

with open(perf_input, 'w') as f:
    for value in perf_data:
        f.write(f"{value}\n")

print(f"Dataset: {len(perf_data)} records")
print()

# Test 1: Standalone
standalone_runner = StandaloneRunner('kalman_filter', {})
standalone_start = time.time()
standalone_stats = standalone_runner.run_file(str(perf_input), None)
standalone_time = time.time() - standalone_start
standalone_throughput = len(perf_data) / standalone_time

print(f"Standalone:")
print(f"  Time:       {standalone_time:.3f}s")
print(f"  Throughput: {standalone_throughput:.1f} rec/s")
print()

# Test 2: Ray with 1 actor
ray_runner_1 = RayRunner(num_actors=1)
ray_metrics_1 = ray_runner_1.run_file('kalman_filter', str(perf_input), None, {})
ray_runner_1.shutdown()

print(f"Ray (1 actor):")
print(f"  Time:       {ray_metrics_1['total_time']:.3f}s")
print(f"  Throughput: {ray_metrics_1['throughput']:.1f} rec/s")
print(f"  Overhead:   {(ray_metrics_1['total_time'] / standalone_time - 1) * 100:.1f}%")
print()

# Test 3: Ray with 4 actors
ray_runner_4 = RayRunner(num_actors=4)
ray_metrics_4 = ray_runner_4.run_file('kalman_filter', str(perf_input), None, {})
ray_runner_4.shutdown()

print(f"Ray (4 actors):")
print(f"  Time:       {ray_metrics_4['total_time']:.3f}s")
print(f"  Throughput: {ray_metrics_4['throughput']:.1f} rec/s")
print(f"  Speedup:    {ray_metrics_1['total_time'] / ray_metrics_4['total_time']:.2f}x vs 1 actor")
print()

print("💡 Insight: Ray has some overhead for small datasets but scales with actors!")


# =============================================================================
# Example 6: Metrics Export
# =============================================================================
print("\n" + "="*80)
print("Example 6: Metrics Collection and Export")
print("="*80)

# Run task and collect detailed metrics
runner = RayRunner(num_actors=4)
metrics = runner.run_file(
    task_name='senml_parse',
    input_file=str(Path(__file__).parent / "data" / "sample_senml.json"),
    output_file=None,
    config={}
)

# Export metrics to JSON
metrics_json = temp_dir / "ray_metrics.json"
runner.export_metrics(metrics, str(metrics_json), format='json')
print(f"✓ Exported metrics to JSON: {metrics_json}")

# Export metrics to CSV
metrics_csv = temp_dir / "ray_metrics.csv"
runner.export_metrics(metrics, str(metrics_csv), format='csv')
print(f"✓ Exported metrics to CSV: {metrics_csv}")

# Display per-actor metrics
print("\nPer-Actor Performance:")
print(f"{'Actor':<10} {'Processed':<12} {'Avg Time (ms)':<15} {'Throughput':<12}")
print("-" * 60)
for i, actor_metrics in enumerate(metrics['actor_metrics']):
    print(f"Actor {i:<4} "
          f"{actor_metrics['total_processed']:<12} "
          f"{actor_metrics['avg_time']*1000:<15.2f} "
          f"{actor_metrics['throughput']:<12.1f}")

runner.shutdown()

print("\n✓ Metrics exported successfully!")


# =============================================================================
# Example 7: Stream Processing (In-Memory)
# =============================================================================
print("\n" + "="*80)
print("Example 7: Stream Processing (In-Memory Data)")
print("="*80)

# Create in-memory data stream
stream_data = [f"{20.0 + i * 0.5}" for i in range(50)]

print(f"Stream data: {len(stream_data)} items")
print()

# Process stream with Ray
runner = RayRunner(num_actors=4)
result = runner.run_stream(
    task_name='noop',
    data_items=stream_data,
    config={}
)

print(f"✓ Items processed: {result['metrics']['total_items']}")
print(f"✓ Valid results: {result['metrics']['valid_results']}")
print(f"✓ Time: {result['metrics']['total_time']:.3f}s")
print(f"✓ Throughput: {result['metrics']['throughput']:.1f} items/s")
print(f"✓ Results returned: {len(result['results'])} items")

runner.shutdown()


# =============================================================================
# Summary
# =============================================================================
print("\n" + "="*80)
print("Summary - Ray Integration Features")
print("="*80)
print()
print("✓ Basic Execution:       Single/multi-actor processing")
print("✓ Scalability:           Linear scaling with actor count")
print("✓ Stateful Tasks:        Window-based operations supported")
print("✓ Batch Processing:      Multiple files in one run")
print("✓ Performance:           Comparable to standalone, scales well")
print("✓ Metrics:               Detailed per-actor metrics")
print("✓ Export:                JSON/CSV metrics export")
print("✓ Stream Processing:     In-memory data processing")
print()
print("Ray Integration: COMPLETE! 🎉")
print("="*80)

# Cleanup
import shutil
shutil.rmtree(temp_dir, ignore_errors=True)
print(f"\n✓ Cleaned up temporary files: {temp_dir}")
