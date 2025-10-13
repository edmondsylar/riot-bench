"""
Example: Running RIoTBench tasks with Apache Beam.

This example demonstrates how to use Apache Beam to process IoT sensor data
through RIoTBench tasks. Shows both simple pipelines and batch processing.
"""

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

# Import tasks to trigger registration
import pyriotbench.tasks  # noqa: F401

from pyriotbench.platforms.beam.adapter import BeamTaskDoFn

# Example 1: Simple pipeline with Kalman filter
def example_kalman_filter():
    """Run Kalman filter on sensor data using Beam."""
    print("\n=== Example 1: Kalman Filter Pipeline ===")
    
    # Configure Kalman filter
    config = {
        'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
        'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
    }
    
    # Create pipeline
    with beam.Pipeline() as p:
        # Simulate noisy sensor readings
        noisy_data = [
            '25.2', '26.8', '24.1', '25.9', '26.3',
            '24.7', '25.5', '26.1', '25.0', '24.9'
        ]
        
        results = (
            p
            | 'Create Data' >> beam.Create(noisy_data)
            | 'Kalman Filter' >> beam.ParDo(BeamTaskDoFn('kalman_filter', config))
            | 'Print Results' >> beam.Map(lambda x: print(f"Filtered: {x:.2f}"))
        )
    
    print("Kalman filter pipeline complete!")


# Example 2: Block window average for downsampling
def example_window_average():
    """Downsample sensor data using windowed averaging."""
    print("\n=== Example 2: Block Window Average ===")
    
    # Configure 5-element windows
    config = {
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 5,
    }
    
    # Create pipeline
    with beam.Pipeline() as p:
        # High-frequency sensor data (20 readings)
        high_freq_data = [str(25.0 + i * 0.1) for i in range(20)]
        
        results = (
            p
            | 'Create Data' >> beam.Create(high_freq_data)
            | 'Window Average' >> beam.ParDo(BeamTaskDoFn('block_window_average', config))
            | 'Print Averages' >> beam.Map(lambda x: print(f"Window avg: {x:.2f}"))
        )
    
    print("Window averaging complete!")


# Example 3: Chain multiple tasks
def example_task_chain():
    """Chain Kalman filter and window average."""
    print("\n=== Example 3: Task Chaining ===")
    
    kalman_config = {
        'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
        'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
    }
    
    window_config = {
        'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 3,
    }
    
    # Create pipeline with chained processing
    with beam.Pipeline() as p:
        noisy_data = [str(25.0 + (i % 5 - 2) * 0.5) for i in range(12)]
        
        results = (
            p
            | 'Create Data' >> beam.Create(noisy_data)
            | 'Kalman Filter' >> beam.ParDo(BeamTaskDoFn('kalman_filter', kalman_config))
            | 'Convert to String' >> beam.Map(str)  # Convert float back to string
            | 'Window Average' >> beam.ParDo(BeamTaskDoFn('block_window_average', window_config))
            | 'Print Final' >> beam.Map(lambda x: print(f"Final result: {x:.2f}"))
        )
    
    print("Chained pipeline complete!")


# Example 4: File-based processing
def example_file_processing():
    """Process sensor data from file using Beam."""
    print("\n=== Example 4: File-Based Processing ===")
    
    import tempfile
    from pathlib import Path
    
    # Create temporary input file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("25.0\n26.1\n24.8\n25.5\n26.2\n")
        input_file = f.name
    
    output_file = Path(input_file).with_suffix('.out.txt')
    
    config = {
        'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
        'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
    }
    
    # Create file processing pipeline
    with beam.Pipeline() as p:
        results = (
            p
            | 'Read File' >> beam.io.ReadFromText(input_file)
            | 'Kalman Filter' >> beam.ParDo(BeamTaskDoFn('kalman_filter', config))
            | 'Format Output' >> beam.Map(lambda x: f"{x:.4f}")
            | 'Write File' >> beam.io.WriteToText(
                str(output_file),
                shard_name_template='',
                num_shards=1
            )
        )
    
    # Read and display results
    actual_output = Path(str(output_file) + '-00000-of-00001')
    if actual_output.exists():
        print(f"\nResults written to: {actual_output}")
        with open(actual_output, 'r') as f:
            for line in f:
                print(f"  {line.strip()}")
        
        # Cleanup
        actual_output.unlink()
    
    Path(input_file).unlink()
    print("File processing complete!")


# Example 5: Parallel processing with Beam
def example_parallel_processing():
    """Demonstrate parallel processing with multiple workers."""
    print("\n=== Example 5: Parallel Processing ===")
    
    # Configure DirectRunner with multiple workers
    options = PipelineOptions(
        runner='DirectRunner',
        direct_num_workers=4,  # Use 4 worker threads
        direct_running_mode='multi_threading'
    )
    
    config = {
        'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
        'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
    }
    
    # Process large dataset
    with beam.Pipeline(options=options) as p:
        # Create large dataset (1000 readings)
        large_dataset = [str(25.0 + (i % 10) * 0.1) for i in range(1000)]
        
        results = (
            p
            | 'Create Data' >> beam.Create(large_dataset)
            | 'Kalman Filter' >> beam.ParDo(BeamTaskDoFn('kalman_filter', config))
            | 'Count' >> beam.combiners.Count.Globally()
            | 'Print Count' >> beam.Map(lambda x: print(f"Processed {x} elements in parallel"))
        )
    
    print("Parallel processing complete!")


def main():
    """Run all examples."""
    print("=" * 60)
    print("RIoTBench + Apache Beam Examples")
    print("=" * 60)
    
    example_kalman_filter()
    example_window_average()
    example_task_chain()
    example_file_processing()
    example_parallel_processing()
    
    print("\n" + "=" * 60)
    print("All examples complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
