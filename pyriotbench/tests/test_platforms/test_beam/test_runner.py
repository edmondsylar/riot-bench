"""
Tests for Beam pipeline runner.

Tests the BeamRunner class that constructs and executes Beam pipelines
for RIoTBench tasks.
"""

import pytest
from pathlib import Path
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions

from pyriotbench.platforms.beam.runner import BeamRunner


class TestBeamRunnerCreation:
    """Test BeamRunner initialization."""
    
    def test_create_with_defaults(self):
        """Test creating runner with default options."""
        runner = BeamRunner('noop')
        
        assert runner.task_name == 'noop'
        assert runner.config == {}
        assert runner.pipeline_options is not None
        
        # Verify DirectRunner is default
        options = runner.pipeline_options.view_as(StandardOptions)
        assert options.runner == 'DirectRunner'
    
    def test_create_with_config(self):
        """Test creating runner with configuration."""
        config = {
            'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
            'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
        }
        runner = BeamRunner('kalman_filter', config)
        
        assert runner.task_name == 'kalman_filter'
        assert runner.config == config
    
    def test_create_with_pipeline_options(self):
        """Test creating runner with custom pipeline options."""
        options = PipelineOptions()
        options.view_as(StandardOptions).runner = 'DirectRunner'
        
        runner = BeamRunner('noop', pipeline_options=options)
        
        assert runner.pipeline_options is options


