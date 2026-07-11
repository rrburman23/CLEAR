import pytest
from target import celsius_to_fahrenheit


def test_freezing() -> None:
    assert celsius_to_fahrenheit(0) == pytest.approx(32.0)


def test_boiling() -> None:
    assert celsius_to_fahrenheit(100) == pytest.approx(212.0)


def test_negative_temp() -> None:
    assert celsius_to_fahrenheit(-40) == pytest.approx(-40.0)
