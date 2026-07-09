from target import is_prime

try:
    assert is_prime(2)
    assert is_prime(11)
    assert not is_prime(9)
    assert not is_prime(1)
    print("SUCCESS")
except AssertionError:
    exit(1)
