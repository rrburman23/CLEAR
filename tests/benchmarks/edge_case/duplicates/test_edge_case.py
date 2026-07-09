from target import remove_duplicates


def test_preserves_order():
    assert remove_duplicates([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_empty():
    assert remove_duplicates([]) == []


def test_single():
    assert remove_duplicates([5]) == [5]
