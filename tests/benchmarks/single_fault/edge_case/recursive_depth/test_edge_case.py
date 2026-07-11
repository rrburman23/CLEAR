import pytest
from target import flatten_dict


def test_flat_dict() -> None:
    assert flatten_dict({"a": 1}) == {"a": 1}


def test_nested_dict() -> None:
    assert flatten_dict({"a": {"b": 2}}) == {"a_b": 2}


def test_circular_reference() -> None:
    d = {"a": 1}
    d["b"] = d # type: ignore
    # RecursionError should be handled/avoided
    with pytest.raises(RecursionError):
        flatten_dict(d)
