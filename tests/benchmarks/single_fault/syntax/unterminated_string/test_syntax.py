import pytest
from target import greet


def test_greet_name() -> None:
    assert greet("Alice") == "Hello, Alice"


def test_greet_empty() -> None:
    assert greet("") == "Hello, "


def test_greet_special_chars() -> None:
    assert greet("!@#") == "Hello, !@#"
