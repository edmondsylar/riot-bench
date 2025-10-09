"""
Metrics collection and reporting for PyRIoTBench tasks.

This module provides lightweight dataclasses for tracking task execution metrics
such as timing, throughput, and resource usage. Metrics can be aggregated across
multiple executions and exported to various formats for analysis.

Key classes:
- TaskMetrics: Individual task execution metrics with timing stats
- MetricsAggregator: Aggregate metrics across multiple executions
"""

from __future__ import annotations

import json
import csv
import statistics
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


@dataclass
class TaskMetrics:
    """
    Metrics for a single task execution.
    
    This class captures timing and metadata for a task execution. It can compute
    aggregate statistics and export results in multiple formats.
    
    Attributes:
        task_name: Name of the task that was executed
        execution_time_us: Execution time in microseconds
        timestamp: ISO 8601 timestamp of execution
        status: Status of execution ('success' or 'error')
        input_size: Optional size of input data (bytes, records, etc.)
        output_size: Optional size of output data
        metadata: Optional additional metadata as key-value pairs
    
    Example:
        >>> metrics = TaskMetrics(
        ...     task_name="senml_parse",
        ...     execution_time_us=1250,
        ...     status="success"
        ... )
        >>> metrics.execution_time_ms
        1.25
        >>> metrics.to_dict()
        {'task_name': 'senml_parse', 'execution_time_us': 1250, ...}
    """
    
    task_name: str
    execution_time_us: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "success"  # 'success' or 'error'
    input_size: Optional[int] = None
    output_size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def execution_time_ms(self) -> float:
        """Execution time in milliseconds."""
        return self.execution_time_us / 1000.0
    
    @property
    def execution_time_s(self) -> float:
        """Execution time in seconds."""
        return self.execution_time_us / 1_000_000.0
    
    @property
    def is_success(self) -> bool:
        """Whether the execution was successful."""
        return self.status == "success"
    
    @property
    def is_error(self) -> bool:
        """Whether the execution encountered an error."""
        return self.status == "error"
    
    @property
    def throughput_per_second(self) -> Optional[float]:
        """
        Calculate throughput in items per second.
        
        Returns None if input_size is not set or execution time is zero.
        """
        if self.input_size is None or self.execution_time_s == 0:
            return None
        return self.input_size / self.execution_time_s
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metrics to a dictionary.
        
        Returns:
            Dictionary representation with all fields
        """
        return asdict(self)
    
    def to_json(self) -> str:
        """
        Convert metrics to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskMetrics:
        """
        Create TaskMetrics from a dictionary.
        
        Args:
            data: Dictionary with metric fields
        
        Returns:
            New TaskMetrics instance
        """
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> TaskMetrics:
        """
        Create TaskMetrics from JSON string.
        
        Args:
            json_str: JSON string representation
        
        Returns:
            New TaskMetrics instance
        """
        return cls.from_dict(json.loads(json_str))


