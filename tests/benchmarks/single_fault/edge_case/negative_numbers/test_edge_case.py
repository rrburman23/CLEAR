import pytest
from target import absolute_difference


def test_positive_difference() -> None:
    assert absolute_difference(10, 5) == 5


def test_negative_difference() -> None:
    # Target was returning -5, expected 5
    assert absolute_difference(5, 10) == 5


def test_zero_case() -> None:
    assert absolute_difference(0, 0) == 0
