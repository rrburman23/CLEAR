import pytest

from target import binary_search


def test_normal_case() -> None:
    arr = [1, 3, 5, 7, 9, 11, 13]
    assert binary_search(arr, 7) == 3
    assert binary_search(arr, 1) == 0


def test_boundary_case() -> None:
    arr = [2, 4]
    assert binary_search(arr, 2) == 0
    assert binary_search(arr, 4) == 1


def test_special_not_found() -> None:
    arr = [10, 20, 30, 40, 50]
    # The buggy implementation will infinite loop here.
    # PyTest will be terminated by the benchmark runner's timeout,
    # registering a legitimate failure.
    assert binary_search(arr, 25) == -1
    assert binary_search(arr, 5) == -1
    assert binary_search(arr, 60) == -1
