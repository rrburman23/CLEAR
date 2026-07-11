import pytest

from target import is_prime


def test_prime_number() -> None:
    assert is_prime(7) is True


def test_composite_number() -> None:
    assert is_prime(4) is False


def test_boundary_cases() -> None:
    assert is_prime(0) is False
    assert is_prime(1) is False
