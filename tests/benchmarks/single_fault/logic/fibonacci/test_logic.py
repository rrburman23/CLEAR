import pytest
from.target import fibonacci


def test_normal_case() -> None:
    """Tests standard Fibonacci sequence values."""
    assert fibonacci(5) == 5
    assert fibonacci(6) == 8
    assert fibonacci(10) == 55


def test_boundary_case() -> None:
    """Tests the sequence boundaries (n=0, n=1)."""
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_large_input_case() -> None:
    """Tests a larger number to ensure recurrence consistency."""
    # Fibonacci(12) = 144
    assert fibonacci(12) == 144


def test_negative_input() -> None:
    """
    Tests edge behavior for negative input.
    Note: If your target doesn't raise a ValueError,
    you might expect a specific return based on your requirements.
    """
    # Assuming input < 0 should return the input or raise an error.
    # Adjust based on your specific target.py implementation requirements.
    assert fibonacci(-1) == -1
