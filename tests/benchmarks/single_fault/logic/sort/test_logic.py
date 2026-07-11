import pytest

from target import sort_numbers


def test_normal_case() -> None:
    assert sort_numbers([3, 1, 2]) == [1, 2, 3]


def test_empty_list() -> None:
    assert sort_numbers([]) == []


def test_already_sorted() -> None:
    assert sort_numbers([1, 2, 3]) == [1, 2, 3]
    