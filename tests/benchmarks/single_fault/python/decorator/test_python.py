import pytest
from target import multiply


def test_multiply_result() -> None:
    assert multiply(5, 5) == 25


def test_multiply_negative() -> None:
    assert multiply(-1, 5) == -5


def test_decorator_name_preservation() -> None:
    # This tests if the model properly implemented functools.wraps
    assert multiply.__name__ == "multiply"
