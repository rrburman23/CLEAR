import pytest
from target import average


def test_normal_case() -> None:
    assert average([1, 2, 3]) == pytest.approx(2.0)


def test_boundary_case() -> None:
    assert average([10]) == 10.0


def test_empty_case() -> None:
    with pytest.raises(ZeroDivisionError):
        average([])
