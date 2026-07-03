try:
    assert filter_even_numbers([1, 2, 3, 4, 5]) == [2, 4], "Failed to filter basic list"
    assert filter_even_numbers([1, 3, 5]) == [], "Failed to handle list with no evens"
    assert filter_even_numbers([2, 4, 6]) == [2, 4, 6], "Failed to handle all-even list"
    print("SUCCESS: All syntax tests passed.")
except AssertionError as e:
    print(f"TEST FAILED: {e}")
    exit(1)
except Exception as e:
    print(f"RUNTIME ERROR: {e}")
    exit(1)
