import pytest

from target import parse_csv


def test_normal_case() -> None:
    assert parse_csv("apple,banana,cherry") == ["apple", "banana", "cherry"]


def test_boundary_empty_string() -> None:
    assert parse_csv("") == [""]


def test_special_whitespace_handling() -> None:
    assert parse_csv("one, two, three") == ["one", " two", " three"]


def test_single_element() -> None:
    assert parse_csv("solitary") == ["solitary"]
