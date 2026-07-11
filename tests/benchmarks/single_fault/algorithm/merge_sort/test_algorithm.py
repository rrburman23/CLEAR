import pytest

from target import merge_sort


def test_normal_case() -> None:
    arr = [38, 27, 43, 3, 9, 82, 10]
    expected = [3, 9, 10, 27, 38, 43, 82]
    assert merge_sort(arr) == expected


def test_boundary_case() -> None:
    assert merge_sort([]) == []
    assert merge_sort([5]) == [5]


def test_special_case_duplicates() -> None:
    # The buggy implementation loses elements when one list exhausts first
    arr = [5, 1, 5, 1, 2, 9, 2]
    expected = [1, 1, 2, 2, 5, 5, 9]
    assert merge_sort(arr) == expected


def test_already_sorted() -> None:
    arr = [1, 2, 3, 4, 5]
    assert merge_sort(arr) == [1, 2, 3, 4, 5]
