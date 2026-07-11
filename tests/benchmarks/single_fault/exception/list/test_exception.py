import pytest
from target import first_item


def test_normal_list() -> None:
    assert first_item([1, 2, 3]) == 1


def test_empty_list() -> None:
    # Based on docstring, should return None
    assert first_item([]) is None


def test_single_item_list() -> None:
    assert first_item(["only"]) == "only"
