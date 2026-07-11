import pytest
from target import remove_duplicates


def test_no_duplicates_preserves_order() -> None:
    assert remove_duplicates([1, 2, 3]) == [1, 2, 3]


def test_duplicates_removed_preserves_order() -> None:
    # Target was previously returning sorted(unique), which is wrong
    assert remove_duplicates([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_empty_list() -> None:
    assert remove_duplicates([]) == []
