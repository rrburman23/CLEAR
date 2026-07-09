from target import get_age

try:
    assert get_age({"age": 20}) == 20
    assert get_age({}) is None
    print("SUCCESS")
except KeyError:
    exit(1)
