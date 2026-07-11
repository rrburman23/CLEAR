import pytest
from target import Car


def test_car_drive() -> None:
    c = Car()
    assert c.drive() is True


def test_engine_init() -> None:
    c = Car()
    assert hasattr(c, "engine")


def test_car_type() -> None:
    c = Car()
    assert isinstance(c.drive(), bool)