@dataclass
class MetricsAggregator:
    """
    Aggregate metrics across multiple task executions.
    
    This class collects metrics from multiple runs and computes aggregate statistics
    like mean, median, min, max, percentiles, etc.
    
    Attributes:
        task_name: Name of the task being measured
        metrics: List of individual TaskMetrics instances
    
    Example:
        >>> aggregator = MetricsAggregator("senml_parse")
        >>> aggregator.add(TaskMetrics("senml_parse", 1250, status="success"))
        >>> aggregator.add(TaskMetrics("senml_parse", 1500, status="success"))
        >>> aggregator.mean_time_us
        1375.0
        >>> aggregator.success_rate
        1.0
    """
    
    task_name: str
    metrics: List[TaskMetrics] = field(default_factory=list)
    
    def add(self, metric: TaskMetrics) -> None:
        """
        Add a metric to the aggregator.
        
        Args:
            metric: TaskMetrics instance to add
        
        Raises:
            ValueError: If metric is for a different task
        """
        if metric.task_name != self.task_name:
            raise ValueError(
                f"Metric task name '{metric.task_name}' does not match "
                f"aggregator task name '{self.task_name}'"
            )
        self.metrics.append(metric)
    
    @property
    def count(self) -> int:
        """Total number of metrics."""
        return len(self.metrics)
    
    @property
    def success_count(self) -> int:
        """Number of successful executions."""
        return sum(1 for m in self.metrics if m.is_success)
    
    @property
    def error_count(self) -> int:
        """Number of failed executions."""
        return sum(1 for m in self.metrics if m.is_error)
    
    @property
    def success_rate(self) -> float:
        """Success rate as a fraction (0.0 to 1.0)."""
        if self.count == 0:
            return 0.0
        return self.success_count / self.count
    
    @property
    def execution_times_us(self) -> List[float]:
        """List of all execution times in microseconds."""
        return [m.execution_time_us for m in self.metrics if m.is_success]
    
    @property
    def mean_time_us(self) -> Optional[float]:
        """Mean execution time in microseconds (successful runs only)."""
        times = self.execution_times_us
        return statistics.mean(times) if times else None
    
    @property
    def median_time_us(self) -> Optional[float]:
        """Median execution time in microseconds (successful runs only)."""
        times = self.execution_times_us
        return statistics.median(times) if times else None
    
    @property
    def min_time_us(self) -> Optional[float]:
        """Minimum execution time in microseconds (successful runs only)."""
        times = self.execution_times_us
        return min(times) if times else None
    
    @property
    def max_time_us(self) -> Optional[float]:
        """Maximum execution time in microseconds (successful runs only)."""
        times = self.execution_times_us
        return max(times) if times else None
    
    @property
    def stddev_time_us(self) -> Optional[float]:
        """Standard deviation of execution time (successful runs only)."""
        times = self.execution_times_us
        return statistics.stdev(times) if len(times) > 1 else None
    
    @property
    def total_time_us(self) -> float:
        """Total execution time across all successful runs."""
        return sum(self.execution_times_us)
    
    def percentile(self, p: float) -> Optional[float]:
        """
        Calculate percentile of execution times.
        
        Args:
            p: Percentile to calculate (0-100)
        
        Returns:
            Execution time at the given percentile, or None if no data
        """
        times = sorted(self.execution_times_us)
        if not times:
            return None
        
        if p <= 0:
            return times[0]
        if p >= 100:
            return times[-1]
        
        # Linear interpolation
        index = (len(times) - 1) * p / 100.0
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(times):
            return times[-1]
        
        weight = index - lower
        return times[lower] * (1 - weight) + times[upper] * weight
    
    @property
    def p50(self) -> Optional[float]:
        """50th percentile (median) execution time."""
        return self.median_time_us
    
    @property
    def p95(self) -> Optional[float]:
        """95th percentile execution time."""
        return self.percentile(95)
    
    @property
    def p99(self) -> Optional[float]:
        """99th percentile execution time."""
        return self.percentile(99)
    
    def summary(self) -> Dict[str, Any]:
        """
        Generate a summary of aggregate statistics.
        
        Returns:
            Dictionary with aggregate statistics
        """
        return {
            "task_name": self.task_name,
            "count": self.count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "mean_time_us": self.mean_time_us,
            "median_time_us": self.median_time_us,
            "min_time_us": self.min_time_us,
            "max_time_us": self.max_time_us,
            "stddev_time_us": self.stddev_time_us,
            "total_time_us": self.total_time_us,
            "p50_us": self.p50,
            "p95_us": self.p95,
            "p99_us": self.p99,
        }
    
    def to_csv(self, path: Path | str) -> None:
        """
        Export individual metrics to CSV file.
        
        Args:
            path: Path to output CSV file
        """
        path = Path(path)
        
        if not self.metrics:
            # Write empty file with headers
            with open(path, 'w', newline='') as f:
                empty_writer = csv.writer(f)
                empty_writer.writerow([
                    "task_name", "execution_time_us", "timestamp", "status",
                    "input_size", "output_size"
                ])
            return
        
        with open(path, 'w', newline='') as f:
            writer: csv.DictWriter[str] = csv.DictWriter(f, fieldnames=[
                "task_name", "execution_time_us", "timestamp", "status",
                "input_size", "output_size"
            ])
            writer.writeheader()
            for metric in self.metrics:
                # Write only core fields, not metadata
                row = {
                    "task_name": metric.task_name,
                    "execution_time_us": metric.execution_time_us,
                    "timestamp": metric.timestamp,
                    "status": metric.status,
                    "input_size": metric.input_size,
                    "output_size": metric.output_size,
                }
                writer.writerow(row)
    
    def to_json(self, path: Path | str) -> None:
        """
        Export metrics to JSON file.
        
        Args:
            path: Path to output JSON file
        """
        path = Path(path)
        
        data = {
            "task_name": self.task_name,
            "summary": self.summary(),
            "metrics": [m.to_dict() for m in self.metrics]
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def to_summary_csv(self, path: Path | str) -> None:
        """
        Export aggregate summary to CSV file.
        
        Args:
            path: Path to output CSV file
        """
        path = Path(path)
        summary = self.summary()
        
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=summary.keys())
            writer.writeheader()
            writer.writerow(summary)
    
    @classmethod
    def from_metrics(cls, metrics: List[TaskMetrics]) -> MetricsAggregator:
        """
        Create aggregator from a list of metrics.
        
        Args:
            metrics: List of TaskMetrics instances
        
        Returns:
            New MetricsAggregator with metrics added
        
        Raises:
            ValueError: If metrics list is empty or contains different task names
        """
        if not metrics:
            raise ValueError("Cannot create aggregator from empty metrics list")
        
        task_names = {m.task_name for m in metrics}
        if len(task_names) > 1:
            raise ValueError(
                f"All metrics must be for the same task, found: {task_names}"
            )
        
        aggregator = cls(task_name=metrics[0].task_name)
        for metric in metrics:
            aggregator.add(metric)
        
        return aggregator


# Convenience function for quick metric creation
def create_metric(
    task_name: str,
    execution_time_us: float,
    status: str = "success",
    **kwargs: Any
) -> TaskMetrics:
    """
    Create a TaskMetrics instance with convenient defaults.
    
    Args:
        task_name: Name of the task
        execution_time_us: Execution time in microseconds
        status: Status of execution ('success' or 'error')
        **kwargs: Additional fields (input_size, output_size, metadata, etc.)
    
    Returns:
        New TaskMetrics instance
    
    Example:
        >>> metric = create_metric("parse", 1500, input_size=1024)
        >>> metric.execution_time_ms
        1.5
    """
    return TaskMetrics(
        task_name=task_name,
        execution_time_us=execution_time_us,
        status=status,
        **kwargs
    )
