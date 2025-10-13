"""
Accumulator Task Demo - Windowed Data Collection.

Demonstrates the Accumulator task which batches sensor data in fixed windows
for downstream visualization or analysis.
"""

from pyriotbench.core.registry import TaskRegistry
from pyriotbench.platforms.standalone.runner import StandaloneRunner
import pyriotbench.tasks.statistics  # Import to trigger registration

# Example sensor data with multiple obstypes
sensor_data = [
    "sensor_001|TEMP|25.5|1234567890,location1|1234567890",
    "sensor_001|HUM|60.2|1234567891,location1|1234567891",
    "sensor_002|TEMP|26.1|1234567892,location2|1234567892",
    "sensor_001|TEMP|25.8|1234567893,location1|1234567893",
    "sensor_002|HUM|58.9|1234567894,location2|1234567894",
    "sensor_003|TEMP|24.2|1234567895,location3|1234567895",  # Window full here!
    "sensor_003|HUM|62.1|1234567896,location3|1234567896",
]


def parse_sensor_data(line: str) -> dict:
    """Convert pipe-separated sensor data to dict format."""
    parts = line.split('|')
    return {
        'SENSORID': parts[0],
        'OBSTYPE': parts[1],
        'OBSVALUE': parts[2],
        'META': parts[3],
        'TS': parts[4],
    }


def main():
    """Run accumulator demo."""
    print("=" * 70)
    print("Accumulator Task Demo - Windowed Data Batching")
    print("=" * 70)
    
    # Create and configure task
    task = TaskRegistry.create('accumulator')
    task.config = {
        'AGGREGATE.ACCUMULATOR.TUPLE_WINDOW_SIZE': 6,  # Emit every 6 tuples
        'AGGREGATE.ACCUMULATOR.MULTIVALUE_OBSTYPE': '',
        'AGGREGATE.ACCUMULATOR.META_TIMESTAMP_FIELD': 0,
    }
    task.setup()
    
    print(f"\n✓ Task configured: window_size=6")
    print(f"\nProcessing {len(sensor_data)} sensor readings...")
    print("-" * 70)
    
    # Process data
    for i, line in enumerate(sensor_data, 1):
        data_dict = parse_sensor_data(line)
        result = task.execute(data_dict)
        
        print(f"\n[{i}] {data_dict['SENSORID']} - {data_dict['OBSTYPE']}: {data_dict['OBSVALUE']}")
        
        if result is not None:
            # Window full - emit batch
            print(f"\n🎯 Window FULL! Emitting batch:")
            print(f"   Total composite keys: {len(result)}")
            for key, meta_dict in result.items():
                for meta_key, values in meta_dict.items():
                    print(f"   • {key} [{meta_key}]: {len(values)} values")
                    for val, ts in values[:2]:  # Show first 2
                        print(f"     - {val} @ {ts}")
                    if len(values) > 2:
                        print(f"     ... and {len(values) - 2} more")
        else:
            print(f"   Accumulating... ({task.get_current_count()}/6)")
    
    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
