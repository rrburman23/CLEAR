import pytest
from target import factorial


def test_normal_case() -> None:
    assert factorial(5) == 120


def test_boundary_case() -> None:
    assert factorial(0) == 1


def test_negative_input() -> None:
    with pytest.raises(ValueError):
        factorial(-1)
