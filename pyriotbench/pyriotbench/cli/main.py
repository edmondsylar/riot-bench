"""
Command-line interface for PyRIoTBench.

This module provides a Click-based CLI for running benchmarks, listing tasks,
and managing configurations.

Example:
    # List all registered tasks
    $ pyriotbench list-tasks
    
    # Run a task
    $ pyriotbench run noop input.txt -o output.txt
    
    # Run with config file
    $ pyriotbench run senml_parse data.json -c config.yaml
    
    # Run with metrics export
    $ pyriotbench benchmark noop input.txt -m metrics.json
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import click

from pyriotbench.core import list_tasks, create_task
from pyriotbench.platforms.standalone import StandaloneRunner

# Auto-import tasks to register them
import pyriotbench.tasks.noop  # noqa: F401
import pyriotbench.tasks.parse.senml_parse  # noqa: F401


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="PyRIoTBench")
def cli():
    """
    PyRIoTBench - Python IoT Stream Processing Benchmarks
    
    A multi-platform benchmarking suite for IoT stream processing tasks.
    Port of the Java RIoTBench framework with support for Apache Beam,
    Apache Flink, Ray, and standalone execution.
    """
    pass


@cli.command("list-tasks")
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Show detailed task information'
)
def list_tasks_command(verbose: bool):
    """List all registered benchmark tasks.
    
    Shows all tasks that have been registered with the TaskRegistry.
    Use --verbose to see additional details about each task.
    
    Example:
        $ pyriotbench list-tasks
        $ pyriotbench list-tasks --verbose
    """
    tasks = list_tasks()
    
    if not tasks:
        click.echo("No tasks registered.", err=True)
        sys.exit(1)
    
    click.echo(f"\n{'='*60}")
    click.echo(f"Registered Tasks ({len(tasks)} total)")
    click.echo(f"{'='*60}\n")
    
    for task_name in sorted(tasks):
        if verbose:
            try:
                task_class = create_task(task_name).__class__
                doc = task_class.__doc__ or "No description available"
                # Get first line of docstring
                doc_line = doc.strip().split('\n')[0]
                click.echo(f"  • {task_name}")
                click.echo(f"    {doc_line}")
                click.echo()
            except Exception as e:
                click.echo(f"  • {task_name}")
                click.echo(f"    Error loading task: {e}")
                click.echo()
        else:
            click.echo(f"  • {task_name}")
    
    click.echo()


@cli.command("run")
@click.argument('task_name')
@click.argument('input_file', type=click.Path(exists=True))
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Output file path (default: stdout)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='Configuration file (YAML or properties)'
)
@click.option(
    '--progress/--no-progress',
    default=True,
    help='Show progress reporting (default: enabled)'
)
@click.option(
    '--progress-interval',
    type=int,
    default=1000,
    help='Progress reporting interval in records (default: 1000)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
def run_command(
    task_name: str,
    input_file: str,
    output: Optional[str],
    config: Optional[str],
    progress: bool,
    progress_interval: int,
    verbose: bool
):
    """Run a benchmark task on an input file.
    
    Executes the specified task using the standalone runner.
    Input is processed line-by-line and results are written to
    the output file (or stdout if not specified).
    
    Example:
        $ pyriotbench run noop input.txt
        $ pyriotbench run noop input.txt -o output.txt
        $ pyriotbench run senml_parse data.json -o parsed.txt -c config.yaml
    """
    # Setup logging
    if verbose:
        logging.getLogger('pyriotbench').setLevel(logging.DEBUG)
    
    # Load config if provided
    task_config = {}
    if config:
        from pyriotbench.core import BenchmarkConfig
        try:
            bench_config = BenchmarkConfig.from_yaml(config)
            if bench_config.tasks:
                task_config = bench_config.tasks[0].config_params
        except Exception as e:
            click.echo(f"Error loading config: {e}", err=True)
            sys.exit(1)
    
    # Validate task exists
    if task_name not in list_tasks():
        click.echo(f"Error: Task '{task_name}' not found.", err=True)
        click.echo(f"Available tasks: {', '.join(list_tasks())}", err=True)
        sys.exit(1)
    
    # Create runner
    try:
        runner = StandaloneRunner(
            task_name,
            config=task_config,
            progress_interval=progress_interval if progress else 0
        )
    except Exception as e:
        click.echo(f"Error creating runner: {e}", err=True)
        sys.exit(1)
    
    # Run task
    click.echo(f"\n{'='*60}")
    click.echo(f"Running: {task_name}")
    click.echo(f"Input: {input_file}")
    if output:
        click.echo(f"Output: {output}")
    click.echo(f"{'='*60}\n")
    
    try:
        stats = runner.run(input_file, output)
        
        # Print summary
        click.echo(f"\n{'='*60}")
        click.echo("Execution Summary")
        click.echo(f"{'='*60}")
        click.echo(str(stats))
        click.echo()
        
    except Exception as e:
        click.echo(f"\nError during execution: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command("benchmark")
@click.argument('task_name')
@click.argument('input_file', type=click.Path(exists=True))
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Output file path'
)
@click.option(
    '--metrics', '-m',
    type=click.Path(),
    required=True,
    help='Metrics output file (JSON format)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='Configuration file (YAML or properties)'
)
@click.option(
    '--progress-interval',
    type=int,
    default=1000,
    help='Progress reporting interval (default: 1000)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
def benchmark_command(
    task_name: str,
    input_file: str,
    output: Optional[str],
    metrics: str,
    config: Optional[str],
    progress_interval: int,
    verbose: bool
):
    """Run a benchmark with full metrics collection.
    
    Similar to 'run' but requires metrics export and provides
    detailed performance statistics. Metrics are saved in JSON
    format with aggregate statistics and individual measurements.
    
    Example:
        $ pyriotbench benchmark noop input.txt -m metrics.json
        $ pyriotbench benchmark noop input.txt -o out.txt -m metrics.json
    """
    # Setup logging
    if verbose:
        logging.getLogger('pyriotbench').setLevel(logging.DEBUG)
    
    # Load config if provided
    task_config = {}
    if config:
        from pyriotbench.core import BenchmarkConfig
        try:
            bench_config = BenchmarkConfig.from_yaml(config)
            if bench_config.tasks:
                task_config = bench_config.tasks[0].config_params
        except Exception as e:
            click.echo(f"Error loading config: {e}", err=True)
            sys.exit(1)
    
    # Validate task exists
    if task_name not in list_tasks():
        click.echo(f"Error: Task '{task_name}' not found.", err=True)
        click.echo(f"Available tasks: {', '.join(list_tasks())}", err=True)
        sys.exit(1)
    
    # Create runner
    try:
        runner = StandaloneRunner(
            task_name,
            config=task_config,
            progress_interval=progress_interval
        )
    except Exception as e:
        click.echo(f"Error creating runner: {e}", err=True)
        sys.exit(1)
    
    # Run benchmark
    click.echo(f"\n{'='*60}")
    click.echo(f"Benchmark: {task_name}")
    click.echo(f"Input: {input_file}")
    if output:
        click.echo(f"Output: {output}")
    click.echo(f"Metrics: {metrics}")
    click.echo(f"{'='*60}\n")
    
    try:
        stats = runner.run(input_file, output, metrics)
        
        # Print detailed summary
        click.echo(f"\n{'='*60}")
        click.echo("Benchmark Results")
        click.echo(f"{'='*60}")
        click.echo(str(stats))
        click.echo(f"\nMetrics exported to: {metrics}")
        click.echo()
        
    except Exception as e:
        click.echo(f"\nError during benchmark: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command("batch")
@click.argument('task_name')
@click.argument('input_files', nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    '--output-dir', '-o',
    type=click.Path(),
    required=True,
    help='Output directory for results'
)
@click.option(
    '--metrics-dir', '-m',
    type=click.Path(),
    help='Directory for metrics files (JSON format)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='Configuration file (YAML or properties)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
def batch_command(
    task_name: str,
    input_files: tuple,
    output_dir: str,
    metrics_dir: Optional[str],
    config: Optional[str],
    verbose: bool
):
    """Run a task on multiple input files (batch processing).
    
    Processes multiple files and saves results to the output directory.
    Each input file gets a corresponding output file with '_output' suffix.
    
    Example:
        $ pyriotbench batch noop file1.txt file2.txt -o results/
        $ pyriotbench batch noop *.txt -o results/ -m metrics/
    """
    # Setup logging
    if verbose:
        logging.getLogger('pyriotbench').setLevel(logging.DEBUG)
    
    # Load config if provided
    task_config = {}
    if config:
        from pyriotbench.core import BenchmarkConfig
        try:
            bench_config = BenchmarkConfig.from_yaml(config)
            if bench_config.tasks:
                task_config = bench_config.tasks[0].config_params
        except Exception as e:
            click.echo(f"Error loading config: {e}", err=True)
            sys.exit(1)
    
    # Validate task exists
    if task_name not in list_tasks():
        click.echo(f"Error: Task '{task_name}' not found.", err=True)
        click.echo(f"Available tasks: {', '.join(list_tasks())}", err=True)
        sys.exit(1)
    
    # Create runner
    try:
        runner = StandaloneRunner(
            task_name,
            config=task_config,
            progress_interval=1000
        )
    except Exception as e:
        click.echo(f"Error creating runner: {e}", err=True)
        sys.exit(1)
    
    # Run batch
    click.echo(f"\n{'='*60}")
    click.echo(f"Batch Processing: {task_name}")
    click.echo(f"Files: {len(input_files)}")
    click.echo(f"Output: {output_dir}")
    if metrics_dir:
        click.echo(f"Metrics: {metrics_dir}")
    click.echo(f"{'='*60}\n")
    
    try:
        stats_list = runner.run_batch(
            list(input_files),
            output_dir,
            metrics_dir
        )
        
        # Print summary
        total_records = sum(s.total_records for s in stats_list)
        total_time = sum(s.total_time_s for s in stats_list)
        avg_throughput = total_records / total_time if total_time > 0 else 0
        
        click.echo(f"\n{'='*60}")
        click.echo("Batch Summary")
        click.echo(f"{'='*60}")
        click.echo(f"Files processed: {len(stats_list)}")
        click.echo(f"Total records: {total_records}")
        click.echo(f"Total time: {total_time:.2f}s")
        click.echo(f"Average throughput: {avg_throughput:.1f} records/s")
        click.echo()
        
    except Exception as e:
        click.echo(f"\nError during batch processing: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
