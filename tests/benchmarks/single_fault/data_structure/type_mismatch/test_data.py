import pytest
from target import get_length


def test_string_length() -> None:
    """Test normal string input."""
    assert get_length("hello") == 5


def test_list_length() -> None:
    """Test normal list input."""
    assert get_length([1, 2, 3]) == 3


def test_none_case() -> None:
    """Boundary case: None should return 0."""
    assert get_length(None) == 0


def test_type_error_on_int() -> None:
    """Special case: Integers don't have length, should raise TypeError."""
    with pytest.raises(TypeError):
        get_length(123)
