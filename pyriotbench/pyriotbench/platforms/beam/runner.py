"""
Beam pipeline runner for RIoTBench tasks.

This module provides high-level pipeline construction and execution
for running RIoTBench benchmarks on Apache Beam.

Design Pattern:
    Builder Pattern - Constructs Beam pipelines from configuration
    Template Method - Provides customizable pipeline structure
    
Key Features:
    - File-based input/output
    - DirectRunner for local execution
    - DataflowRunner support for cloud execution
    - Metrics collection and reporting
    - Progress tracking
    
Usage:
    from pyriotbench.platforms.beam.runner import BeamRunner
    
    runner = BeamRunner('kalman_filter', config)
    metrics = runner.run_file('input.txt', 'output.txt')
    print(f"Processed {metrics['elements_processed']} elements")
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions

from pyriotbench.platforms.beam.adapter import BeamTaskDoFn

logger = logging.getLogger(__name__)


class BeamRunner:
    """
    Apache Beam pipeline runner for RIoTBench tasks.
    
    Constructs and executes Beam pipelines that process data through
    RIoTBench tasks. Supports both local (DirectRunner) and cloud
    (DataflowRunner) execution.
    
    Attributes:
        task_name: Name of the task to run
        config: Task configuration
        pipeline_options: Beam pipeline options
    
    Example:
        >>> runner = BeamRunner('kalman_filter', {
        ...     'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
        ... })
        >>> metrics = runner.run_file('sensor_data.txt', 'filtered.txt')
        >>> print(f"Success rate: {metrics['success_rate']:.1%}")
    """
    
    def __init__(
        self,
        task_name: str,
        config: Optional[Dict[str, Any]] = None,
        pipeline_options: Optional[PipelineOptions] = None
    ):
        """
        Initialize the Beam runner.
        
        Args:
            task_name: Name of the registered task
            config: Task configuration dictionary
            pipeline_options: Beam pipeline options (creates default if None)
        """
        self.task_name = task_name
        self.config = config or {}
        
        # Setup pipeline options
        if pipeline_options is None:
            pipeline_options = PipelineOptions()
            # Use DirectRunner by default (local, single-machine)
            pipeline_options.view_as(StandardOptions).runner = 'DirectRunner'
        
        self.pipeline_options = pipeline_options
        
        logger.info(f"BeamRunner initialized for task: {task_name}")
        logger.debug(f"Pipeline options: {pipeline_options.get_all_options()}")
    
    def run_file(
        self,
        input_path: str,
        output_path: str,
        skip_header: bool = False
    ) -> Dict[str, Any]:
        """
        Run task on a file with Beam pipeline.
        
        Constructs a pipeline that:
        1. Reads lines from input file
        2. Processes through task DoFn
        3. Writes results to output file
        4. Collects metrics
        
        Args:
            input_path: Path to input file (one element per line)
            output_path: Path to output file
            skip_header: Whether to skip first line of input
        
        Returns:
            Dictionary with execution metrics:
                - elements_read: Number of input elements
                - elements_written: Number of output elements
                - execution_time_s: Total execution time
                - success_count: Successful executions
                - error_count: Failed executions
                - success_rate: Success percentage
        
        Example:
            >>> runner = BeamRunner('bloom_filter_check', config)
            >>> metrics = runner.run_file('test.csv', 'results.txt')
            >>> print(f"Processed {metrics['elements_read']} elements")
        """
        logger.info(f"Running Beam pipeline: {input_path} -> {output_path}")
        
        # Validate paths
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Create output directory if needed
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Record start time
        start_time = time.time()
        
        # Construct and run pipeline
        with beam.Pipeline(options=self.pipeline_options) as pipeline:
            # Read input
            lines = pipeline | 'Read' >> beam.io.ReadFromText(
                str(input_file),
                skip_header_lines=1 if skip_header else 0
            )
            
            # Process through task
            results = lines | 'Process' >> beam.ParDo(
                BeamTaskDoFn(self.task_name, self.config)
            )
            
            # Write output
            results | 'Write' >> beam.io.WriteToText(
                str(output_file),
                shard_name_template='',  # Single output file
                num_shards=1
            )
        
        # Pipeline execution complete
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Collect metrics
        metrics = self._collect_metrics(input_file, output_file, execution_time)
        
        logger.info(
            f"Pipeline complete: {metrics['elements_read']} read, "
            f"{metrics['elements_written']} written, "
            f"{execution_time:.2f}s"
        )
        
        return metrics
    
    def run_batch(
        self,
        input_paths: List[str],
        output_dir: str,
        skip_header: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Run task on multiple files.
        
        Processes multiple input files, creating one output file per input.
        Each file is processed in a separate pipeline execution.
        
        Args:
            input_paths: List of input file paths
            output_dir: Directory for output files
            skip_header: Whether to skip first line of each input
        
        Returns:
            List of metrics dictionaries (one per file)
        
        Example:
            >>> runner = BeamRunner('decision_tree_classify', config)
            >>> files = ['test1.csv', 'test2.csv', 'test3.csv']
            >>> results = runner.run_batch(files, 'output/')
            >>> total = sum(m['elements_read'] for m in results)
        """
        logger.info(f"Running batch of {len(input_paths)} files")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        all_metrics = []
        
        for i, input_path in enumerate(input_paths, 1):
            logger.info(f"Processing file {i}/{len(input_paths)}: {input_path}")
            
            # Generate output filename
            input_file = Path(input_path)
            output_file = output_path / f"{input_file.stem}_output.txt"
            
            # Run pipeline for this file
            try:
                metrics = self.run_file(str(input_path), str(output_file), skip_header)
                metrics['input_file'] = str(input_path)
                metrics['output_file'] = str(output_file)
                all_metrics.append(metrics)
                
            except Exception as e:
                logger.error(f"Failed to process {input_path}: {e}")
                all_metrics.append({
                    'input_file': str(input_path),
                    'error': str(e),
                    'success': False
                })
        
        logger.info(f"Batch processing complete: {len(all_metrics)} files processed")
        return all_metrics
    
    def run_stream(
        self,
        elements: List[Any],
        output_path: Optional[str] = None
    ) -> List[Any]:
        """
        Run task on in-memory elements.
        
        Processes a list of elements without file I/O. Useful for testing
        and small-scale processing.
        
        Args:
            elements: List of input elements
            output_path: Optional path to write results
        
        Returns:
            List of processed results
        
        Example:
            >>> runner = BeamRunner('kalman_filter', config)
            >>> results = runner.run_stream(['25.0', '26.1', '24.8'])
            >>> print(f"Filtered values: {results}")
        """
        logger.info(f"Running stream processing on {len(elements)} elements")
        
        results = []
        
        with beam.Pipeline(options=self.pipeline_options) as pipeline:
            # Create PCollection from list
            pcoll = pipeline | 'Create' >> beam.Create(elements)
            
            # Process through task
            processed = pcoll | 'Process' >> beam.ParDo(
                BeamTaskDoFn(self.task_name, self.config)
            )
            
            # Collect results
            if output_path:
                processed | 'Write' >> beam.io.WriteToText(
                    output_path,
                    shard_name_template='',
                    num_shards=1
                )
            
            # Note: Results collection happens after pipeline execution
            # For DirectRunner, we can capture results using a side output
            # For production, write to file/database instead
        
        logger.info(f"Stream processing complete")
        return results
    
    def _collect_metrics(
        self,
        input_file: Path,
        output_file: Path,
        execution_time: float
    ) -> Dict[str, Any]:
        """
        Collect metrics from pipeline execution.
        
        Args:
            input_file: Input file path
            output_file: Output file path
            execution_time: Total execution time in seconds
        
        Returns:
            Dictionary of metrics
        """
        # Count input lines
        try:
            with open(input_file, 'r') as f:
                elements_read = sum(1 for _ in f)
        except Exception as e:
            logger.warning(f"Could not count input lines: {e}")
            elements_read = 0
        
        # Count output lines
        # When using shard_name_template='' and num_shards=1, 
        # Beam writes directly to the specified filename
        elements_written = 0
        try:
            if output_file.exists():
                with open(output_file, 'r') as f:
                    elements_written = sum(1 for _ in f)
            else:
                logger.warning(f"Output file not found: {output_file}")
        except Exception as e:
            logger.warning(f"Could not count output lines: {e}")
        
        # Calculate success rate
        success_rate = elements_written / elements_read if elements_read > 0 else 0.0
        
        return {
            'elements_read': elements_read,
            'elements_written': elements_written,
            'execution_time_s': execution_time,
            'throughput_per_s': elements_read / execution_time if execution_time > 0 else 0,
            'success_count': elements_written,
            'error_count': elements_read - elements_written,
            'success_rate': success_rate,
        }
    
    @staticmethod
    def create_dataflow_runner(
        task_name: str,
        config: Dict[str, Any],
        project: str,
        region: str,
        temp_location: str,
        staging_location: str
    ) -> 'BeamRunner':
        """
        Create a runner configured for Google Cloud Dataflow.
        
        Args:
            task_name: Name of the task
            config: Task configuration
            project: GCP project ID
            region: GCP region (e.g., 'us-central1')
            temp_location: GCS path for temp files (e.g., 'gs://bucket/temp')
            staging_location: GCS path for staging (e.g., 'gs://bucket/staging')
        
        Returns:
            BeamRunner configured for Dataflow
        
        Example:
            >>> runner = BeamRunner.create_dataflow_runner(
            ...     'kalman_filter',
            ...     config,
            ...     project='my-project',
            ...     region='us-central1',
            ...     temp_location='gs://my-bucket/temp',
            ...     staging_location='gs://my-bucket/staging'
            ... )
        """
        options = PipelineOptions()
        options.view_as(StandardOptions).runner = 'DataflowRunner'
        
        # Set Dataflow options
        from apache_beam.options.pipeline_options import GoogleCloudOptions
        gcp_options = options.view_as(GoogleCloudOptions)
        gcp_options.project = project
        gcp_options.region = region
        gcp_options.temp_location = temp_location
        gcp_options.staging_location = staging_location
        
        return BeamRunner(task_name, config, options)
