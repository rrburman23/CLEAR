from target import numbers


def test_generator():
    result = numbers(5)

    assert hasattr(result, "__iter__")
    assert list(result) == [0, 1, 2, 3, 4]


def test_lazy():
    assert not isinstance(numbers(5), list)
