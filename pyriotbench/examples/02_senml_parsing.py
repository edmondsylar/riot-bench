#!/usr/bin/env python3
"""
Example 02: SenML Parsing

This example demonstrates parsing SenML (Sensor Markup Language) data,
which is commonly used in IoT applications for sensor data exchange.
"""

import json
import logging
from pathlib import Path

from pyriotbench.tasks.parse.senml_parse import SenMLParse
from pyriotbench.platforms.standalone import StandaloneRunner


def example_1_parse_single_senml():
    """Example 1: Parse a single SenML record."""
    print("=" * 60)
    print("Example 1: Parse Single SenML Record")
    print("=" * 60)
    
    # Create and setup task
    task = SenMLParse()
    logger = logging.getLogger('pyriotbench')
    task.setup(logger, config={})
    
    # Sample SenML data (as CSV format with JSON in 'D' column)
    # Format: timestamp,D
    senml_json = {
        "bn": "temperature_sensor_1",
        "bt": 1422748810,
        "e": [
            {"n": "temperature", "v": 23.5, "u": "Cel", "t": 0},
            {"n": "humidity", "v": 65.2, "u": "%RH", "t": 1}
        ]
    }
    
    # Wrap in CSV format (how it comes from input file)
    csv_line = f"1422748810,{json.dumps(senml_json)}"
    
    print(f"\nInput CSV line:")
    print(f"  {csv_line[:80]}...")
    
    # Parse the data
    result = task.execute(csv_line)
    
    if result.success:
        parsed = task.get_last_result()
        print(f"\nParsed SenML data:")
        print(f"  Base name: {parsed.get('bn', 'N/A')}")
        print(f"  Base time: {parsed.get('bt', 'N/A')}")
        print(f"  Measurements: {len(parsed.get('e', []))}")
        
        for i, measurement in enumerate(parsed.get('e', [])):
            print(f"\n  Measurement {i+1}:")
            print(f"    Name: {measurement.get('n', 'N/A')}")
            print(f"    Value: {measurement.get('v', 'N/A')}")
            print(f"    Unit: {measurement.get('u', 'N/A')}")
            print(f"    Time offset: {measurement.get('t', 0)}")
        
        print(f"\n  Execution time: {result.execution_time_ms:.3f}ms")
    else:
        print(f"❌ Parse failed: {result.error}")
    
    task.tear_down()
    print()


def example_2_parse_taxi_data():
    """Example 2: Parse TAXI dataset SenML format."""
    print("=" * 60)
    print("Example 2: Parse TAXI Dataset SenML")
    print("=" * 60)
    
    # Create task
    task = SenMLParse()
    task.setup()
    
    # Sample TAXI data in SenML format
    taxi_senml = {
        "bn": "taxi_001",
        "bt": 1422748800,
        "e": [
            {"n": "medallion", "vs": "89D227B655E5C82AECF13C3F540D4CF4"},
            {"n": "pickup_datetime", "vs": "2013-01-01 00:00:00"},
            {"n": "dropoff_datetime", "vs": "2013-01-01 00:02:00"},
            {"n": "trip_time_in_secs", "v": 120},
            {"n": "trip_distance", "v": 0.44, "u": "miles"},
            {"n": "pickup_longitude", "v": -73.956528},
            {"n": "pickup_latitude", "v": 40.716976},
            {"n": "dropoff_longitude", "v": -73.962440},
            {"n": "dropoff_latitude", "v": 40.715008},
            {"n": "fare_amount", "v": 3.50, "u": "USD"}
        ]
    }
    
    csv_line = f"1422748800,{json.dumps(taxi_senml)}"
    
    print("\nParsing TAXI trip data...")
    result = task.execute(csv_line)
    
    if result.success:
        parsed = task.get_last_result()
        print(f"\nTaxi Trip Information:")
        print(f"  Vehicle: {parsed['bn']}")
        print(f"  Timestamp: {parsed['bt']}")
        
        # Extract key measurements
        measurements = {m['n']: m.get('v') or m.get('vs') 
                       for m in parsed['e']}
        
        print(f"  Trip duration: {measurements.get('trip_time_in_secs')} seconds")
        print(f"  Distance: {measurements.get('trip_distance')} miles")
        print(f"  Fare: ${measurements.get('fare_amount')}")
        print(f"  Pickup: ({measurements.get('pickup_latitude')}, "
              f"{measurements.get('pickup_longitude')})")
        print(f"  Dropoff: ({measurements.get('dropoff_latitude')}, "
              f"{measurements.get('dropoff_longitude')})")
    
    print(f"\nParsed successfully in {result.execution_time_ms:.3f}ms")
    task.tear_down()
    print()


