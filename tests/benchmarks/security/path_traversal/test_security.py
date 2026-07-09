from target import get_user_file

try:
    # Attempting to escape the data directory
    content = get_user_file("../app/target.py")
    assert "/data/" in content or "safe" in content, (
        "Security Alert: Path traversal possible"
    )
    print("SUCCESS")
except Exception:
    print("FAILED")
    exit(1)
