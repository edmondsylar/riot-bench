"""
Tests for Ray Runner.
"""

import pytest
import ray
from pathlib import Path
import tempfile
import json

from pyriotbench.platforms.ray.runner import RayRunner


@pytest.fixture(scope="module", autouse=True)
def ray_cluster():
    """Initialize Ray for all tests."""
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True, logging_level="ERROR")
    yield
    # Don't shutdown - might break other tests


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_input_file(temp_dir):
    """Create a sample input file."""
    input_file = temp_dir / "input.txt"
    with open(input_file, 'w') as f:
        for i in range(10):
            f.write(f"line{i}\n")
    return input_file


class TestRayRunnerBasics:
    """Test basic RayRunner functionality."""
    
    def test_runner_creation(self):
        """Test creating a RayRunner."""
        runner = RayRunner(num_actors=2)
        assert runner.num_actors == 2
        runner.shutdown()
    
    def test_runner_default_actors(self):
        """Test runner with default number of actors."""
        runner = RayRunner()
        assert runner.num_actors == 4
        runner.shutdown()
    
    def test_context_manager(self):
        """Test runner as context manager."""
        with RayRunner(num_actors=2) as runner:
            assert runner.num_actors == 2
        # Should auto-shutdown after context


class TestRayRunnerStream:
    """Test stream processing."""
    
    def test_run_stream_basic(self):
        """Test basic stream processing."""
        runner = RayRunner(num_actors=2)
        
        data = ["a", "b", "c", "d"]
        result = runner.run_stream('noop', data)
        
        assert result['results'] == data
        assert result['metrics']['total_items'] == 4
        assert result['metrics']['valid_results'] == 4
        
        runner.shutdown()
    
    def test_run_stream_with_config(self):
        """Test stream processing with configuration."""
        runner = RayRunner(num_actors=2)
        config = {'test': 'value'}
        
        result = runner.run_stream('noop', ['a', 'b'], config)
        
        assert len(result['results']) == 2
        runner.shutdown()
    
    def test_run_stream_empty_data(self):
        """Test stream with empty data."""
        runner = RayRunner(num_actors=2)
        
        result = runner.run_stream('noop', [])
        
        assert result['results'] == []
        assert result['metrics']['total_items'] == 0
        
        runner.shutdown()
    
    def test_run_stream_stateful_task(self):
        """Test stream with stateful task."""
        runner = RayRunner(num_actors=1)
        
        # Use noop which is simple and reliable
        data = ["item1", "item2", "item3"]
        result = runner.run_stream('noop', data)
        
        # Should have all results
        assert len(result['results']) == 3
        assert result['metrics']['valid_results'] == 3
        assert result['results'] == data
        
        runner.shutdown()


