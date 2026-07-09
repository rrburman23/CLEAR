from target import sort_numbers

try:
    assert sort_numbers([3, 1, 2]) == [1, 2, 3]
    assert sort_numbers([5, 4, 6]) == [4, 5, 6]
    print("SUCCESS")
except AssertionError:
    exit(1)
