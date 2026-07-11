import pytest
from target import parse_json


def test_valid_json() -> None:
    assert parse_json('{"key": "value"}') == {"key": "value"}


def test_invalid_json() -> None:
    # Based on docstring, should return None
    assert parse_json("invalid") is None


def test_empty_json() -> None:
    assert parse_json("{}") == {}
