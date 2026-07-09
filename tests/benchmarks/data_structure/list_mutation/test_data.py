from target import remove_even_numbers

try:
    assert remove_even_numbers([1, 2, 3, 4]) == [1, 3]
    print("SUCCESS")
except Exception:
    print("FAILED")
    exit(1)
