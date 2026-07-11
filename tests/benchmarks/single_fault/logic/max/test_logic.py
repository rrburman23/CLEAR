import pytest
from target import maximum


def test_normal_case() -> None:
    assert maximum([1, 5, 3]) == 5


def test_negative_numbers() -> None:
    assert maximum([-10, -5, -20]) == -5


def test_single_element() -> None:
    assert maximum([42]) == 42
