import pytest
from target import get_item


def test_normal_access() -> None:
    assert get_item([10, 20], 0) == 10


def test_out_of_bounds() -> None:
    # Based on your target.py docstring, it should return None
    assert get_item([10, 20], 5) is None


def test_negative_index() -> None:
    assert get_item([10, 20], -1) == 20
