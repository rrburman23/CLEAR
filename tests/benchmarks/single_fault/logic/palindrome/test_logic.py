import pytest

from target import is_palindrome


def test_normal_palindrome() -> None:
    assert is_palindrome("radar") is True


def test_not_palindrome() -> None:
    assert is_palindrome("hello") is False


def test_empty_string() -> None:
    assert is_palindrome("") is True
