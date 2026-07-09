from target import get_length

try:
    assert get_length("hello") == 5
    assert get_length(None) == 0, "Should handle None gracefully"
    print("SUCCESS")
except Exception:
    print("FAILED")
    exit(1)
