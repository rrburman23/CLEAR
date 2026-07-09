from target import average


def test_average():
    assert average([2, 4, 6]) == 4


def test_empty():
    assert average([]) == 0


def test_single():
    assert average([5]) == 5
