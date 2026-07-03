try:
    assert calculate_factorial(5) == 120, "Logic Error: 5! should be 120"
    assert calculate_factorial(0) == 1, "Logic Error: 0! should be 1"
    assert calculate_factorial(3) == 6, "Logic Error: 3! should be 6"
    print("SUCCESS: All logic tests passed.")
except AssertionError as e:
    print(f"TEST FAILED: {e}")
    exit(1)
