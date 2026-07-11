import pytest
from target import remove_even_numbers


def test_removes_evens() -> None:
    assert remove_even_numbers([1, 2, 3, 4]) == [1, 3]


def test_removes_all() -> None:
    assert remove_even_numbers([2, 4, 6]) == []


def test_keeps_odds() -> None:
    assert remove_even_numbers([1, 3, 5]) == [1, 3, 5]
