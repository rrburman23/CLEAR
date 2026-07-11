import pytest

from target import validate_email


def test_normal_valid_email() -> None:
    
    assert validate_email("user@example.com") is True


def test_boundary_missing_parts() -> None:
    assert validate_email("userexample.com") is False
    assert validate_email("user@examplecom") is False


def test_special_empty_string() -> None:
    assert validate_email("") is False


def test_special_only_symbols() -> None:
    assert validate_email("@.") is False
