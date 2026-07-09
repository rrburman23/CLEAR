from target import get_item

try:
    assert get_item([1, 2, 3], 1) == 2
    assert get_item(["a"], 0) == "a"
    assert get_item([], 0) is None
    assert get_item([1], 5) is None
    print("SUCCESS: All exception tests passed.")
except AssertionError as e:
    print(f"TEST FAILED: {e}")
    exit(1)
except IndexError:
    print("TEST FAILED: Unhandled IndexError.")
    exit(1)
