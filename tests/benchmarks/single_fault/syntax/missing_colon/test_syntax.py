import pytest

from target import add


def test_adds_positive_numbers() -> None:
    assert add(2, 3) == 5


def test_adds_negative_numbers() -> None:
    assert add(-4, -6) == -10


def test_adds_mixed_numbers() -> None:
    assert add(-5, 8) == 3


def test_adds_zero() -> None:
    assert add(0, 0) == 0
