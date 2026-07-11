import pytest
from target import Temperature, convert


def test_conversion_value() -> None:
    t = Temperature(0)
    assert convert(t) == pytest.approx(32.0)


def test_celsius_to_fahrenheit_logic() -> None:
    t = Temperature(100)
    assert convert(t) == pytest.approx(212.0)


def test_property_access() -> None:
    t = Temperature(25)
    assert t.fahrenheit == pytest.approx(77.0)