class TestBeamRunnerFileProcessing:
    """Test file-based pipeline execution."""
    
    def test_run_file_with_noop(self, tmp_path):
        """Test basic file processing with noop task."""
        # Create input file
        input_file = tmp_path / "input.txt"
        input_file.write_text("line1\nline2\nline3\n")
        
        output_file = tmp_path / "output.txt"
        
        # Run pipeline
        runner = BeamRunner('noop')
        metrics = runner.run_file(str(input_file), str(output_file))
        
        # Verify metrics
        assert metrics['elements_read'] == 3
        assert metrics['elements_written'] == 3
        assert metrics['success_rate'] == 1.0
        assert metrics['error_count'] == 0
        assert metrics['execution_time_s'] > 0
        assert metrics['throughput_per_s'] > 0
        
        # Verify output file exists
        assert output_file.exists()
        
        # Verify output content
        output_lines = output_file.read_text().splitlines()
        assert len(output_lines) == 3
        assert output_lines == ['line1', 'line2', 'line3']
    
    def test_run_file_with_kalman_filter(self, tmp_path):
        """Test file processing with stateful task."""
        # Create input file with noisy sensor data
        input_file = tmp_path / "sensor.txt"
        input_file.write_text("25.0\n26.5\n24.8\n25.3\n26.1\n")
        
        output_file = tmp_path / "filtered.txt"
        
        # Run pipeline with Kalman filter
        config = {
            'STATISTICS.KALMAN_FILTER.PROCESS_NOISE': 0.01,
            'STATISTICS.KALMAN_FILTER.MEASUREMENT_NOISE': 0.1,
        }
        runner = BeamRunner('kalman_filter', config)
        metrics = runner.run_file(str(input_file), str(output_file))
        
        # Verify metrics
        assert metrics['elements_read'] == 5
        assert metrics['elements_written'] == 5
        assert metrics['success_rate'] == 1.0
        
        # Verify output exists
        assert output_file.exists()
        
        # Verify filtering worked
        output_lines = output_file.read_text().splitlines()
        assert len(output_lines) == 5
        # All values should be numeric
        for line in output_lines:
            assert float(line) > 0
    
    def test_run_file_with_windowed_task(self, tmp_path):
        """Test file processing with windowed aggregation."""
        # Create input file with sensor readings
        input_file = tmp_path / "readings.txt"
        readings = [f"sensor1,{i*10.0}" for i in range(1, 11)]
        input_file.write_text("\n".join(readings) + "\n")
        
        output_file = tmp_path / "averages.txt"
        
        # Run pipeline with block window average
        config = {
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 5,
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.FIELD': 1,  # Value field
            'AGGREGATE.BLOCK_WINDOW_AVERAGE.ID_FIELD': 0,  # Sensor ID field
        }
        runner = BeamRunner('block_window_average', config)
        metrics = runner.run_file(str(input_file), str(output_file))
        
        # Verify metrics
        assert metrics['elements_read'] == 10
        # Windowed task emits fewer results (one per window)
        assert metrics['elements_written'] == 2  # Two windows of 5 each
        assert metrics['success_rate'] == 0.2  # 2/10
        
        # Verify output
        assert output_file.exists()
        output_lines = output_file.read_text().splitlines()
        assert len(output_lines) == 2
    
    def test_run_file_with_skip_header(self, tmp_path):
        """Test file processing with header skipping."""
        # Create CSV file with header
        input_file = tmp_path / "data.csv"
        input_file.write_text("header,row\nvalue1\nvalue2\nvalue3\n")
        
        output_file = tmp_path / "output.txt"
        
        # Run pipeline skipping header
        runner = BeamRunner('noop')
        metrics = runner.run_file(str(input_file), str(output_file), skip_header=True)
        
        # Verify header was skipped (4 total lines, 1 skipped = 3 processed)
        assert metrics['elements_read'] == 4  # Still counts all lines in file
        assert metrics['elements_written'] == 3  # But only 3 processed
        
        # Verify output doesn't contain header
        output_lines = output_file.read_text().splitlines()
        assert len(output_lines) == 3
        assert 'header' not in output_lines[0]
    
    def test_run_file_creates_output_directory(self, tmp_path):
        """Test that runner creates output directory if needed."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("test\n")
        
        # Output in nested directory that doesn't exist
        output_file = tmp_path / "nested" / "subdir" / "output.txt"
        
        runner = BeamRunner('noop')
        metrics = runner.run_file(str(input_file), str(output_file))
        
        # Verify directory was created
        assert output_file.parent.exists()
        assert output_file.exists()
    
    def test_run_file_input_not_found(self, tmp_path):
        """Test error handling for missing input file."""
        input_file = tmp_path / "nonexistent.txt"
        output_file = tmp_path / "output.txt"
        
        runner = BeamRunner('noop')
        
        with pytest.raises(FileNotFoundError):
            runner.run_file(str(input_file), str(output_file))


class TestBeamRunnerBatchProcessing:
    """Test batch file processing."""
    
    def test_run_batch_multiple_files(self, tmp_path):
        """Test processing multiple files in batch."""
        # Create multiple input files
        input_files = []
        for i in range(3):
            file_path = tmp_path / f"input{i}.txt"
            file_path.write_text(f"data{i}\n")
            input_files.append(str(file_path))
        
        output_dir = tmp_path / "output"
        
        # Run batch processing
        runner = BeamRunner('noop')
        results = runner.run_batch(input_files, str(output_dir))
        
        # Verify results
        assert len(results) == 3
        
        for i, result in enumerate(results):
            assert result['input_file'] == input_files[i]
            assert 'output_file' in result
            assert result['elements_read'] == 1
            assert result['elements_written'] == 1
            assert result['success_rate'] == 1.0
            
            # Verify output file exists
            output_path = Path(result['output_file'])
            assert output_path.exists()
    
    def test_run_batch_creates_output_directory(self, tmp_path):
        """Test that batch processing creates output directory."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("test\n")
        
        output_dir = tmp_path / "nested" / "output"
        
        runner = BeamRunner('noop')
        results = runner.run_batch([str(input_file)], str(output_dir))
        
        # Verify directory was created
        assert output_dir.exists()
        assert len(results) == 1
    
    def test_run_batch_with_errors(self, tmp_path):
        """Test batch processing with some failing files."""
        # Create valid and invalid input files
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("test\n")
        
        invalid_file = tmp_path / "nonexistent.txt"
        
        output_dir = tmp_path / "output"
        
        # Run batch with mixed results
        runner = BeamRunner('noop')
        results = runner.run_batch(
            [str(valid_file), str(invalid_file)],
            str(output_dir)
        )
        
        # Verify results
        assert len(results) == 2
        
        # First file should succeed
        assert 'error' not in results[0]
        assert results[0]['elements_read'] == 1
        
        # Second file should fail
        assert 'error' in results[1]
        assert results[1]['success'] is False


