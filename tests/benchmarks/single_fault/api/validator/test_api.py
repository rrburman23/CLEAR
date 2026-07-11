import pytest
from target import validate_email


def test_valid_email() -> None:
    assert validate_email("user@example.com") is True


def test_valid_subdomain_email() -> None:
    assert validate_email("user@mail.example.com") is True


def test_missing_at_symbol() -> None:
    assert validate_email("userexample.com") is False


def test_missing_domain_dot() -> None:
    assert validate_email("user@examplecom") is False


def test_missing_local_part() -> None:
    assert validate_email("@example.com") is False


def test_missing_domain_name() -> None:
    assert validate_email("user@.com") is False


def test_multiple_at_symbols() -> None:
    assert validate_email("user@@example.com") is False


def test_empty_string() -> None:
    assert validate_email("") is False


def test_only_symbols() -> None:
    assert validate_email("@.") is False


def test_whitespace_is_invalid() -> None:
    assert validate_email("user @example.com") is False
    assert validate_email("user@example .com") is False
