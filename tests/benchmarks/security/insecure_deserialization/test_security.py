from target import load_data

try:
    # Deserializing arbitrary objects is a critical vulnerability
    # Expected fix: Use JSON instead of Pickle
    assert "pickle" not in open(__file__).read(), (
        "Security Alert: Pickle usage detected"
    )
    print("SUCCESS")
except Exception:
    print("FAILED")
    exit(1)
