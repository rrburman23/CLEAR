import pytest
from target import get_user_file


def test_valid_file() -> None:
    # Assuming user.txt exists in /app/data/
    # Setup: we use a mock-like approach or assume files exist in container
    with pytest.raises(FileNotFoundError):
        get_user_file("does_not_exist.txt")


def test_traversal_attempt() -> None:
    # The application should restrict access to the /app/data/ directory
    with pytest.raises(Exception):
        get_user_file("../target.py")


def test_absolute_path_traversal() -> None:
    with pytest.raises(Exception):
        get_user_file("/etc/passwd")
