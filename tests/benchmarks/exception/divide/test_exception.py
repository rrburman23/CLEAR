import pytest

from target import divide


def test_normal_division():
    assert divide(10, 2) == 5


def test_float_division():
    assert divide(5, 2) == 2.5


def test_negative_division():
    assert divide(-10, 2) == -5


def test_zero_division_returns_none():
    assert divide(10, 0) is None


def test_zero_by_zero_returns_none():
    assert divide(0, 0) is None
