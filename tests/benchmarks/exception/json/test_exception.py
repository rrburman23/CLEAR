from target import parse_json

try:
    assert parse_json('{"a":1}') == {"a": 1}
    assert parse_json("invalid") is None
    print("SUCCESS: All exception tests passed.")
except AssertionError as e:
    print(f"TEST FAILED: {e}")
    exit(1)
except Exception:
    print("TEST FAILED: JSONDecodeError not handled.")
    exit(1)
