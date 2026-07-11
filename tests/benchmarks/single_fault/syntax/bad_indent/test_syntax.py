import pytest

from target import even


def test_even_number() -> None:
    assert even(2) is True


def test_odd_number() -> None:
    assert even(3) is False


def test_zero_case() -> None:
    assert even(0) is True
