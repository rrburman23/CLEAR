import pytest
from target import get_user_data


def test_normal_user() -> None:
    assert get_user_data("guest") == ["hello"]


def test_admin_user() -> None:
    assert get_user_data("admin") == ["super_secret"]


def test_sql_injection_attempt() -> None:
    results = get_user_data("' OR '1'='1")

    assert results == []
    assert "super_secret" not in results
    assert "hello" not in results
