import pytest
from target import calculate


def test_normal_addition() -> None:
    assert calculate("10 + 5") == 15
    assert calculate("100 - 42") == 58


def test_boundary_floats() -> None:
    assert calculate("10 / 4") == pytest.approx(2.5)


def test_special_invalid_expression() -> None:
    # The buggy implementation uses raw `eval()` without try/except.
    # This should return None per the docstring, but will raise an exception.
    assert calculate("abc") is None
    assert calculate("10 / 0") is None
