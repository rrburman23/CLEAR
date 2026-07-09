from target import maximum

try:
    assert maximum([1, 4, 2]) == 4
    assert maximum([-5, -2, -8]) == -2
    print("SUCCESS")
except AssertionError:
    exit(1)
