import pytest
from target import average


def test_normal_average() -> None:
    assert average([2, 4, 6]) == pytest.approx(4.0)


def test_empty_list_returns_zero() -> None:
    # Target currently crashes/divides by zero
    assert average([]) == 0


def test_single_element() -> None:
    assert average([10]) == 10.0