def example_3_batch_parsing():
    """Example 3: Parse multiple SenML records from a file."""
    print("=" * 60)
    print("Example 3: Batch SenML Parsing")
    print("=" * 60)
    
    # Create sample SenML data file
    input_file = Path("example_senml_data.csv")
    output_file = Path("example_senml_parsed.txt")
    metrics_file = Path("example_senml_metrics.json")
    
    print("\nCreating sample SenML data file...")
    
    # Generate sample sensor readings
    with open(input_file, "w") as f:
        for i in range(10):
            senml = {
                "bn": f"sensor_{i % 3}",
                "bt": 1422748800 + i * 60,  # Every minute
                "e": [
                    {"n": "temperature", "v": 20.0 + i * 0.5, "u": "Cel"},
                    {"n": "pressure", "v": 1013.25 + i * 0.1, "u": "hPa"},
                    {"n": "humidity", "v": 60.0 + i * 2, "u": "%RH"}
                ]
            }
            f.write(f"{1422748800 + i * 60},{json.dumps(senml)}\n")
    
    print(f"  Created {input_file} with 10 SenML records")
    
    # Use StandaloneRunner for batch processing
    print("\nProcessing with StandaloneRunner...")
    runner = StandaloneRunner("senml_parse", progress_interval=5)
    
    stats = runner.run_file(
        input_file=input_file,
        output_file=output_file,
        metrics_file=metrics_file
    )
    
    # Print results
    print(f"\nProcessing Statistics:")
    print(f"  Total records: {stats.total_records}")
    print(f"  Successfully parsed: {stats.success_count}")
    print(f"  Failed: {stats.failed_count}")
    print(f"  Success rate: {stats.success_count / stats.total_records * 100:.1f}%")
    print(f"  Total time: {stats.total_time_s:.3f}s")
    print(f"  Throughput: {stats.throughput_per_sec:.2f} records/s")
    
    # Show parsed output sample
    if output_file.exists():
        print(f"\nFirst parsed record:")
        with open(output_file) as f:
            first_line = f.readline()
            if first_line:
                parsed = json.loads(first_line.strip())
                print(f"  {json.dumps(parsed, indent=2)[:200]}...")
    
    # Show metrics sample
    if metrics_file.exists():
        with open(metrics_file) as f:
            metrics = json.load(f)
            print(f"\nMetrics Summary:")
            print(f"  Mean parse time: {metrics['summary']['mean_time_us']:.2f}μs")
            print(f"  P95: {metrics['summary']['p95_us']:.2f}μs")
            print(f"  P99: {metrics['summary']['p99_us']:.2f}μs")
    
    # Cleanup
    input_file.unlink()
    if output_file.exists():
        output_file.unlink()
    if metrics_file.exists():
        metrics_file.unlink()
    
    print()


def example_4_error_handling():
    """Example 4: Handling invalid SenML data."""
    print("=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)
    
    task = SenMLParse()
    task.setup()
    
    # Test various invalid inputs
    test_cases = [
        ("Empty data", ""),
        ("Invalid JSON", "1234567890,{invalid json}"),
        ("Missing D column", "1234567890"),
        ("Valid CSV but not SenML", '1234567890,{"key": "value"}'),
    ]
    
    print("\nTesting error handling:")
    for name, data in test_cases:
        result = task.execute(data)
        status = "✓ Handled" if not result.success else "✗ Unexpected success"
        print(f"  {name:25s}: {status}")
        if result.error:
            print(f"    Error: {str(result.error)[:60]}...")
    
    stats = task.tear_down()
    print(f"\nTask statistics:")
    print(f"  Total parse attempts: {task.parse_count}")
    print(f"  Average time: {stats:.3f}ms")
    print()


def main():
    """Run all SenML parsing examples."""
    print("\n" + "=" * 60)
    print("PyRIoTBench - SenML Parsing Examples")
    print("=" * 60 + "\n")
    
    # Run all examples
    example_1_parse_single_senml()
    example_2_parse_taxi_data()
    example_3_batch_parsing()
    example_4_error_handling()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
    print("\n💡 Tip: Run with CLI commands:")
    print("  pyriotbench run senml_parse input.csv -o output.txt")
    print("  pyriotbench benchmark senml_parse input.csv -m metrics.json")


if __name__ == "__main__":
    main()
