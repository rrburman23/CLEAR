from target import validate_email

try:
    assert validate_email("user@example.com")
    assert not validate_email("invalidemail")
    assert not validate_email("user@example")
    print("SUCCESS")
except AssertionError:
    exit(1)
