from target import first_character


def test_normal():
    assert first_character("hello") == "h"


def test_single():
    assert first_character("A") == "A"


def test_empty():
    assert first_character("") == ""
