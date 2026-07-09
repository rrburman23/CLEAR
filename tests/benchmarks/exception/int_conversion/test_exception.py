from target import parse_number

try:
    assert parse_number("10") == 10
    assert parse_number("abc") is None
    print("SUCCESS")
except ValueError:
    exit(1)
