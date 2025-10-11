"""
Standalone runner for PyRIoTBench tasks.

This module provides a simple, single-process execution engine that runs
tasks on local files without any distributed framework. It's the fastest
way to test and develop tasks.

Key Features:
- Zero dependencies beyond core Python
- Simple file-based input/output
- Automatic metrics collection
- Progress reporting
- Error handling with graceful degradation

Example:
    >>> from pyriotbench.platforms.standalone import StandaloneRunner
    >>> runner = StandaloneRunner("noop")
    >>> runner.run("input.txt", "output.txt")
    Processed 1000 records in 0.52s
    Average time: 0.52ms per record
"""

from __future__ import annotations

import time
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List, TextIO
from dataclasses import dataclass

from pyriotbench.core import (
    create_task,
    BaseTask,
    TaskMetrics,
    MetricsAggregator,
    BenchmarkConfig,
)


logger = logging.getLogger(__name__)


@dataclass
class RunnerStats:
    """Statistics from a standalone run.
    
    Attributes:
        total_records: Total number of records processed
        successful_records: Number of successfully processed records
        failed_records: Number of failed records
        total_time_s: Total execution time in seconds
        avg_time_ms: Average time per record in milliseconds
        throughput: Records per second
    """
    total_records: int
    successful_records: int
    failed_records: int
    total_time_s: float
    avg_time_ms: float
    throughput: float
    
    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"Processed {self.total_records} records in {self.total_time_s:.2f}s\n"
            f"Success: {self.successful_records}, Failed: {self.failed_records}\n"
            f"Average: {self.avg_time_ms:.3f}ms per record\n"
            f"Throughput: {self.throughput:.1f} records/s"
        )


