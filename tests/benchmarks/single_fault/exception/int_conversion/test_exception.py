import pytest
from target import parse_number


def test_valid_integer() -> None:
    assert parse_number("123") == 123


def test_invalid_string() -> None:
    with pytest.raises(ValueError):
        parse_number("abc")


def test_float_string() -> None:
    # int("12.3") raises ValueError
    with pytest.raises(ValueError):
        parse_number("12.3")
