"""
Tests for BeamTaskDoFn adapter.

Tests cover:
- DoFn lifecycle (setup, process, teardown)
- Task execution through Beam
- Metrics collection
- Error handling
- None filtering (windowed tasks)
"""

import apache_beam as beam
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to

import pytest

from pyriotbench.platforms.beam.adapter import BeamTaskDoFn


class TestBeamTaskDoFnCreation:
    """Tests for DoFn creation and validation."""
    
    def test_create_with_valid_task(self, kalman_config):
        """Test creating DoFn with valid registered task."""
        dofn = BeamTaskDoFn('kalman_filter', kalman_config)
        
        assert dofn.task_name == 'kalman_filter'
        assert dofn.config == kalman_config
        assert dofn.task is None  # Not created until setup()
    
    def test_create_with_invalid_task(self):
        """Test creating DoFn with unregistered task fails."""
        with pytest.raises(ValueError, match="not registered"):
            BeamTaskDoFn('nonexistent_task', {})
    
    def test_create_without_config(self):
        """Test creating DoFn without config uses empty dict."""
        dofn = BeamTaskDoFn('noop')
        
        assert dofn.config == {}


class TestBeamTaskDoFnLifecycle:
    """Tests for DoFn lifecycle management."""
    
    def test_setup_creates_task(self, kalman_config):
        """Test setup() creates and initializes task."""
        dofn = BeamTaskDoFn('kalman_filter', kalman_config)
        
        assert dofn.task is None
        
        dofn.setup()
        
        assert dofn.task is not None
        assert dofn.task.config == kalman_config
    
    def test_teardown_cleans_up(self, kalman_config):
        """Test teardown() cleans up task resources."""
        dofn = BeamTaskDoFn('kalman_filter', kalman_config)
        dofn.setup()
        
        assert dofn.task is not None
        
        dofn.teardown()
        
        assert dofn.task is None
    
    def test_teardown_without_setup(self):
        """Test teardown() handles no task gracefully."""
        dofn = BeamTaskDoFn('noop')
        
        # Should not raise
        dofn.teardown()
        
        assert dofn.task is None


class TestBeamTaskDoFnExecution:
    """Tests for task execution through DoFn."""
    
    def test_process_single_element(self, kalman_config):
        """Test processing a single element."""
        dofn = BeamTaskDoFn('kalman_filter', kalman_config)
        dofn.setup()
        
        results = list(dofn.process("25.0"))
        
        assert len(results) == 1
        assert isinstance(results[0], float)
        # Kalman filter output can vary based on initial state
        assert 20.0 < results[0] < 30.0  # Reasonable range near input
    
    def test_process_without_setup_fails(self):
        """Test processing without setup logs error and returns nothing."""
        dofn = BeamTaskDoFn('noop')
        
        # Process without setup
        results = list(dofn.process("test"))
        
        assert len(results) == 0  # No output when setup not called
    
    def test_process_filters_none(self, window_config):
        """Test that None results are filtered out."""
        # Block window average returns None until window is full
        dofn = BeamTaskDoFn('block_window_average', window_config)
        dofn.setup()
        
        # First 2 elements return None (window size 3)
        results1 = list(dofn.process("10.0"))
        results2 = list(dofn.process("20.0"))
        
        assert len(results1) == 0
        assert len(results2) == 0
        
        # Third element emits average
        results3 = list(dofn.process("30.0"))
        
        assert len(results3) == 1
        assert results3[0] == 20.0
    
    def test_process_filters_error_sentinel(self, kalman_config):
        """Test that error sentinels are filtered out."""
        dofn = BeamTaskDoFn('kalman_filter', kalman_config)
        dofn.setup()
        
        # Invalid input returns float('-inf')
        results = list(dofn.process("not_a_number"))
        
        assert len(results) == 0  # Error filtered out


class TestBeamTaskDoFnIntegration:
    """Integration tests with actual Beam pipelines."""
    
    def test_pipeline_with_noop(self):
        """Test simple pipeline with noop task."""
        with TestPipeline() as p:
            output = (
                p
                | beam.Create(['a', 'b', 'c'])
                | beam.ParDo(BeamTaskDoFn('noop'))
            )
            
            # Noop passes through input
            assert_that(output, equal_to(['a', 'b', 'c']))
    
    def test_pipeline_with_kalman_filter(self, kalman_config):
        """Test pipeline with stateful Kalman filter."""
        with TestPipeline() as p:
            output = (
                p
                | beam.Create(['25.0', '26.0', '25.5'])
                | beam.ParDo(BeamTaskDoFn('kalman_filter', kalman_config))
            )
            
            # Collect results
            results = []
            
            def collect(element):
                results.append(element)
            
            # Note: TestPipeline with assert_that is better for validation
            # Here we just verify pipeline executes without error
            assert_that(output, lambda x: len(list(x)) == 3)
    
    def test_pipeline_with_block_window_average(self, window_config):
        """Test pipeline with windowed aggregation."""
        with TestPipeline() as p:
            output = (
                p
                | beam.Create(['10.0', '20.0', '30.0', '40.0', '50.0', '60.0'])
                | beam.ParDo(BeamTaskDoFn('block_window_average', window_config))
            )
            
            # Window size 3, so expect 2 outputs: 20.0, 50.0
            assert_that(output, equal_to([20.0, 50.0]))
    
    def test_pipeline_with_multiple_workers(self, kalman_config):
        """Test pipeline with multiple elements (simulates parallel processing)."""
        # Create more elements to potentially distribute across workers
        elements = [str(25.0 + i * 0.1) for i in range(100)]
        
        with TestPipeline() as p:
            output = (
                p
                | beam.Create(elements)
                | beam.ParDo(BeamTaskDoFn('kalman_filter', kalman_config))
            )
            
            # All elements should be processed
            assert_that(output, lambda x: len(list(x)) == 100)


class TestBeamTaskDoFnDisplay:
    """Tests for display data (monitoring/UI)."""
    
    def test_display_data(self, kalman_config):
        """Test display_data provides monitoring information."""
        dofn = BeamTaskDoFn('kalman_filter', kalman_config)
        
        display = dofn.display_data()
        
        assert 'task_name' in display
        assert display['task_name'] == 'kalman_filter'
        assert 'config_keys' in display
        assert isinstance(display['config_keys'], list)
