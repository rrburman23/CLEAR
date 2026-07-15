import pytest

from target import fibonacci


def test_normal_case() -> None:
    assert fibonacci(5) == 5


def test_zero() -> None:
    assert fibonacci(0) == 0


def test_one() -> None:
    assert fibonacci(1) == 1


def test_large_input() -> None:
    assert fibonacci(12) == 144


def test_negative_input() -> None:
    with pytest.raises(ValueError):
        fibonacci(-1)
