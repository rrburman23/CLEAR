import pytest

from target import square


def test_positive_square() -> None:
    assert square(4) == 16


def test_negative_square() -> None:
    assert square(-3) == 9


def test_zero_square() -> None:
    assert square(0) == 0
