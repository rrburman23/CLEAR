import pytest
from target import get_age


def test_normal_case() -> None:
    assert get_age({"age": 25}) == 25


def test_missing_key() -> None:
    with pytest.raises(KeyError):
        get_age({"name": "Rohan"})


def test_boundary_case() -> None:
    assert get_age({"age": 0}) == 0
