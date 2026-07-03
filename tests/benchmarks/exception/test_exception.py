try:
    assert safe_divide(10, 2) == 5.0, "Math Error: 10 / 2 should be 5.0"
    assert safe_divide(10, 0) is None, (
        "Robustness Error: Division by zero must return None"
    )
    print("SUCCESS: All exception tests passed.")
except AssertionError as e:
    print(f"TEST FAILED: {e}")
    exit(1)
except ZeroDivisionError:
    print("TEST FAILED: Unhandled ZeroDivisionError. Code crashed.")
    exit(1)