class TestBeamRunnerStreamProcessing:
    """Test in-memory stream processing."""
    
    def test_run_stream_basic(self):
        """Test basic stream processing."""
        elements = ["test1", "test2", "test3"]
        
        runner = BeamRunner('noop')
        results = runner.run_stream(elements)
        
        # Note: DirectRunner doesn't easily return results in-memory
        # This is primarily for testing the method works without error
        assert isinstance(results, list)
    
    def test_run_stream_with_output_file(self, tmp_path):
        """Test stream processing with file output."""
        elements = ["line1", "line2", "line3"]
        output_file = tmp_path / "stream_output.txt"
        
        runner = BeamRunner('noop')
        results = runner.run_stream(elements, str(output_file))
        
        # Verify output file was created (without suffix when using shard_name_template='')
        assert output_file.exists()
        
        # Verify content
        output_lines = output_file.read_text().splitlines()
        assert len(output_lines) == 3
        assert output_lines == elements


class TestBeamRunnerDataflowFactory:
    """Test Dataflow runner factory method."""
    
    def test_create_dataflow_runner(self):
        """Test creating a Dataflow-configured runner."""
        runner = BeamRunner.create_dataflow_runner(
            task_name='kalman_filter',
            config={},
            project='test-project',
            region='us-central1',
            temp_location='gs://test-bucket/temp',
            staging_location='gs://test-bucket/staging'
        )
        
        # Verify runner was created
        assert runner.task_name == 'kalman_filter'
        assert runner.pipeline_options is not None
        
        # Verify Dataflow options
        options = runner.pipeline_options.view_as(StandardOptions)
        assert options.runner == 'DataflowRunner'
        
        from apache_beam.options.pipeline_options import GoogleCloudOptions
        gcp_options = runner.pipeline_options.view_as(GoogleCloudOptions)
        assert gcp_options.project == 'test-project'
        assert gcp_options.region == 'us-central1'
        assert gcp_options.temp_location == 'gs://test-bucket/temp'
        assert gcp_options.staging_location == 'gs://test-bucket/staging'


class TestBeamRunnerMetrics:
    """Test metrics collection."""
    
    def test_metrics_with_perfect_success(self, tmp_path):
        """Test metrics when all elements succeed."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("a\nb\nc\n")
        
        output_file = tmp_path / "output.txt"
        
        runner = BeamRunner('noop')
        metrics = runner.run_file(str(input_file), str(output_file))
        
        assert metrics['elements_read'] == 3
        assert metrics['elements_written'] == 3
        assert metrics['success_count'] == 3
        assert metrics['error_count'] == 0
        assert metrics['success_rate'] == 1.0
    
    def test_metrics_with_partial_success(self, tmp_path):
        """Test metrics when some elements filtered out."""
        # Windowed task will filter out partial windows
        input_file = tmp_path / "input.txt"
        readings = [f"sensor1,{i*10.0}" for i in range(1, 8)]  # 7 readings
        input_file.write_text("\n".join(readings) + "\n")
        
        output_file = tmp_path / "output.txt"
        
        # Window size 5 means: 1 complete window + 2 filtered
        config = {'AGGREGATE.BLOCK_WINDOW_AVERAGE.WINDOW_SIZE': 5}
        runner = BeamRunner('block_window_average', config)
        metrics = runner.run_file(str(input_file), str(output_file))
        
        assert metrics['elements_read'] == 7
        assert metrics['elements_written'] == 1  # Only one full window
        assert metrics['error_count'] == 6  # 6 filtered
        assert 0 < metrics['success_rate'] < 1.0  # Partial success
    
    def test_metrics_execution_time(self, tmp_path):
        """Test that execution time is measured."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("test\n")
        
        output_file = tmp_path / "output.txt"
        
        runner = BeamRunner('noop')
        metrics = runner.run_file(str(input_file), str(output_file))
        
        assert metrics['execution_time_s'] > 0
        assert metrics['throughput_per_s'] > 0
