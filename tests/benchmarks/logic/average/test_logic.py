from target import average

try:
    assert average([1, 2, 3]) == 2
    assert average([1, 2]) == 1.5
    print("SUCCESS")
except AssertionError:
    exit(1)
