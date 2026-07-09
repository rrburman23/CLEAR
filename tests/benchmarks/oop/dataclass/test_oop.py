from target import create_user, User


def test_user_creation():
    user = create_user("Alice", 25)

    assert isinstance(user, User)
    assert user.name == "Alice"
    assert user.age == 25


def test_default_active():
    user = create_user("Bob", 30)

    assert user.active is True
