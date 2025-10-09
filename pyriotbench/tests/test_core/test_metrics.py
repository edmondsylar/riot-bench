"""
Tests for the metrics module.

This module tests TaskMetrics and MetricsAggregator functionality including:
- Metric creation and properties
- Time unit conversions
- Aggregate statistics
- CSV/JSON export
- Edge cases and error handling
"""

import json
import csv
import pytest
from pathlib import Path
from datetime import datetime

from pyriotbench.core.metrics import (
    TaskMetrics,
    MetricsAggregator,
    create_metric,
)


class TestTaskMetrics:
    """Tests for TaskMetrics dataclass."""
    
    def test_create_basic_metric(self):
        """Test creating a basic metric."""
        metric = TaskMetrics(
            task_name="test_task",
            execution_time_us=1500.0,
            status="success"
        )
        
        assert metric.task_name == "test_task"
        assert metric.execution_time_us == 1500.0
        assert metric.status == "success"
        assert metric.is_success
        assert not metric.is_error
    
    def test_time_conversions(self):
        """Test time unit conversion properties."""
        metric = TaskMetrics(
            task_name="test",
            execution_time_us=1_500_000.0  # 1.5 seconds
        )
        
        assert metric.execution_time_us == 1_500_000.0
        assert metric.execution_time_ms == 1_500.0
        assert metric.execution_time_s == 1.5
    
    def test_status_properties(self):
        """Test status check properties."""
        success = TaskMetrics("task", 1000, status="success")
        error = TaskMetrics("task", 1000, status="error")
        
        assert success.is_success
        assert not success.is_error
        assert not error.is_success
        assert error.is_error
    
    def test_throughput_calculation(self):
        """Test throughput calculation."""
        metric = TaskMetrics(
            task_name="test",
            execution_time_us=1_000_000.0,  # 1 second
            input_size=1000
        )
        
        assert metric.throughput_per_second == 1000.0
    
    def test_throughput_no_input_size(self):
        """Test throughput returns None when input_size not set."""
        metric = TaskMetrics("test", 1000.0)
        assert metric.throughput_per_second is None
    
    def test_throughput_zero_time(self):
        """Test throughput returns None for zero execution time."""
        metric = TaskMetrics("test", 0.0, input_size=1000)
        assert metric.throughput_per_second is None
    
    def test_timestamp_auto_generated(self):
        """Test that timestamp is automatically generated."""
        metric = TaskMetrics("test", 1000.0)
        
        # Should be valid ISO 8601
        dt = datetime.fromisoformat(metric.timestamp)
        assert isinstance(dt, datetime)
    
    def test_custom_timestamp(self):
        """Test using a custom timestamp."""
        custom_ts = "2025-01-01T12:00:00"
        metric = TaskMetrics("test", 1000.0, timestamp=custom_ts)
        assert metric.timestamp == custom_ts
    
    def test_metadata_field(self):
        """Test storing custom metadata."""
        metric = TaskMetrics(
            task_name="test",
            execution_time_us=1000.0,
            metadata={"platform": "beam", "worker_id": 5}
        )
        
        assert metric.metadata["platform"] == "beam"
        assert metric.metadata["worker_id"] == 5
    
    def test_to_dict(self):
        """Test converting metric to dictionary."""
        metric = TaskMetrics(
            task_name="test",
            execution_time_us=1500.0,
            status="success",
            input_size=100,
            output_size=50
        )
        
        d = metric.to_dict()
        assert d["task_name"] == "test"
        assert d["execution_time_us"] == 1500.0
        assert d["status"] == "success"
        assert d["input_size"] == 100
        assert d["output_size"] == 50
    
    def test_to_json(self):
        """Test converting metric to JSON."""
        metric = TaskMetrics("test", 1500.0, status="success")
        json_str = metric.to_json()
        
        # Should be valid JSON
        data = json.loads(json_str)
        assert data["task_name"] == "test"
        assert data["execution_time_us"] == 1500.0
    
    def test_from_dict(self):
        """Test creating metric from dictionary."""
        data = {
            "task_name": "test",
            "execution_time_us": 1500.0,
            "timestamp": "2025-01-01T12:00:00",
            "status": "success",
            "input_size": 100,
            "output_size": 50,
            "metadata": {"key": "value"}
        }
        
        metric = TaskMetrics.from_dict(data)
        assert metric.task_name == "test"
        assert metric.execution_time_us == 1500.0
        assert metric.input_size == 100
        assert metric.metadata["key"] == "value"
    
    def test_from_json(self):
        """Test creating metric from JSON."""
        json_str = json.dumps({
            "task_name": "test",
            "execution_time_us": 1500.0,
            "timestamp": "2025-01-01T12:00:00",
            "status": "success",
            "input_size": None,
            "output_size": None,
            "metadata": {}
        })
        
        metric = TaskMetrics.from_json(json_str)
        assert metric.task_name == "test"
        assert metric.execution_time_us == 1500.0
    
    def test_create_metric_convenience(self):
        """Test convenience function for creating metrics."""
        metric = create_metric("test", 1500.0, input_size=100)
        
        assert metric.task_name == "test"
        assert metric.execution_time_us == 1500.0
        assert metric.input_size == 100
        assert metric.status == "success"


