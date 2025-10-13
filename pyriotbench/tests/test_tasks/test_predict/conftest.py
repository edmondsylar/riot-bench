"""Pytest configuration for predictive task tests."""

import tempfile
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.tree import DecisionTreeClassifier


@pytest.fixture
def sample_decision_tree_model():
    """Create a simple trained decision tree model for testing."""
    # Create simple training data
    # Features: [sensor1, sensor2, sensor3, sensor4, sensor5]
    # Classes: 0=Bad, 1=Average, 2=Good, 3=VeryGood, 4=Excellent
    np.random.seed(42)
    
    # Generate synthetic training data
    X_train = np.array([
        # Bad: low values
        [0.1, 0.2, 0.1, 0.15, 0.2],
        [0.15, 0.1, 0.2, 0.1, 0.15],
        [0.2, 0.15, 0.1, 0.2, 0.1],
        # Average: medium-low values
        [0.3, 0.4, 0.35, 0.4, 0.3],
        [0.35, 0.3, 0.4, 0.3, 0.35],
        [0.4, 0.35, 0.3, 0.35, 0.4],
        # Good: medium values
        [0.5, 0.6, 0.55, 0.6, 0.5],
        [0.55, 0.5, 0.6, 0.5, 0.55],
        [0.6, 0.55, 0.5, 0.55, 0.6],
        # VeryGood: medium-high values
        [0.7, 0.75, 0.7, 0.75, 0.7],
        [0.75, 0.7, 0.75, 0.7, 0.75],
        [0.7, 0.75, 0.7, 0.75, 0.7],
        # Excellent: high values
        [0.9, 0.95, 0.9, 0.95, 0.9],
        [0.95, 0.9, 0.95, 0.9, 0.95],
        [0.9, 0.95, 0.9, 0.95, 0.9],
    ])
    
    y_train = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4])
    
    # Train simple decision tree
    model = DecisionTreeClassifier(random_state=42, max_depth=3)
    model.fit(X_train, y_train)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.joblib') as f:
        joblib.dump(model, f)
        temp_path = Path(f.name)
    
    yield temp_path, model
    
    # Cleanup
    temp_path.unlink()


@pytest.fixture
def decision_tree_config(sample_decision_tree_model):
    """Configuration for decision tree task."""
    model_path, model = sample_decision_tree_model
    
    return {
        'CLASSIFICATION.DECISION_TREE.MODEL_PATH': str(model_path),
        'CLASSIFICATION.DECISION_TREE.CLASS_NAMES': 'Bad,Average,Good,VeryGood,Excellent',
        'CLASSIFICATION.DECISION_TREE.FEATURE_COUNT': 5,
        'CLASSIFICATION.DECISION_TREE.USE_MSG_FIELD': 0,
    }, model


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing classification."""
    return [
        # Bad examples (low values)
        "0.1,0.15,0.12,0.18,0.14",
        "0.15,0.1,0.2,0.1,0.15",
        # Average examples (medium-low values)
        "0.35,0.4,0.38,0.4,0.35",
        "0.4,0.35,0.3,0.35,0.4",
        # Good examples (medium values)
        "0.55,0.6,0.58,0.6,0.55",
        "0.6,0.55,0.5,0.55,0.6",
        # VeryGood examples (medium-high values)
        "0.75,0.7,0.75,0.7,0.75",
        "0.7,0.75,0.7,0.75,0.7",
        # Excellent examples (high values)
        "0.95,0.9,0.95,0.9,0.95",
        "0.9,0.95,0.9,0.95,0.9",
    ]
