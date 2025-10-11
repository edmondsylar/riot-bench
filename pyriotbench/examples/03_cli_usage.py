#!/usr/bin/env python3
"""
Example 03: CLI Usage

This example demonstrates various CLI commands available in PyRIoTBench.
Run this script to see the commands, or execute them directly in your terminal.
"""


def print_cli_examples():
    """Print CLI usage examples."""
    
    print("\n" + "=" * 70)
    print("PyRIoTBench - CLI Usage Examples")
    print("=" * 70)
    
    print("\n[LISTING TASKS]")
    print("-" * 70)
    print("\n# List all available tasks")
    print("pyriotbench list-tasks")
    print("\n# List with descriptions")
    print("pyriotbench list-tasks --verbose")
    
    print("\n\n[RUNNING TASKS]")
    print("-" * 70)
    print("\n# Basic execution (output to stdout)")
    print("pyriotbench run noop input.txt")
    
    print("\n# With output file")
    print("pyriotbench run noop input.txt -o output.txt")
    print("pyriotbench run noop input.txt --output output.txt")
    
    print("\n# With configuration file")
    print("pyriotbench run noop input.txt -c config.yaml")
    print("pyriotbench run noop input.txt --config config.yaml")
    
    print("\n# With progress reporting")
    print("pyriotbench run noop input.txt --progress-interval 1000")
    
    print("\n# Complex example with all options")
    print("pyriotbench run senml_parse data.csv \\")
    print("    -o parsed.txt \\")
    print("    -c config.yaml \\")
    print("    --progress-interval 5000")
    
    print("\n\n[BENCHMARKING]")
    print("-" * 70)
    print("\n# Run with metrics collection (--metrics is required)")
    print("pyriotbench benchmark noop input.txt -m metrics.json")
    
    print("\n# With output and metrics")
    print("pyriotbench benchmark noop input.txt \\")
    print("    -o output.txt \\")
    print("    -m metrics.json")
    
    print("\n# Benchmark SenML parsing")
    print("pyriotbench benchmark senml_parse data.csv \\")
    print("    -o parsed.txt \\")
    print("    -m senml_metrics.json \\")
    print("    --progress-interval 1000")
    
    print("\n\n[BATCH PROCESSING]")
    print("-" * 70)
    print("\n# Process multiple files")
    print("pyriotbench batch noop file1.txt file2.txt file3.txt \\")
    print("    -o output_dir/")
    
    print("\n# With wildcards")
    print("pyriotbench batch noop data/*.txt -o output_dir/")
    
    print("\n# With metrics for each file")
    print("pyriotbench batch noop file1.txt file2.txt \\")
    print("    -o output_dir/ \\")
    print("    -m metrics_dir/")
    
    print("\n# Batch process with configuration")
    print("pyriotbench batch senml_parse data/*.csv \\")
    print("    -o parsed_dir/ \\")
    print("    -m metrics_dir/ \\")
    print("    -c config.yaml")
    
    print("\n\n[HELP & VERSION]")
    print("-" * 70)
    print("\n# Show general help")
    print("pyriotbench --help")
    
    print("\n# Show version")
    print("pyriotbench --version")
    
    print("\n# Help for specific command")
    print("pyriotbench run --help")
    print("pyriotbench benchmark --help")
    print("pyriotbench batch --help")
    
    print("\n\n[CONFIGURATION FILES]")
    print("-" * 70)
    print("\n# YAML configuration (config.yaml):")
    print("""
name: my_benchmark
input_file: data/input.txt
output_file: data/output.txt
log_level: INFO
progress_interval: 1000

platform_config:
  platform: standalone
  parallelism: 4

tasks:
  - task_name: senml_parse
    enabled: true
    config_params:
      validate: true
""")
    
    print("\n# Properties configuration (config.properties):")
    print("""
name=my_benchmark
input_file=data/input.txt
output_file=data/output.txt
log_level=INFO

platform_config.platform=standalone
platform_config.parallelism=4

tasks.0.task_name=senml_parse
tasks.0.enabled=true
""")
    
    print("\n\n[METRICS OUTPUT]")
    print("-" * 70)
    print("\n# Metrics JSON structure:")
    print("""
{
  "task_name": "noop",
  "summary": {
    "count": 1000,
    "success_count": 1000,
    "error_count": 0,
    "success_rate": 1.0,
    "mean_time_us": 2.5,
    "median_time_us": 2.3,
    "min_time_us": 1.2,
    "max_time_us": 8.7,
    "stddev_time_us": 1.1,
    "p50_us": 2.3,
    "p95_us": 4.5,
    "p99_us": 6.2
  },
  "metrics": [
    {
      "task_name": "noop",
      "execution_time_us": 2.5,
      "timestamp": "2025-10-10T12:00:00.000Z",
      "status": "success"
    },
    ...
  ]
}
""")
    
    print("\n\n[COMMON WORKFLOWS]")
    print("-" * 70)
    
    print("\n1. Quick Test Run:")
    print("""
# Create test data
echo -e "line1\\nline2\\nline3" > test.txt

# Run noop task
pyriotbench run noop test.txt -o output.txt

# Check output
cat output.txt
""")
    
    print("\n2. Performance Benchmark:")
    print("""
# Generate larger dataset
for i in {1..10000}; do echo "record $i"; done > large_data.txt

# Benchmark with metrics
pyriotbench benchmark noop large_data.txt \\
    -o processed.txt \\
    -m metrics.json

# View metrics summary
cat metrics.json | jq '.summary'
""")
    
    print("\n3. SenML Data Processing:")
    print("""
# Parse SenML data
pyriotbench run senml_parse senml_data.csv \\
    -o parsed.txt \\
    --progress-interval 1000

# With metrics
pyriotbench benchmark senml_parse senml_data.csv \\
    -o parsed.txt \\
    -m senml_metrics.json
""")
    
    print("\n4. Batch Processing Pipeline:")
    print("""
# Process all CSV files in a directory
pyriotbench batch senml_parse data/*.csv \\
    -o parsed_output/ \\
    -m metrics/ \\
    --progress-interval 5000

# Check results
ls -lh parsed_output/
ls -lh metrics/
""")
    
    print("\n\n[TIPS & TRICKS]")
    print("-" * 70)
    print("""
1. Use --progress-interval to see progress on large files
   pyriotbench run noop large.txt --progress-interval 10000

2. Pipe output to other tools
   pyriotbench run noop input.txt | grep "pattern"

3. Use configuration files for complex setups
   pyriotbench run senml_parse data.csv -c production.yaml

4. Benchmark mode always requires --metrics flag
   pyriotbench benchmark noop input.txt -m metrics.json

5. Batch mode creates output files with same names
   input: data/file1.txt -> output: output_dir/file1.txt

6. View metrics with jq for better formatting
   cat metrics.json | jq '.summary'
""")
    
    print("\n" + "=" * 70)
    print("For more information, visit:")
    print("  GitHub: https://github.com/edmondsylar/riot-bench")
    print("  Docs: ../pyDocs/")
    print("=" * 70 + "\n")


def main():
    """Main function."""
    print_cli_examples()


if __name__ == "__main__":
    main()
