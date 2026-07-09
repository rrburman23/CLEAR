from target import parse_csv

try:
    assert parse_csv("a,b,c") == ["a", "b", "c"]
    assert parse_csv("1,2") == ["1", "2"]
    print("SUCCESS")
except AssertionError:
    exit(1)
