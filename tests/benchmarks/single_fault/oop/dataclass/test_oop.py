import pytest
from target import create_user, User


def test_user_creation() -> None:
    user = create_user("Alice", 30)
    assert user.name == "Alice"
    assert user.age == 30


def test_default_active_status() -> None:
    user = create_user("Bob", 25)
    assert user.active is True


def test_attribute_types() -> None:
    user = create_user("Charlie", 40)
    assert isinstance(user, User)
