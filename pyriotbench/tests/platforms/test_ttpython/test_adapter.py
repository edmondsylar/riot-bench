"""Tests for TTPython platform adapter.

This module tests the integration between PyRIoTBench tasks and TTPython.
"""

import pytest
import sys
import os

# Ensure pyriotbench is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from pyriotbench.tasks.noop import NoOpTask
from pyriotbench.platforms.ttpython import wrap_task_as_sq, TTPythonRunner


class TestTTPythonAdapter:
    """Test the TTPython adapter wrapping functionality."""
    
    def test_wrap_task_as_sq(self):
        """Test that a task can be wrapped as an SQ."""
        config = {}
        sq = wrap_task_as_sq(NoOpTask, config)
        
        # Should be a function
        assert callable(sq), "Wrapped task should be callable"
        assert sq.__name__ == "NoOpTask_SQ", "Should have descriptive name"
    
    @pytest.mark.skip(reason="Direct SQ invocation requires TTPython Token objects")
    def test_wrapped_task_execution(self):
        """Test that wrapped task can execute."""
        # This test is skipped because calling @SQify functions directly
        # requires TTPython Token objects, not raw values.
        # The adapter is designed to work within TTPython's execution framework.
        pass
    
    @pytest.mark.skip(reason="Direct SQ invocation requires TTPython Token objects")
    def test_wrapped_task_with_dict_input(self):
        """Test wrapped task with dictionary input."""
        # This test is skipped because calling @SQify functions directly
        # requires TTPython Token objects, not raw values.
        pass


class TestTTPythonRunner:
    """Test the TTPython runner."""
    
    def test_runner_initialization(self):
        """Test creating a TTPython runner."""
        runner = TTPythonRunner(config={})
        assert runner is not None
        assert runner.config == {}
    
    def test_create_pipeline_single_task(self):
        """Test creating a pipeline with a single task."""
        runner = TTPythonRunner(config={})
        
        # Create pipeline with NoOpTask
        task_sqs, pipeline_func = runner.create_pipeline([NoOpTask])
        
        assert task_sqs is not None, "Should create task SQs"
        assert len(task_sqs) == 1, "Should have one SQ"
        assert pipeline_func is not None, "Should create pipeline function"
        assert callable(pipeline_func), "Pipeline should be callable"
    
    def test_run_pipeline(self):
        """Test running a simple pipeline."""
        runner = TTPythonRunner(config={})
        
        # Create pipeline
        task_sqs, pipeline_func = runner.create_pipeline([NoOpTask])
        
        # Run with simple input
        input_data = [1, 2, 3]
        results = runner.run(task_sqs, pipeline_func, input_data)
        
        assert results is not None, "Should return results"
        assert len(results) == len(input_data), "Should have result for each input"
        assert results == [1, 2, 3], "Should pass through values"


class TestTTPythonIntegration:
    """Integration tests for TTPython platform."""
    
    def test_noop_task_can_be_wrapped(self):
        """Test that NoOpTask can be wrapped as SQ."""
        from pyriotbench.tasks.noop import NoOpTask
        from pyriotbench.platforms.ttpython import wrap_task_as_sq
        
        sq = wrap_task_as_sq(NoOpTask, {})
        assert sq is not None
        assert callable(sq)
    
    def test_pipeline_creation_doesnt_crash(self):
        """Test that pipeline creation doesn't crash."""
        from pyriotbench.tasks.noop import NoOpTask
        from pyriotbench.platforms.ttpython import TTPythonRunner
        
        runner = TTPythonRunner({})
        
        # This should not raise an exception
        try:
            task_sqs, func = runner.create_pipeline([NoOpTask])
            assert task_sqs is not None
            assert len(task_sqs) > 0
        except Exception as e:
            pytest.fail(f"Pipeline creation failed: {e}")
