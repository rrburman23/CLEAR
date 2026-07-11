import pytest
from target import first_character


def test_normal_string() -> None:
    assert first_character("hello") == "h"


def test_single_character() -> None:
    assert first_character("A") == "A"


def test_empty_string_returns_empty() -> None:
    # Target currently crashes on index [0]
    assert first_character("") == ""
