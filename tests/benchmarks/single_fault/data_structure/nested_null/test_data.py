import pytest
from target import get_user_country


def test_valid_country() -> None:
    data = {"user": {"address": {"country": "UK"}}}
    assert get_user_country(data) == "UK"


def test_missing_address_key() -> None:
    data = {"user": {}}
    with pytest.raises(KeyError):
        get_user_country(data)


def test_none_input() -> None:
    with pytest.raises(TypeError):
        get_user_country(None) #type: ignore
