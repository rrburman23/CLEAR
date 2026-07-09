# This test suite deliberately creates a circular reference and expects the function to handle it gracefully (e.g., by skipping it or replacing it with "<circular>") rather than crashing Python.

from typing import Any
from target import flatten_dict

try:
    # Test 1: Standard flattening (should pass)
    normal = {"a": 1, "b": {"c": 2}}
    assert flatten_dict(normal) == {"a": 1, "b_c": 2}

    # Test 2: Circular reference (will cause RecursionError in broken code)
    circular: dict[str, Any] = {"x": 10}
    circular["y"] = circular  # The dictionary references itself

    # The repaired code should catch the circular reference and return something safe
    # e.g., {'x': 10, 'y': '<circular>'} or just skip it.
    # We will accept skipping it for this test:
    result = flatten_dict(circular)

    # If it survived without a RecursionError, check if it flattened 'x'
    assert result.get("x") == 10
    assert "y" in result  # It should acknowledge 'y' exists

    print("SUCCESS")
except RecursionError:
    print("FAILURE: RecursionError caught - circular reference not handled.")
    exit(1)
except AssertionError:
    print("FAILURE: Output did not match expected structure.")
    exit(1)
