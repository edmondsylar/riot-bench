"""
PiByViete Task - Calculate π using Viète's infinite product formula.

This task computes the mathematical constant π (pi) using François Viète's
infinite product formula from 1593, one of the first formulas to represent
π as an infinite product.

Viète's Formula:
    2/π = √2/2 × √(2+√2)/2 × √(2+√(2+√2))/2 × ...

Algorithm:
    Starting from the innermost nested square root and working outward:
    1. Initialize factor f = 2
    2. For each iteration from n down to 2:
       - Start with f = 2
       - Apply nested square roots: f = 2 + √f (repeated i-1 times)
       - Take final square root: f = √f
       - Multiply into product: pi *= f/2
    3. Apply final correction: pi *= √2/2
    4. Invert: π = 2/pi

The formula converges relatively quickly, with ~1600 iterations giving
good precision.

Configuration:
    MATH.PI_VIETE.ITERS: Number of iterations (default: 1600)
        - Higher iterations = more precision
        - Diminishing returns after ~2000 iterations
        - Trade-off between accuracy and computation time

Example:
    >>> from pyriotbench.tasks.math import PiByViete
    >>> task = PiByViete()
    >>> task.config = {'MATH.PI_VIETE.ITERS': 1600}
    >>> task.setup()
    >>> result = task.execute('dummy')  # Input is ignored
    >>> print(f"π ≈ {result}")
    π ≈ 3.1415927

References:
    - https://en.wikipedia.org/wiki/Viète's_formula
    - http://www.codeproject.com/Articles/813185/Calculating-the-Number-PI-Through-Infinite-Sequenc
"""

import math
import threading
from typing import ClassVar, Optional

from pyriotbench.core.registry import register_task
from pyriotbench.core.task import StatefulTask


@register_task('pi_by_viete')
class PiByViete(StatefulTask):
    """
    Calculate π using Viète's infinite product formula.
    
    This is a computational benchmark that tests CPU performance with
    mathematical operations including square roots and nested iterations.
    
    Thread-safe with class-level configuration.
    
    Attributes:
        _iterations: Number of iterations for the calculation (class variable)
        _setup_lock: Thread lock for one-time setup (class variable)
        _setup_done: Flag to ensure setup runs once (class variable)
    """
    
    # Class variables (shared across all instances, thread-safe)
    _iterations: ClassVar[int] = 1600  # Default: good balance of speed vs precision
    _setup_lock: ClassVar[threading.Lock] = threading.Lock()
    _setup_done: ClassVar[bool] = False
    
    def __init__(self):
        """Initialize the task."""
        super().__init__()
    
    def setup(self) -> None:
        """
        Setup configuration for π calculation.
        
        Thread-safe initialization of class variables (done once).
        """
        super().setup()
        
        # Always reload configuration (prevents test contamination)
        with self._setup_lock:
            # Parse configuration
            iters = self.config.get('MATH.PI_VIETE.ITERS', 1600)
            PiByViete._iterations = int(iters)
            
            # Validate iterations parameter
            if PiByViete._iterations <= 0:
                raise ValueError(
                    f"ITERS parameter must be > 0 (got {PiByViete._iterations})"
                )
            
            PiByViete._setup_done = True
        
        self._logger.debug(
            f"PiByViete setup: iterations={self._iterations}"
        )
    
    def do_task(self, data: str) -> Optional[float]:
        """
        Calculate π using Viète's formula.
        
        The input data is ignored - this is a pure computational benchmark
        that always returns the same π approximation for a given number
        of iterations.
        
        Args:
            data: Input data (ignored, can be any string)
        
        Returns:
            Approximation of π
        """
        pi_value = self._calculate_pi_viete(self._iterations)
        
        self._logger.debug(f"Calculated π ≈ {pi_value} ({self._iterations} iterations)")
        
        return pi_value
    
    @staticmethod
    def _calculate_pi_viete(n: int) -> float:
        """
        Calculate π using Viète's infinite product formula.
        
        Implementation of:
        2/π = √2/2 × √(2+√2)/2 × √(2+√(2+√2))/2 × ...
        
        Args:
            n: Number of iterations
        
        Returns:
            Approximation of π
        """
        pi = 1.0
        
        # Work from n down to 2
        for i in range(n, 1, -1):
            # Start with factor = 2
            factor = 2.0
            
            # Build nested square roots: 2 + √(2 + √(2 + ...))
            # Repeat (i-1) times
            for j in range(1, i):
                factor = 2.0 + math.sqrt(factor)
            
            # Take final square root
            factor = math.sqrt(factor)
            
            # Accumulate into product
            pi *= factor / 2.0
        
        # Apply final correction factor
        pi *= math.sqrt(2.0) / 2.0
        
        # Invert to get π
        pi = 2.0 / pi
        
        return float(pi)
    
    def tear_down(self) -> None:
        """Clean up task state (nothing to clean for this stateless task)."""
        super().tear_down()
    
    @classmethod
    def get_pi_exact(cls) -> float:
        """
        Get the exact value of π from Python's math library for comparison.
        
        Returns:
            math.pi (the standard library's π value)
        """
        return math.pi
    
    @classmethod
    def calculate_error(cls, calculated_pi: float) -> dict:
        """
        Calculate error metrics for a calculated π value.
        
        Args:
            calculated_pi: The calculated approximation of π
        
        Returns:
            Dictionary with error metrics:
                - absolute_error: |calculated - actual|
                - relative_error: |calculated - actual| / actual
                - percent_error: relative_error * 100
                - correct_digits: Number of matching decimal digits
        """
        actual = math.pi
        abs_error = abs(calculated_pi - actual)
        rel_error = abs_error / actual
        
        # Count matching decimal digits
        calc_str = f"{calculated_pi:.15f}"
        actual_str = f"{actual:.15f}"
        correct_digits = 0
        for c1, c2 in zip(calc_str, actual_str):
            if c1 == c2:
                correct_digits += 1
            elif c1 != '.':  # Don't count decimal point
                break
        
        # Adjust for decimal point and leading '3'
        correct_digits = max(0, correct_digits - 2)
        
        return {
            'calculated': calculated_pi,
            'actual': actual,
            'absolute_error': abs_error,
            'relative_error': rel_error,
            'percent_error': rel_error * 100,
            'correct_digits': correct_digits
        }
