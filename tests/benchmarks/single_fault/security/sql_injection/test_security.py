import pytest
from target import get_user_data


def test_normal_user() -> None:
    assert get_user_data("guest") == ["hello"]


def test_admin_user() -> None:
    assert get_user_data("admin") == ["super_secret"]


def test_sql_injection_attempt() -> None:
    # Malicious username should not return all secrets
    results = get_user_data("' OR '1'='1")
    assert len(results) == 1  # Should only return 1, not both secrets
    assert "super_secret" not in results
