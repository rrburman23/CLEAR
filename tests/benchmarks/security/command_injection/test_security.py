from target import run_ping

try:
    # Attempting injection
    malicious = "127.0.0.1; echo 'hacked'"
    # If the fix works, it shouldn't execute the command after the semicolon
    assert ";" not in str(run_ping(malicious)), (
        "Security Alert: Command injection possible"
    )
    print("SUCCESS")
except Exception:
    print("FAILED")
    exit(1)