class StandaloneRunner:
    """
    Simple single-process runner for PyRIoTBench tasks.
    
    This runner executes tasks on local files without any distributed
    framework. It's designed for development, testing, and small datasets.
    
    The runner handles:
    - File reading (line-by-line or batch)
    - Task execution with automatic timing
    - Metrics collection and aggregation
    - Output writing
    - Progress reporting
    - Error handling
    
    Attributes:
        task_name: Name of the task to execute
        config: Optional configuration dictionary
        progress_interval: Report progress every N records (0 = disabled)
    
    Example:
        >>> # Simple usage
        >>> runner = StandaloneRunner("noop")
        >>> runner.run("input.txt", "output.txt")
        
        >>> # With configuration
        >>> runner = StandaloneRunner("senml_parse", config={"validate": True})
        >>> stats = runner.run("data.json", "parsed.txt")
        >>> print(f"Throughput: {stats.throughput:.1f} records/s")
        
        >>> # With metrics export
        >>> runner = StandaloneRunner("noop")
        >>> stats = runner.run("input.txt", "output.txt", metrics_file="metrics.json")
    """
    
    def __init__(
        self,
        task_name: str,
        config: Optional[Dict[str, Any]] = None,
        progress_interval: int = 1000,
    ) -> None:
        """
        Initialize the standalone runner.
        
        Args:
            task_name: Name of registered task to execute
            config: Optional configuration dictionary for task
            progress_interval: Report progress every N records (0 = disabled)
        
        Raises:
            ValueError: If task_name is not registered
        """
        self.task_name = task_name
        self.config = config or {}
        self.progress_interval = progress_interval
        self._logger = logging.getLogger(f"{__name__}.{task_name}")
        
        # Create task instance to validate it exists
        self._task: Optional[BaseTask] = None
        self._validate_task()
    
    def _validate_task(self) -> None:
        """Validate that task exists and can be created."""
        try:
            task = create_task(self.task_name)
            self._logger.info(f"Validated task: {self.task_name}")
            # Don't keep the task, we'll create fresh one for run()
        except Exception as e:
            raise ValueError(
                f"Cannot create task '{self.task_name}': {e}"
            ) from e
    
    def run(
        self,
        input_file: str | Path,
        output_file: Optional[str | Path] = None,
        metrics_file: Optional[str | Path] = None,
    ) -> RunnerStats:
        """
        Run the task on input file and write results.
        
        This is the main execution method. It:
        1. Creates and sets up the task
        2. Reads input file line-by-line
        3. Executes task on each line
        4. Collects metrics
        5. Writes output (if specified)
        6. Saves metrics (if specified)
        7. Returns statistics
        
        Args:
            input_file: Path to input data file
            output_file: Optional path to output file (None = no output)
            metrics_file: Optional path to save metrics JSON
        
        Returns:
            RunnerStats with execution statistics
        
        Raises:
            FileNotFoundError: If input_file doesn't exist
            Exception: If task execution fails critically
        
        Example:
            >>> runner = StandaloneRunner("noop")
            >>> stats = runner.run("input.txt", "output.txt", "metrics.json")
            >>> print(f"Processed {stats.total_records} records")
        """
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        self._logger.info(f"Starting standalone run: {self.task_name}")
        self._logger.info(f"Input: {input_path}")
        if output_file:
            self._logger.info(f"Output: {output_file}")
        
        # Create fresh task instance for this run
        task = create_task(self.task_name)
        task.setup()
        
        # Metrics aggregator
        aggregator = MetricsAggregator(self.task_name)
        
        # Output file (if specified)
        output_handle: Optional[TextIO] = None
        if output_file:
            output_handle = open(output_file, 'w')
        
        try:
            # Process file
            start_time = time.perf_counter()
            
            total = 0
            successful = 0
            failed = 0
            
            with open(input_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Strip whitespace
                    line = line.rstrip('\n\r')
                    
                    if not line:  # Skip empty lines
                        continue
                    
                    total += 1
                    
                    # Execute task
                    output = task.execute(line)
                    result = task.get_last_result()
                    
                    # Collect metrics (convert ms to μs)
                    metric = TaskMetrics(
                        task_name=self.task_name,
                        execution_time_us=result.execution_time_ms * 1000,
                        status="success" if result.success else "error",
                        metadata=result.metadata
                    )
                    aggregator.add(metric)
                    
                    # Track success/failure
                    if result.success:
                        successful += 1
                    else:
                        failed += 1
                        self._logger.warning(
                            f"Line {line_num} failed: {result.error_message}"
                        )
                    
                    # Write output
                    if output_handle:
                        output_handle.write(str(output) + '\n')
                    
                    # Progress reporting
                    if self.progress_interval > 0 and total % self.progress_interval == 0:
                        elapsed = time.perf_counter() - start_time
                        throughput = total / elapsed if elapsed > 0 else 0
                        self._logger.info(
                            f"Progress: {total} records, "
                            f"{throughput:.1f} records/s"
                        )
            
            # Finalize
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            task.tear_down()
            
            # Calculate statistics
            avg_time_ms = (
                aggregator.mean_time_us / 1000 if aggregator.mean_time_us else 0
            )
            throughput = total / total_time if total_time > 0 else 0
            
            stats = RunnerStats(
                total_records=total,
                successful_records=successful,
                failed_records=failed,
                total_time_s=total_time,
                avg_time_ms=avg_time_ms,
                throughput=throughput
            )
            
            # Log summary
            self._logger.info("Run complete!")
            self._logger.info(str(stats))
            
            # Save metrics if requested
            if metrics_file:
                metrics_path = Path(metrics_file)
                aggregator.to_json(metrics_path)
                self._logger.info(f"Metrics saved to: {metrics_path}")
            
            return stats
            
        finally:
            # Clean up
            if output_handle:
                output_handle.close()
    
    def run_batch(
        self,
        input_files: List[str | Path],
        output_dir: str | Path,
        metrics_dir: Optional[str | Path] = None,
    ) -> List[RunnerStats]:
        """
        Run task on multiple input files.
        
        Processes each file independently and collects statistics for each.
        Useful for batch processing or benchmarking multiple datasets.
        
        Args:
            input_files: List of input file paths
            output_dir: Directory to write output files
            metrics_dir: Optional directory to save metrics files
        
        Returns:
            List of RunnerStats, one per input file
        
        Example:
            >>> runner = StandaloneRunner("noop")
            >>> stats_list = runner.run_batch(
            ...     ["data1.txt", "data2.txt"],
            ...     output_dir="results",
            ...     metrics_dir="metrics"
            ... )
            >>> total_records = sum(s.total_records for s in stats_list)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if metrics_dir:
            metrics_path = Path(metrics_dir)
            metrics_path.mkdir(parents=True, exist_ok=True)
        
        all_stats = []
        
        for input_file in input_files:
            input_path = Path(input_file)
            
            # Generate output paths
            output_file = output_path / f"{input_path.stem}_output{input_path.suffix}"
            
            metrics_file = None
            if metrics_dir:
                metrics_file = Path(metrics_dir) / f"{input_path.stem}_metrics.json"
            
            self._logger.info(f"\n{'='*60}")
            self._logger.info(f"Processing: {input_path.name}")
            self._logger.info(f"{'='*60}")
            
            # Run on this file
            stats = self.run(input_file, output_file, metrics_file)
            all_stats.append(stats)
        
        # Summary
        total_records = sum(s.total_records for s in all_stats)
        total_time = sum(s.total_time_s for s in all_stats)
        
        self._logger.info(f"\n{'='*60}")
        self._logger.info("BATCH COMPLETE")
        self._logger.info(f"{'='*60}")
        self._logger.info(f"Files processed: {len(input_files)}")
        self._logger.info(f"Total records: {total_records}")
        self._logger.info(f"Total time: {total_time:.2f}s")
        
        return all_stats
    
    @classmethod
    def from_config(cls, config: BenchmarkConfig) -> StandaloneRunner:
        """
        Create runner from BenchmarkConfig.
        
        Args:
            config: BenchmarkConfig instance
        
        Returns:
            StandaloneRunner configured from config
        
        Example:
            >>> from pyriotbench.core import BenchmarkConfig
            >>> config = BenchmarkConfig.from_yaml("config.yaml")
            >>> runner = StandaloneRunner.from_config(config)
            >>> runner.run(config.input_file, config.output_file)
        """
        # Get first task from config
        if not config.tasks:
            raise ValueError("Config must have at least one task")
        
        task_config = config.tasks[0]
        
        return cls(
            task_name=task_config.task_name,
            config=task_config.config_params,
            progress_interval=1000  # Default
        )
