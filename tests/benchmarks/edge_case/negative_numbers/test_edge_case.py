from target import absolute_difference


def test_positive():
    assert absolute_difference(10, 3) == 7


def test_negative():
    assert absolute_difference(-5, -2) == 3


def test_mixed():
    assert absolute_difference(-5, 4) == 9


def test_reverse():
    assert absolute_difference(3, 10) == 7
