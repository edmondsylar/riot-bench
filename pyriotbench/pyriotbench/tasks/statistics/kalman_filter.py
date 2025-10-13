"""
Kalman Filter Task - 1D Sensor Noise Reduction.

This task applies a 1D Kalman filter to reduce noise in sensor measurements.
The Kalman filter is an optimal estimator that recursively updates predictions
based on noisy measurements, providing smooth estimates of the true signal.

Based on: Java RIoTBench KalmanFilter.java
Reference: "Kalman Filter For Dummies" by Bilgin Esme
"""

import logging
import random
import threading
from typing import Any, ClassVar, Optional

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import StatefulTask


@register_task("kalman_filter")
class KalmanFilterTask(StatefulTask):
    """
    1D Kalman filter for sensor noise reduction.
    
    Applies Kalman filtering to reduce noise in sensor measurements.
    Maintains state across invocations for continuous estimation.
    
    The algorithm consists of two steps:
    1. Time Update (Prediction): Predict current state from previous estimate
    2. Measurement Update (Correction): Correct prediction using new measurement
    
    Configuration:
        STATISTICS.KALMAN_FILTER.USE_MSG_FIELD: Field index (0=direct, >0=CSV field, <0=random)
        STATISTICS.KALMAN_FILTER.PROCESS_NOISE: Process noise covariance (q)
        STATISTICS.KALMAN_FILTER.SENSOR_NOISE: Sensor noise covariance (r)
        STATISTICS.KALMAN_FILTER.ESTIMATED_ERROR: Initial error covariance
    
    Returns:
        Filtered estimate (float)
    
    Example:
        >>> task = KalmanFilterTask()
        >>> task.config = {
        ...     "STATISTICS.KALMAN_FILTER.PROCESS_NOISE": 0.1,
        ...     "STATISTICS.KALMAN_FILTER.SENSOR_NOISE": 0.1,
        ... }
        >>> task.setup()
        >>> # Process noisy measurements
        >>> estimate1 = task.execute("10.5")  # Returns smoothed estimate
        >>> estimate2 = task.execute("10.8")  # Uses state from previous call
    """
    
    # Class variables (shared configuration)
    _use_msg_field: ClassVar[int] = 0
    _q_process_noise: ClassVar[float] = 0.1
    _r_sensor_noise: ClassVar[float] = 0.1
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def setup(self) -> None:
        """
        Setup Kalman filter configuration (thread-safe).
        
        Loads configuration parameters and initializes instance state.
        Configuration is shared across instances, but state is per-instance.
        """
        super().setup()
        
        with self._setup_lock:
            if not self._setup_done:
                # Load configuration (shared across instances)
                self.__class__._use_msg_field = int(
                    self.config.get('STATISTICS.KALMAN_FILTER.USE_MSG_FIELD', 0)
                )
                
                self.__class__._q_process_noise = float(
                    self.config.get('STATISTICS.KALMAN_FILTER.PROCESS_NOISE', 0.1)
                )
                
                self.__class__._r_sensor_noise = float(
                    self.config.get('STATISTICS.KALMAN_FILTER.SENSOR_NOISE', 0.1)
                )
                
                self._logger.info(
                    f"Kalman filter configured: "
                    f"use_field={self._use_msg_field}, "
                    f"q={self._q_process_noise}, "
                    f"r={self._r_sensor_noise}"
                )
                
                self.__class__._setup_done = True
        
        # Instance state (unique per task instance)
        self.p0_prior_error_cov = float(
            self.config.get('STATISTICS.KALMAN_FILTER.ESTIMATED_ERROR', 1.0)
        )
        self.x0_previous_est = 0.0
        
        self._logger.debug(
            f"Kalman filter instance initialized: "
            f"p0={self.p0_prior_error_cov}, x0={self.x0_previous_est}"
        )
    
    def do_task(self, input_data: Any) -> float:
        """
        Apply Kalman filter to measurement.
        
        Implements the Kalman filter algorithm:
        1. Time Update: p1 = p0 + q
        2. Measurement Update:
           - k = p1 / (p1 + r)  [Kalman gain]
           - x1 = x0 + k * (z - x0)  [Updated estimate]
           - p1 = (1 - k) * p1  [Updated error covariance]
        3. Update state: x0 = x1, p0 = p1
        
        Args:
            input_data: Input string (CSV format or single value)
        
        Returns:
            Filtered estimate (float)
        
        Raises:
            ValueError: If measurement cannot be extracted
        """
        # Extract measurement
        try:
            if self._use_msg_field > 0:
                # Extract from CSV field
                fields = str(input_data).split(',')
                if self._use_msg_field - 1 >= len(fields):
                    self._logger.warning(
                        f"Field index {self._use_msg_field} out of range "
                        f"(only {len(fields)} fields available)"
                    )
                    return float('-inf')
                
                z_measured = float(fields[self._use_msg_field - 1].strip())
                
            elif self._use_msg_field == 0:
                # Use entire input as measurement
                z_measured = float(str(input_data).strip())
                
            else:
                # Generate random value for testing (negative = random mode)
                # Default: 10 +/- 1.0
                z_measured = 10.0 + random.uniform(-1.0, 1.0)
        
        except (ValueError, IndexError) as e:
            self._logger.error(f"Failed to extract measurement: {e}")
            return float('-inf')
        
        # Time Update (Prediction)
        p1_current_error_cov = self.p0_prior_error_cov + self._q_process_noise
        
        # Measurement Update (Correction)
        # Calculate Kalman gain
        k_kalman_gain = p1_current_error_cov / (
            p1_current_error_cov + self._r_sensor_noise
        )
        
        # Update estimate with measurement
        x1_current_est = self.x0_previous_est + k_kalman_gain * (
            z_measured - self.x0_previous_est
        )
        
        # Update error covariance
        p1_current_error_cov = (1.0 - k_kalman_gain) * p1_current_error_cov
        
        # Update state for next iteration
        self.x0_previous_est = x1_current_est
        self.p0_prior_error_cov = p1_current_error_cov
        
        self._logger.debug(
            f"Kalman filter: measured={z_measured:.3f}, "
            f"estimated={x1_current_est:.3f}, "
            f"error_cov={p1_current_error_cov:.6f}, "
            f"kalman_gain={k_kalman_gain:.6f}"
        )
        
        return x1_current_est
    
    def tear_down(self) -> None:
        """Cleanup resources and reset state."""
        super().tear_down()
        # Reset instance state
        self.p0_prior_error_cov = 1.0
        self.x0_previous_est = 0.0
