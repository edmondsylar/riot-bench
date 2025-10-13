"""
Tests for DecisionTreeClassify task.

Tests cover:
- Task registration
- Setup and model loading
- Classification accuracy
- Class name extraction
- Feature extraction from CSV
- Field skipping
- Error handling
- Thread safety
"""

import threading

import pytest

from pyriotbench.core.registry import TaskRegistry
from pyriotbench.tasks.predict.decision_tree_classify import DecisionTreeClassify


class TestDecisionTreeRegistration:
    """Test task registration and discovery."""
    
    def test_task_is_registered(self):
        """Test that DecisionTreeClassify is registered."""
        assert TaskRegistry.is_registered("decision_tree_classify")
    
    def test_can_get_task_class(self):
        """Test retrieving task class from registry."""
        task_cls = TaskRegistry.get("decision_tree_classify")
        assert task_cls is DecisionTreeClassify
    
    def test_can_create_task_instance(self):
        """Test creating task instance."""
        task = TaskRegistry.create("decision_tree_classify")
        assert isinstance(task, DecisionTreeClassify)


class TestDecisionTreeSetup:
    """Test setup and initialization."""
    
    def test_setup_loads_model(self, decision_tree_config):
        """Test that setup loads decision tree model."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        assert DecisionTreeClassify._model is not None
        assert DecisionTreeClassify._setup_done is True
        assert len(DecisionTreeClassify._class_names) == 5
        assert DecisionTreeClassify._feature_count == 5
    
    def test_setup_without_config_raises_error(self):
        """Test that setup without config raises error."""
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = {}
        
        with pytest.raises(ValueError, match="MODEL_PATH not configured"):
            task.setup()
    
    def test_setup_with_invalid_path_raises_error(self):
        """Test that setup with invalid path raises error."""
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = {
            'CLASSIFICATION.DECISION_TREE.MODEL_PATH': '/nonexistent/path/model.joblib'
        }
        
        with pytest.raises(FileNotFoundError):
            task.setup()
    
    def test_setup_with_auto_detection(self, sample_decision_tree_model):
        """Test setup with auto-detection of features and classes."""
        model_path, model = sample_decision_tree_model
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        config = {
            'CLASSIFICATION.DECISION_TREE.MODEL_PATH': str(model_path),
            # No CLASS_NAMES or FEATURE_COUNT specified
        }
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        # Should auto-detect
        assert DecisionTreeClassify._feature_count == 5
        assert len(DecisionTreeClassify._class_names) == 5
        # Auto-generated names
        assert DecisionTreeClassify._class_names[0] == "Class_0"


class TestDecisionTreeClassification:
    """Test classification functionality."""
    
    def test_classify_bad_example(self, decision_tree_config):
        """Test classifying a 'Bad' example."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        # Low values should be classified as Bad (class 0)
        result = task.do_task("0.1,0.15,0.12,0.18,0.14")
        
        assert result == 0.0  # Class index for Bad
        classification = task.get_classification_result()
        assert classification['class_name'] == 'Bad'
        assert classification['class_index'] == 0
    
    def test_classify_excellent_example(self, decision_tree_config):
        """Test classifying an 'Excellent' example."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        # High values should be classified as Excellent (class 4)
        result = task.do_task("0.95,0.9,0.95,0.9,0.95")
        
        assert result == 4.0  # Class index for Excellent
        classification = task.get_classification_result()
        assert classification['class_name'] == 'Excellent'
        assert classification['class_index'] == 4
    
    def test_classify_multiple_examples(self, decision_tree_config, sample_csv_data):
        """Test classifying multiple examples."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        results = []
        for csv_line in sample_csv_data:
            result = task.do_task(csv_line)
            results.append(result)
        
        # Should have classified all examples
        assert len(results) == len(sample_csv_data)
        
        # All should be valid class indices (0-4)
        assert all(0.0 <= r <= 4.0 or r == float('-inf') for r in results)
    
    def test_metadata_contains_features(self, decision_tree_config):
        """Test that classification result contains input features."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        task.do_task("0.5,0.6,0.55,0.6,0.5")
        classification = task.get_classification_result()
        
        assert 'features' in classification
        assert len(classification['features']) == 5
        assert classification['features'][0] == 0.5


class TestDecisionTreeFieldExtraction:
    """Test CSV field extraction and skipping."""
    
    def test_skip_fields(self, decision_tree_config):
        """Test skipping leading fields."""
        config, model = decision_tree_config
        config['CLASSIFICATION.DECISION_TREE.USE_MSG_FIELD'] = 2  # Skip first 2 fields
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        # Input: id,timestamp,f1,f2,f3,f4,f5
        result = task.do_task("sensor001,1234567890,0.1,0.15,0.12,0.18,0.14")
        
        # Should successfully classify (using fields after first 2)
        assert result in (0.0, 1.0, 2.0, 3.0, 4.0)
    
    def test_wrong_feature_count(self, decision_tree_config):
        """Test with wrong number of features."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        # Only 3 features instead of 5
        result = task.do_task("0.5,0.6,0.55")
        
        assert result == float('-inf')  # Error
    
    def test_invalid_feature_values(self, decision_tree_config):
        """Test with non-numeric feature values."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        result = task.do_task("0.5,invalid,0.55,0.6,0.5")
        
        assert result == float('-inf')  # Error


class TestDecisionTreeExecution:
    """Test full execution with timing."""
    
    def test_execute_records_timing(self, decision_tree_config):
        """Test that execute records timing metrics."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        result_value = task.execute("0.5,0.6,0.55,0.6,0.5")
        result = task.get_last_result()
        classification = task.get_classification_result()
        
        assert result_value in (0.0, 1.0, 2.0, 3.0, 4.0)
        assert result.value == result_value
        assert result.execution_time_ms > 0
        assert result.success is True
        assert 'class_name' in classification
    
    def test_execute_with_error(self, decision_tree_config):
        """Test execute with invalid input."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        result_value = task.execute("invalid,data,here")
        result = task.get_last_result()
        
        assert result_value == float('-inf')
        assert result.value == float('-inf')


class TestDecisionTreeThreadSafety:
    """Test thread safety of setup."""
    
    def test_concurrent_setup(self, decision_tree_config):
        """Test that concurrent setup is thread-safe."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        results = []
        errors = []
        
        def setup_task():
            try:
                task = DecisionTreeClassify()
                task.config = config
                task.setup()
                results.append(DecisionTreeClassify._model)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=setup_task) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have no errors
        assert len(errors) == 0
        
        # All results should reference the same model
        assert len(set(id(m) for m in results)) == 1
    
    def test_concurrent_classification(self, decision_tree_config, sample_csv_data):
        """Test concurrent classification."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        # Setup once
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        results = []
        errors = []
        
        def classify():
            try:
                # Create new task instance
                t = DecisionTreeClassify()
                t.config = config
                t.setup()
                
                # Classify a few examples
                for csv_line in sample_csv_data[:3]:
                    result = t.do_task(csv_line)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=classify) for _ in range(3)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have no errors
        assert len(errors) == 0
        
        # Should have classified all examples
        assert len(results) == 3 * 3  # 3 threads × 3 examples


class TestDecisionTreeTearDown:
    """Test teardown and cleanup."""
    
    def test_tear_down(self, decision_tree_config):
        """Test tear_down completes without error."""
        config, model = decision_tree_config
        
        # Reset state
        DecisionTreeClassify._setup_done = False
        DecisionTreeClassify._model = None
        
        task = DecisionTreeClassify()
        task.config = config
        task.setup()
        
        # Should not raise
        task.tear_down()
