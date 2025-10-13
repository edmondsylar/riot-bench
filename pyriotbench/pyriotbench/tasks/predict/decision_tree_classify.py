"""
Decision Tree Classification Task - ML-based Classification.

This task loads a pre-trained scikit-learn decision tree model and
classifies input tuples into predefined classes. It's designed for
IoT sensor data classification (e.g., classifying system performance
as Bad, Average, Good, VeryGood, Excellent).

Based on: Java RIoTBench DecisionTreeClassify.java (originally using Weka J48)
Ported to: scikit-learn DecisionTreeClassifier
"""

import logging
import threading
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

import joblib
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import BaseTask, TaskResult


@register_task("decision_tree_classify")
class DecisionTreeClassify(BaseTask):
    """
    Decision tree classification for IoT sensor data.
    
    Loads a pre-trained scikit-learn decision tree model and classifies
    input CSV tuples into predefined classes. Returns both the class
    index (for flow control) and class name (via metadata).
    
    Configuration:
        CLASSIFICATION.DECISION_TREE.USE_MSG_FIELD: Field index (0=all fields, >0=skip N fields)
        CLASSIFICATION.DECISION_TREE.MODEL_PATH: Path to joblib-serialized sklearn model
        CLASSIFICATION.DECISION_TREE.CLASS_NAMES: Comma-separated class names
        CLASSIFICATION.DECISION_TREE.FEATURE_COUNT: Number of features expected
    
    Returns:
        Class index (float) - for compatibility with pipeline flow control
        Class name stored in metadata via _last_result
    
    Example:
        >>> task = DecisionTreeClassify()
        >>> task.config = {
        ...     "CLASSIFICATION.DECISION_TREE.MODEL_PATH": "model.joblib",
        ...     "CLASSIFICATION.DECISION_TREE.CLASS_NAMES": "Bad,Average,Good,VeryGood,Excellent",
        ...     "CLASSIFICATION.DECISION_TREE.FEATURE_COUNT": 5,
        ... }
        >>> task.setup()
        >>> result = task.execute("0.5,0.8,0.3,0.9,0.6")  # Returns class index
        >>> print(task.get_last_result().metadata['class_name'])  # Get class name
    """
    
    # Class variables (shared across instances)
    _model: ClassVar[Optional[DecisionTreeClassifier]] = None
    _class_names: ClassVar[List[str]] = []
    _feature_count: ClassVar[int] = 0
    _use_msg_field: ClassVar[int] = 0
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def setup(self) -> None:
        """
        Setup decision tree model (thread-safe, executed once).
        
        Loads the trained sklearn model from disk using joblib.
        Uses thread-safe initialization to ensure the model is loaded
        only once even when running with multiple threads.
        """
        super().setup()
        
        with self._setup_lock:
            if not self._setup_done:
                # Load configuration
                model_path_str = self.config.get('CLASSIFICATION.DECISION_TREE.MODEL_PATH')
                if not model_path_str:
                    raise ValueError("CLASSIFICATION.DECISION_TREE.MODEL_PATH not configured")
                
                model_path = Path(model_path_str).expanduser()
                
                # Load class names
                class_names_str = self.config.get('CLASSIFICATION.DECISION_TREE.CLASS_NAMES', '')
                if class_names_str:
                    self.__class__._class_names = [
                        name.strip() for name in class_names_str.split(',')
                    ]
                else:
                    # Default class names if not specified
                    self.__class__._class_names = []
                
                # Load feature count
                self.__class__._feature_count = int(
                    self.config.get('CLASSIFICATION.DECISION_TREE.FEATURE_COUNT', 0)
                )
                
                # Load field config
                self.__class__._use_msg_field = int(
                    self.config.get('CLASSIFICATION.DECISION_TREE.USE_MSG_FIELD', 0)
                )
                
                # Load sklearn model from joblib file
                try:
                    self.__class__._model = joblib.load(model_path)
                    
                    # Validate it's a decision tree
                    if not isinstance(self._model, DecisionTreeClassifier):
                        raise TypeError(
                            f"Expected DecisionTreeClassifier, got {type(self._model)}"
                        )
                    
                    # Auto-detect feature count if not specified
                    if self._feature_count == 0:
                        self.__class__._feature_count = self._model.n_features_in_
                    
                    # Auto-detect class names if not specified
                    if not self._class_names:
                        n_classes = self._model.n_classes_
                        self.__class__._class_names = [f"Class_{i}" for i in range(n_classes)]
                    
                    self._logger.info(
                        f"Loaded decision tree model from {model_path}: "
                        f"{self._feature_count} features, "
                        f"{len(self._class_names)} classes "
                        f"({', '.join(self._class_names)})"
                    )
                    
                except FileNotFoundError:
                    raise FileNotFoundError(
                        f"Decision tree model not found: {model_path}"
                    )
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to load decision tree model from {model_path}: {e}"
                    )
                
                self.__class__._setup_done = True
    
    def do_task(self, input_data: Any) -> float:
        """
        Classify input tuple using decision tree.
        
        Args:
            input_data: Input string (CSV format with feature values)
        
        Returns:
            Class index (float) for compatibility with flow control
            Class name is accessible via get_classification_result()
        
        Raises:
            RuntimeError: If model not loaded
        """
        if self._model is None:
            raise RuntimeError("Decision tree model not initialized. Call setup() first.")
        
        # Extract features from input
        try:
            # Parse CSV input
            fields = str(input_data).split(',')
            
            # Skip fields if configured
            if self._use_msg_field > 0:
                fields = fields[self._use_msg_field:]
            
            # Convert to float array
            if self._feature_count > 0:
                # Use specified number of features
                features = [float(f.strip()) for f in fields[:self._feature_count]]
            else:
                # Use all fields
                features = [float(f.strip()) for f in fields]
            
            # Validate feature count
            expected_features = self._model.n_features_in_
            if len(features) != expected_features:
                self._logger.warning(
                    f"Feature count mismatch: expected {expected_features}, "
                    f"got {len(features)}"
                )
                return float('-inf')
            
            # Convert to numpy array (2D for sklearn)
            X = np.array([features])
            
        except (ValueError, IndexError) as e:
            self._logger.error(f"Failed to extract features: {e}")
            return float('-inf')
        
        # Classify
        try:
            class_index = int(self._model.predict(X)[0])
            
            # Get class name
            if 0 <= class_index < len(self._class_names):
                class_name = self._class_names[class_index]
            else:
                class_name = f"Unknown_{class_index}"
                self._logger.warning(
                    f"Class index {class_index} out of range "
                    f"(only {len(self._class_names)} classes defined)"
                )
            
            # Store classification details for later retrieval
            # Note: This will be overwritten by execute(), so we store in instance variable
            self._classification_result = {
                'class_name': class_name,
                'class_index': class_index,
                'features': features,
            }
            
            self._logger.debug(
                f"Classification: {features} -> {class_name} (index={class_index})"
            )
            
            return float(class_index)
            
        except Exception as e:
            self._logger.error(f"Classification failed: {e}")
            return float('-inf')
    
    def get_classification_result(self) -> Dict[str, Any]:
        """
        Get the detailed classification result from the last do_task() call.
        
        Returns:
            Dictionary with class_name, class_index, and features
        """
        return getattr(self, '_classification_result', {})
    
    def tear_down(self) -> None:
        """Cleanup resources."""
        super().tear_down()
        # Note: We don't clear class variables here as they may be shared
