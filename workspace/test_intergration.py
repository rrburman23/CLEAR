"""Integration test suite for the workspace modules."""

import pytest
from math_ops import calculate_power
from string_ops import reverse_string


def test_calculate_power():
    """Validates the exponentiation logic."""
    assert calculate_power(2, 3) == 8, "2^3 should be 8"
    assert calculate_power(5, 2) == 25, "5^2 should be 25"


def test_reverse_string():
    """Validates the string reversal logic."""
    assert reverse_string("hello") == "olleh", "String was not reversed properly"
    assert reverse_string("CLEAR") == "RAELC", "String was not reversed properly"
