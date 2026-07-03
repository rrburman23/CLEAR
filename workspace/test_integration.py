try:
    # 1. Test Math Ops
    assert calculate_power(2, 3) == 8, "Logic Error: 2^3 should be 8"
    assert calculate_power(5, 2) == 25, "Logic Error: 5^2 should be 25"
    assert calculate_power(10, 0) == 1, "Logic Error: 10^0 should be 1"

    # If no assertions throw an error, the code is logically sound.
    print("SUCCESS: All tests passed.")

except AssertionError as e:
    # If an assertion fails, print the specific error so the AI can read it.
    print(f"TEST FAILED: {e}")
    exit(1)
except Exception as e:
    print(f"RUNTIME ERROR: {e}")
    exit(1)
