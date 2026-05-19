"""Unit test suite for math_ops.py."""

from math_ops import add_numbers


def test_add_numbers():
    """Validates the addition logic."""
    assert add_numbers(5, 5) == 10, "Expected 5 + 5 to equal 10"
    assert add_numbers(-3, 7) == 4, "Expected -3 + 7 to equal 4"
    assert add_numbers(0, 0) == 0, "Expected 0 + 0 to equal 0"