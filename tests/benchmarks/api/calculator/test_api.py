from target import calculate

try:
    assert calculate("2+3") == 5
    assert calculate("10/2") == 5
    assert calculate("abc") is None
    print("SUCCESS")
except AssertionError:
    exit(1)
except Exception:
    print("TEST FAILED: Invalid expression caused crash.")
    exit(1)