class TestMetricsAggregator:
    """Tests for MetricsAggregator."""
    
    def test_create_aggregator(self):
        """Test creating an empty aggregator."""
        agg = MetricsAggregator("test_task")
        assert agg.task_name == "test_task"
        assert agg.count == 0
    
    def test_add_metric(self):
        """Test adding metrics to aggregator."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0))
        agg.add(TaskMetrics("test", 2000.0))
        
        assert agg.count == 2
    
    def test_add_wrong_task_name(self):
        """Test that adding metric with wrong task name raises error."""
        agg = MetricsAggregator("task_a")
        
        with pytest.raises(ValueError, match="does not match"):
            agg.add(TaskMetrics("task_b", 1000.0))
    
    def test_success_and_error_counts(self):
        """Test counting successes and errors."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        agg.add(TaskMetrics("test", 3000.0, status="error"))
        
        assert agg.count == 3
        assert agg.success_count == 2
        assert agg.error_count == 1
        assert agg.success_rate == 2/3
    
    def test_success_rate_empty(self):
        """Test success rate with no metrics."""
        agg = MetricsAggregator("test")
        assert agg.success_rate == 0.0
    
    def test_execution_times(self):
        """Test getting list of execution times."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        agg.add(TaskMetrics("test", 3000.0, status="error"))  # Should be excluded
        
        times = agg.execution_times_us
        assert times == [1000.0, 2000.0]
    
    def test_mean_time(self):
        """Test calculating mean execution time."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        agg.add(TaskMetrics("test", 3000.0, status="success"))
        
        assert agg.mean_time_us == 2000.0
    
    def test_median_time(self):
        """Test calculating median execution time."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        agg.add(TaskMetrics("test", 3000.0, status="success"))
        
        assert agg.median_time_us == 2000.0
    
    def test_min_max_time(self):
        """Test calculating min and max execution times."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1500.0, status="success"))
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 3000.0, status="success"))
        
        assert agg.min_time_us == 1000.0
        assert agg.max_time_us == 3000.0
    
    def test_stddev_time(self):
        """Test calculating standard deviation."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        agg.add(TaskMetrics("test", 3000.0, status="success"))
        
        assert agg.stddev_time_us is not None
        assert agg.stddev_time_us == pytest.approx(1000.0, rel=0.01)
    
    def test_stddev_single_value(self):
        """Test stddev returns None with single value."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        
        assert agg.stddev_time_us is None
    
    def test_total_time(self):
        """Test calculating total execution time."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        agg.add(TaskMetrics("test", 3000.0, status="success"))
        
        assert agg.total_time_us == 6000.0
    
    def test_percentiles(self):
        """Test percentile calculations."""
        agg = MetricsAggregator("test")
        for i in range(1, 101):  # 100 values: 1, 2, 3, ..., 100
            agg.add(TaskMetrics("test", float(i), status="success"))
        
        assert agg.p50 == pytest.approx(50.5, rel=0.01)
        assert agg.p95 == pytest.approx(95.05, rel=0.1)
        assert agg.p99 == pytest.approx(99.01, rel=0.1)
    
    def test_percentile_edge_cases(self):
        """Test percentile edge cases."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        
        # p0 should be min
        assert agg.percentile(0) == 1000.0
        # p100 should be max
        assert agg.percentile(100) == 2000.0
        # p50 should be median
        assert agg.percentile(50) == 1500.0
    
    def test_percentile_empty(self):
        """Test percentile returns None for empty aggregator."""
        agg = MetricsAggregator("test")
        assert agg.percentile(50) is None
    
    def test_stats_empty_aggregator(self):
        """Test that stats return None for empty aggregator."""
        agg = MetricsAggregator("test")
        
        assert agg.mean_time_us is None
        assert agg.median_time_us is None
        assert agg.min_time_us is None
        assert agg.max_time_us is None
        assert agg.stddev_time_us is None
        assert agg.p50 is None
        assert agg.p95 is None
        assert agg.p99 is None
    
    def test_summary(self):
        """Test generating summary statistics."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        agg.add(TaskMetrics("test", 3000.0, status="error"))
        
        summary = agg.summary()
        
        assert summary["task_name"] == "test"
        assert summary["count"] == 3
        assert summary["success_count"] == 2
        assert summary["error_count"] == 1
        assert summary["mean_time_us"] == 1500.0
        assert summary["total_time_us"] == 3000.0
    
    def test_to_csv(self, tmp_path: Path):
        """Test exporting metrics to CSV."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success", input_size=100))
        agg.add(TaskMetrics("test", 2000.0, status="success", input_size=200))
        
        csv_path = tmp_path / "metrics.csv"
        agg.to_csv(csv_path)
        
        # Read back and verify
        with open(csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        assert rows[0]["task_name"] == "test"
        assert float(rows[0]["execution_time_us"]) == 1000.0
        assert int(rows[0]["input_size"]) == 100
    
    def test_to_csv_empty(self, tmp_path: Path):
        """Test exporting empty aggregator to CSV."""
        agg = MetricsAggregator("test")
        csv_path = tmp_path / "empty.csv"
        agg.to_csv(csv_path)
        
        # Should create file with headers
        with open(csv_path, 'r', newline='') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert "task_name" in headers
            assert "execution_time_us" in headers
    
    def test_to_json(self, tmp_path: Path):
        """Test exporting metrics to JSON."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        
        json_path = tmp_path / "metrics.json"
        agg.to_json(json_path)
        
        # Read back and verify
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        assert data["task_name"] == "test"
        assert "summary" in data
        assert "metrics" in data
        assert len(data["metrics"]) == 2
        assert data["summary"]["mean_time_us"] == 1500.0
    
    def test_to_summary_csv(self, tmp_path: Path):
        """Test exporting summary to CSV."""
        agg = MetricsAggregator("test")
        agg.add(TaskMetrics("test", 1000.0, status="success"))
        agg.add(TaskMetrics("test", 2000.0, status="success"))
        
        csv_path = tmp_path / "summary.csv"
        agg.to_summary_csv(csv_path)
        
        # Read back and verify
        with open(csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 1
        assert rows[0]["task_name"] == "test"
        assert float(rows[0]["mean_time_us"]) == 1500.0
    
    def test_from_metrics(self):
        """Test creating aggregator from metrics list."""
        metrics = [
            TaskMetrics("test", 1000.0, status="success"),
            TaskMetrics("test", 2000.0, status="success"),
            TaskMetrics("test", 3000.0, status="success"),
        ]
        
        agg = MetricsAggregator.from_metrics(metrics)
        
        assert agg.task_name == "test"
        assert agg.count == 3
        assert agg.mean_time_us == 2000.0
    
    def test_from_metrics_empty(self):
        """Test that creating from empty list raises error."""
        with pytest.raises(ValueError, match="empty metrics list"):
            MetricsAggregator.from_metrics([])
    
    def test_from_metrics_mixed_tasks(self):
        """Test that creating from mixed task names raises error."""
        metrics = [
            TaskMetrics("task_a", 1000.0),
            TaskMetrics("task_b", 2000.0),
        ]
        
        with pytest.raises(ValueError, match="same task"):
            MetricsAggregator.from_metrics(metrics)
