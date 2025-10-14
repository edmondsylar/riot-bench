"""
Flink Runner - Execute benchmark pipelines using PyFlink DataStream API.

This runner orchestrates task execution using Apache Flink's streaming engine,
enabling scalable distributed processing of IoT workloads.
"""

import logging
import time
from pathlib import Path
from typing import Any, Optional, Dict, List
import json

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.file_system import FileSource, FileSink, StreamFormat
from pyflink.common import Types, WatermarkStrategy

from pyriotbench.platforms.flink.adapter import FlinkTaskMapFunction
from pyriotbench.core.registry import TaskRegistry


class FlinkRunner:
    """
    Execute benchmark tasks using Apache Flink's DataStream API.
    
    This runner:
    - Creates Flink execution environment
    - Builds DataStream pipelines with task MapFunctions
    - Handles file I/O and stream processing
    - Collects execution metrics
    - Supports both local and cluster execution
    
    Usage:
        runner = FlinkRunner()
        metrics = runner.run_file('noop', 'input.txt', 'output.txt')
    
    Attributes:
        parallelism: Degree of parallelism for task execution
        env: Flink StreamExecutionEnvironment
        _logger: Logger for this runner
    """
    
    def __init__(self, parallelism: int = 4):
        """
        Initialize the Flink runner.
        
        Args:
            parallelism: Degree of parallelism (default: 4)
        """
        self.parallelism = parallelism
        self._logger = logging.getLogger("FlinkRunner")
        
        # Create Flink execution environment
        self.env = StreamExecutionEnvironment.get_execution_environment()
        self.env.set_parallelism(parallelism)
        
        self._logger.info(f"FlinkRunner initialized with parallelism={parallelism}")
    
    def run_file(
        self,
        task_name: str,
        input_file: str,
        output_file: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a task on data from a file using Flink DataStream.
        
        Args:
            task_name: Name of registered task to execute
            input_file: Path to input file (one record per line)
            output_file: Path to output file (optional)
            config: Configuration dictionary for task
        
        Returns:
            Dictionary with metrics:
                - total_records: Number of input records
                - processed_records: Number successfully processed
                - total_time: Total execution time
                - throughput: Records per second
        
        Example:
            runner = FlinkRunner(parallelism=4)
            metrics = runner.run_file('senml_parse', 'data.txt', 'output.txt')
        """
        start_time = time.time()
        
        # Validate task
        if not TaskRegistry.is_registered(task_name):
            raise ValueError(
                f"Task '{task_name}' not registered. "
                f"Available: {', '.join(TaskRegistry.list_tasks())}"
            )
        
        # Validate input file
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Count input records
        with open(input_path, 'r') as f:
            total_records = sum(1 for line in f if line.strip())
        
        self._logger.info(
            f"Running task '{task_name}' on {total_records} records from {input_file}"
        )
        
        # Create DataStream from file
        ds = self.env.read_text_file(str(input_path))
        
        # Apply task MapFunction
        map_fn = FlinkTaskMapFunction(task_name, config)
        result_ds = ds.map(map_fn)
        
        # Write output if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            result_ds.write_as_text(str(output_path), mode='OVERWRITE')
            self._logger.info(f"Output will be written to {output_file}")
        else:
            # Just print for validation
            result_ds.print()
        
        # Execute the pipeline
        try:
            self.env.execute(f"PyRIoTBench-{task_name}")
            execution_time = time.time() - start_time
            
            # Build metrics
            throughput = total_records / execution_time if execution_time > 0 else 0
            
            metrics = {
                'total_records': total_records,
                'processed_records': total_records,
                'errors': 0,
                'total_time': execution_time,
                'throughput': throughput,
                'parallelism': self.parallelism
            }
            
            self._logger.info(
                f"Completed in {execution_time:.2f}s "
                f"({throughput:.2f} records/sec)"
            )
            
            return metrics
        
        except Exception as e:
            self._logger.error(f"Execution failed: {e}", exc_info=True)
            raise
    
    def run_batch(
        self,
        task_name: str,
        input_files: List[str],
        output_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a task on multiple files using Flink DataStream.
        
        Args:
            task_name: Name of registered task to execute
            input_files: List of input file paths
            output_dir: Directory for output files (optional)
            config: Configuration dictionary for task
        
        Returns:
            Dictionary with aggregated metrics across all files
        
        Example:
            runner = FlinkRunner()
            metrics = runner.run_batch('noop', ['f1.txt', 'f2.txt'], 'output/')
        """
        start_time = time.time()
        
        # Validate task
        if not TaskRegistry.is_registered(task_name):
            raise ValueError(f"Task '{task_name}' not registered")
        
        # Validate input files
        for input_file in input_files:
            if not Path(input_file).exists():
                raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Count total records
        total_records = 0
        for input_file in input_files:
            with open(input_file, 'r') as f:
                total_records += sum(1 for line in f if line.strip())
        
        self._logger.info(
            f"Running task '{task_name}' on {len(input_files)} files "
            f"({total_records} total records)"
        )
        
        # Create DataStream from all files
        ds = self.env.read_text_file(*[str(Path(f)) for f in input_files])
        
        # Apply task MapFunction
        map_fn = FlinkTaskMapFunction(task_name, config)
        result_ds = ds.map(map_fn)
        
        # Write output if specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            result_ds.write_as_text(str(output_path / "output"), mode='OVERWRITE')
            self._logger.info(f"Output will be written to {output_dir}")
        else:
            result_ds.print()
        
        # Execute the pipeline
        try:
            self.env.execute(f"PyRIoTBench-Batch-{task_name}")
            execution_time = time.time() - start_time
            
            # Build metrics
            throughput = total_records / execution_time if execution_time > 0 else 0
            
            metrics = {
                'total_files': len(input_files),
                'total_records': total_records,
                'processed_records': total_records,
                'errors': 0,
                'total_time': execution_time,
                'throughput': throughput,
                'parallelism': self.parallelism
            }
            
            self._logger.info(
                f"Batch completed in {execution_time:.2f}s "
                f"({throughput:.2f} records/sec)"
            )
            
            return metrics
        
        except Exception as e:
            self._logger.error(f"Batch execution failed: {e}", exc_info=True)
            raise
    
    def run_stream(
        self,
        task_name: str,
        data: List[Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a task on in-memory data using Flink DataStream.
        
        Args:
            task_name: Name of registered task to execute
            data: List of input records
            config: Configuration dictionary for task
        
        Returns:
            Dictionary with execution metrics
        
        Example:
            runner = FlinkRunner()
            metrics = runner.run_stream('kalman_filter', ['25.0', '26.1', '24.8'])
        """
        start_time = time.time()
        
        # Validate task
        if not TaskRegistry.is_registered(task_name):
            raise ValueError(f"Task '{task_name}' not registered")
        
        total_records = len(data)
        self._logger.info(
            f"Running task '{task_name}' on {total_records} in-memory records"
        )
        
        # Create DataStream from collection
        ds = self.env.from_collection(data)
        
        # Apply task MapFunction
        map_fn = FlinkTaskMapFunction(task_name, config)
        result_ds = ds.map(map_fn)
        
        # Print results
        result_ds.print()
        
        # Execute the pipeline
        try:
            self.env.execute(f"PyRIoTBench-Stream-{task_name}")
            execution_time = time.time() - start_time
            
            # Build metrics
            throughput = total_records / execution_time if execution_time > 0 else 0
            
            metrics = {
                'total_records': total_records,
                'processed_records': total_records,
                'errors': 0,
                'total_time': execution_time,
                'throughput': throughput,
                'parallelism': self.parallelism
            }
            
            self._logger.info(
                f"Stream completed in {execution_time:.2f}s "
                f"({throughput:.2f} records/sec)"
            )
            
            return metrics
        
        except Exception as e:
            self._logger.error(f"Stream execution failed: {e}", exc_info=True)
            raise
    
    def export_metrics(self, metrics: Dict[str, Any], output_file: str) -> None:
        """
        Export metrics to a JSON file.
        
        Args:
            metrics: Metrics dictionary from run_file/run_batch/run_stream
            output_file: Path to output JSON file
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        self._logger.info(f"Metrics exported to {output_file}")
    
    def __repr__(self) -> str:
        """String representation of the runner."""
        return f"FlinkRunner(parallelism={self.parallelism})"
