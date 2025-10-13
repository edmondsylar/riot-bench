"""
Ray Runner - Execute benchmark pipelines using Ray distributed computing.

This runner orchestrates task execution across Ray actors, enabling parallel
and distributed processing of IoT streaming workloads.
"""

import logging
import time
from pathlib import Path
from typing import Any, Optional, Dict, List
import json

import ray

from pyriotbench.platforms.ray.adapter import RayTaskActor, create_ray_actors
from pyriotbench.core.metrics import MetricsAggregator


class RayRunner:
    """
    Execute benchmark tasks using Ray's distributed computing framework.
    
    This runner:
    - Initializes Ray cluster (local or distributed)
    - Creates Ray actors for task execution
    - Distributes data across actors for parallel processing
    - Collects and aggregates metrics from all actors
    - Handles file I/O and batching
    
    Usage:
        runner = RayRunner()
        metrics = runner.run_file('noop', 'input.txt', 'output.txt')
    
    Attributes:
        num_actors: Number of Ray actors to create (default: 4)
        _logger: Logger for this runner
        _ray_initialized: Whether Ray was initialized by this runner
    """
    
    def __init__(self, num_actors: int = 4):
        """
        Initialize the Ray runner.
        
        Args:
            num_actors: Number of parallel actors to create (default: 4)
        """
        self.num_actors = num_actors
        self._logger = logging.getLogger("RayRunner")
        self._ray_initialized = False
        
        # Initialize Ray if not already running
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True, logging_level=logging.WARNING)
            self._ray_initialized = True
            self._logger.info(f"Ray initialized with {num_actors} actors")
    
    def run_file(
        self,
        task_name: str,
        input_file: str,
        output_file: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a task on data from a file using Ray actors.
        
        Args:
            task_name: Name of registered task to execute
            input_file: Path to input file (one record per line)
            output_file: Path to output file (optional)
            config: Configuration dictionary for task
        
        Returns:
            Dictionary with metrics:
                - total_records: Number of input records
                - processed_records: Number successfully processed
                - errors: Number of errors
                - total_time: Total execution time
                - throughput: Records per second
                - actor_metrics: Per-actor metrics
        
        Example:
            runner = RayRunner(num_actors=4)
            metrics = runner.run_file('senml_parse', 'data.txt', 'output.txt')
        """
        start_time = time.time()
        
        # Read input file
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        with open(input_path, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        self._logger.info(f"Loaded {len(lines)} records from {input_file}")
        
        # Create Ray actors
        actors = create_ray_actors(task_name, self.num_actors, config)
        self._logger.info(f"Created {len(actors)} Ray actors for '{task_name}'")
        
        # Distribute work across actors (round-robin)
        actor_futures = []
        for i, line in enumerate(lines):
            actor_idx = i % self.num_actors
            future = actors[actor_idx].process.remote(line)
            actor_futures.append(future)
        
        self._logger.info(f"Submitted {len(actor_futures)} tasks to actors")
        
        # Wait for all results
        results = ray.get(actor_futures)
        
        # Filter out None results (from windowed tasks)
        valid_results = [r for r in results if r is not None]
        
        self._logger.info(f"Processed {len(results)} records, {len(valid_results)} non-None")
        
        # Write output if requested
        if output_file and valid_results:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                for result in valid_results:
                    f.write(str(result) + '\n')
            
            self._logger.info(f"Wrote {len(valid_results)} results to {output_file}")
        
        # Collect metrics from all actors
        actor_metrics_futures = [actor.get_metrics.remote() for actor in actors]
        actor_metrics = ray.get(actor_metrics_futures)
        
        # Tear down actors
        teardown_futures = [actor.tear_down.remote() for actor in actors]
        ray.get(teardown_futures)
        
        # Calculate aggregate metrics
        total_time = time.time() - start_time
        total_processed = sum(m['total_processed'] for m in actor_metrics)
        total_errors = sum(m['errors'] for m in actor_metrics)
        total_none = sum(m['none_filtered'] for m in actor_metrics)
        
        metrics = {
            'total_records': len(lines),
            'processed_records': total_processed,
            'valid_results': len(valid_results),
            'none_filtered': total_none,
            'errors': total_errors,
            'total_time': total_time,
            'throughput': len(lines) / total_time if total_time > 0 else 0.0,
            'num_actors': self.num_actors,
            'actor_metrics': actor_metrics,
        }
        
        self._logger.info(
            f"Completed: {total_processed} processed, "
            f"{len(valid_results)} valid, {total_errors} errors, "
            f"{total_time:.2f}s, {metrics['throughput']:.1f} rec/s"
        )
        
        return metrics
    
    def run_batch(
        self,
        task_name: str,
        input_files: List[str],
        output_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a task on multiple files in batch mode.
        
        Args:
            task_name: Name of registered task
            input_files: List of input file paths
            output_dir: Directory for output files (optional)
            config: Configuration dictionary for task
        
        Returns:
            Dictionary with aggregate metrics across all files
        
        Example:
            runner = RayRunner(num_actors=8)
            metrics = runner.run_batch('noop', ['f1.txt', 'f2.txt'], 'out/')
        """
        self._logger.info(f"Starting batch processing of {len(input_files)} files")
        
        all_metrics = []
        batch_start = time.time()
        
        for i, input_file in enumerate(input_files, 1):
            self._logger.info(f"Processing file {i}/{len(input_files)}: {input_file}")
            
            # Determine output file
            output_file = None
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                input_name = Path(input_file).stem
                output_file = str(output_path / f"{input_name}_output.txt")
            
            # Process file
            try:
                metrics = self.run_file(task_name, input_file, output_file, config)
                all_metrics.append(metrics)
            except Exception as e:
                self._logger.error(f"Failed to process {input_file}: {e}")
                all_metrics.append({'error': str(e), 'file': input_file})
        
        # Aggregate metrics
        batch_time = time.time() - batch_start
        total_records = sum(m.get('total_records', 0) for m in all_metrics)
        total_processed = sum(m.get('processed_records', 0) for m in all_metrics)
        total_errors = sum(m.get('errors', 0) for m in all_metrics)
        
        batch_metrics = {
            'files_processed': len(input_files),
            'total_records': total_records,
            'processed_records': total_processed,
            'errors': total_errors,
            'batch_time': batch_time,
            'throughput': total_records / batch_time if batch_time > 0 else 0.0,
            'file_metrics': all_metrics,
        }
        
        self._logger.info(
            f"Batch complete: {len(input_files)} files, "
            f"{total_records} records, {batch_time:.2f}s"
        )
        
        return batch_metrics
    
    def run_stream(
        self,
        task_name: str,
        data_items: List[Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a task on in-memory data stream using Ray actors.
        
        Args:
            task_name: Name of registered task
            data_items: List of data items to process
            config: Configuration dictionary for task
        
        Returns:
            Dictionary with results and metrics:
                - results: List of task outputs
                - metrics: Execution metrics
        
        Example:
            runner = RayRunner(num_actors=4)
            result = runner.run_stream('noop', ['a', 'b', 'c'])
        """
        start_time = time.time()
        
        # Create Ray actors
        actors = create_ray_actors(task_name, self.num_actors, config)
        
        # Distribute work across actors
        actor_futures = []
        for i, item in enumerate(data_items):
            actor_idx = i % self.num_actors
            future = actors[actor_idx].process.remote(item)
            actor_futures.append(future)
        
        # Wait for results
        results = ray.get(actor_futures)
        
        # Collect metrics
        actor_metrics_futures = [actor.get_metrics.remote() for actor in actors]
        actor_metrics = ray.get(actor_metrics_futures)
        
        # Tear down actors
        teardown_futures = [actor.tear_down.remote() for actor in actors]
        ray.get(teardown_futures)
        
        # Calculate metrics
        total_time = time.time() - start_time
        valid_results = [r for r in results if r is not None]
        
        metrics = {
            'total_items': len(data_items),
            'valid_results': len(valid_results),
            'total_time': total_time,
            'throughput': len(data_items) / total_time if total_time > 0 else 0.0,
            'num_actors': self.num_actors,
            'actor_metrics': actor_metrics,
        }
        
        return {
            'results': results,
            'metrics': metrics,
        }
    
    def export_metrics(
        self,
        metrics: Dict[str, Any],
        output_file: str,
        format: str = 'json'
    ) -> None:
        """
        Export metrics to file.
        
        Args:
            metrics: Metrics dictionary to export
            output_file: Path to output file
            format: Export format ('json' or 'csv')
        
        Raises:
            ValueError: If format is not supported
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(metrics, f, indent=2)
            self._logger.info(f"Exported metrics to {output_file} (JSON)")
        
        elif format == 'csv':
            # Flatten metrics for CSV
            import csv
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['metric', 'value'])
                
                for key, value in metrics.items():
                    if not isinstance(value, (list, dict)):
                        writer.writerow([key, value])
            
            self._logger.info(f"Exported metrics to {output_file} (CSV)")
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def shutdown(self) -> None:
        """
        Shutdown Ray if it was initialized by this runner.
        """
        if self._ray_initialized and ray.is_initialized():
            ray.shutdown()
            self._logger.info("Ray shutdown complete")
            self._ray_initialized = False
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures Ray shutdown."""
        self.shutdown()
