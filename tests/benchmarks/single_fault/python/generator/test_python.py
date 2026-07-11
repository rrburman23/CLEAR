import pytest
from target import numbers


def test_normal_sequence() -> None:
    assert numbers(3) == [0, 1, 2]


def test_empty_sequence() -> None:
    assert numbers(0) == []


def test_large_sequence() -> None:
    result = numbers(5)
    assert len(result) == 5
    assert result[-1] == 4