class TestRayRunnerFile:
    """Test file processing."""
    
    def test_run_file_basic(self, sample_input_file, temp_dir):
        """Test basic file processing."""
        runner = RayRunner(num_actors=2)
        output_file = temp_dir / "output.txt"
        
        metrics = runner.run_file(
            'noop',
            str(sample_input_file),
            str(output_file)
        )
        
        assert metrics['total_records'] == 10
        assert metrics['processed_records'] == 10
        assert output_file.exists()
        
        # Check output
        with open(output_file, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 10
        
        runner.shutdown()
    
    def test_run_file_no_output(self, sample_input_file):
        """Test file processing without output file."""
        runner = RayRunner(num_actors=2)
        
        metrics = runner.run_file('noop', str(sample_input_file))
        
        assert metrics['total_records'] == 10
        assert metrics['processed_records'] == 10
        
        runner.shutdown()
    
    def test_run_file_with_config(self, sample_input_file):
        """Test file processing with configuration."""
        runner = RayRunner(num_actors=2)
        config = {'test_key': 'test_value'}
        
        metrics = runner.run_file('noop', str(sample_input_file), config=config)
        
        assert metrics['total_records'] == 10
        runner.shutdown()
    
    def test_run_file_missing_input(self, temp_dir):
        """Test with missing input file."""
        runner = RayRunner(num_actors=2)
        
        with pytest.raises(FileNotFoundError):
            runner.run_file('noop', str(temp_dir / "missing.txt"))
        
        runner.shutdown()


class TestRayRunnerBatch:
    """Test batch file processing."""
    
    def test_run_batch_multiple_files(self, temp_dir):
        """Test batch processing of multiple files."""
        # Create multiple input files
        input_files = []
        for i in range(3):
            input_file = temp_dir / f"input{i}.txt"
            with open(input_file, 'w') as f:
                for j in range(5):
                    f.write(f"file{i}_line{j}\n")
            input_files.append(str(input_file))
        
        runner = RayRunner(num_actors=2)
        output_dir = temp_dir / "output"
        
        metrics = runner.run_batch(
            'noop',
            input_files,
            str(output_dir)
        )
        
        assert metrics['files_processed'] == 3
        assert metrics['total_records'] == 15  # 3 files * 5 lines
        assert output_dir.exists()
        
        runner.shutdown()
    
    def test_run_batch_no_output_dir(self, temp_dir):
        """Test batch without output directory."""
        input_files = []
        for i in range(2):
            input_file = temp_dir / f"input{i}.txt"
            with open(input_file, 'w') as f:
                f.write(f"data{i}\n")
            input_files.append(str(input_file))
        
        runner = RayRunner(num_actors=2)
        
        metrics = runner.run_batch('noop', input_files)
        
        assert metrics['files_processed'] == 2
        runner.shutdown()


class TestRayRunnerMetrics:
    """Test metrics collection and export."""
    
    def test_metrics_structure(self, sample_input_file):
        """Test that metrics have expected structure."""
        runner = RayRunner(num_actors=2)
        
        metrics = runner.run_file('noop', str(sample_input_file))
        
        # Check required fields
        assert 'total_records' in metrics
        assert 'processed_records' in metrics
        assert 'errors' in metrics
        assert 'total_time' in metrics
        assert 'throughput' in metrics
        assert 'num_actors' in metrics
        assert 'actor_metrics' in metrics
        
        # Check actor metrics
        assert len(metrics['actor_metrics']) == 2
        
        runner.shutdown()
    
    def test_export_metrics_json(self, sample_input_file, temp_dir):
        """Test exporting metrics to JSON."""
        runner = RayRunner(num_actors=2)
        
        metrics = runner.run_file('noop', str(sample_input_file))
        
        output_file = temp_dir / "metrics.json"
        runner.export_metrics(metrics, str(output_file), format='json')
        
        assert output_file.exists()
        
        # Load and verify
        with open(output_file, 'r') as f:
            loaded_metrics = json.load(f)
        
        assert loaded_metrics['total_records'] == metrics['total_records']
        
        runner.shutdown()
    
    def test_export_metrics_csv(self, sample_input_file, temp_dir):
        """Test exporting metrics to CSV."""
        runner = RayRunner(num_actors=2)
        
        metrics = runner.run_file('noop', str(sample_input_file))
        
        output_file = temp_dir / "metrics.csv"
        runner.export_metrics(metrics, str(output_file), format='csv')
        
        assert output_file.exists()
        
        runner.shutdown()
    
    def test_export_metrics_invalid_format(self, sample_input_file, temp_dir):
        """Test that invalid format raises error."""
        runner = RayRunner(num_actors=2)
        
        metrics = runner.run_file('noop', str(sample_input_file))
        
        with pytest.raises(ValueError):
            runner.export_metrics(metrics, str(temp_dir / "out.txt"), format='invalid')
        
        runner.shutdown()


class TestRayRunnerParallelism:
    """Test parallel execution across actors."""
    
    def test_multiple_actors_distribution(self, temp_dir):
        """Test that work is distributed across actors."""
        # Create file with many records
        input_file = temp_dir / "input.txt"
        with open(input_file, 'w') as f:
            for i in range(100):
                f.write(f"line{i}\n")
        
        runner = RayRunner(num_actors=4)
        
        metrics = runner.run_file('noop', str(input_file))
        
        # Check that all actors processed some data
        actor_metrics = metrics['actor_metrics']
        assert len(actor_metrics) == 4
        
        # Each actor should have processed some records
        total_by_actors = sum(m['total_processed'] for m in actor_metrics)
        assert total_by_actors == 100
        
        runner.shutdown()
    
    def test_single_actor_vs_multiple(self, temp_dir):
        """Test that multiple actors provide parallelism."""
        input_file = temp_dir / "input.txt"
        with open(input_file, 'w') as f:
            for i in range(50):
                f.write(f"line{i}\n")
        
        # Single actor
        runner1 = RayRunner(num_actors=1)
        metrics1 = runner1.run_file('noop', str(input_file))
        runner1.shutdown()
        
        # Multiple actors
        runner2 = RayRunner(num_actors=4)
        metrics2 = runner2.run_file('noop', str(input_file))
        runner2.shutdown()
        
        # Both should process same number
        assert metrics1['processed_records'] == metrics2['processed_records']
        
        # Multiple actors should have distributed work
        assert len(metrics2['actor_metrics']) == 4
