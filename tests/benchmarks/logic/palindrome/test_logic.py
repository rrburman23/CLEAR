from target import is_palindrome

try:
    assert is_palindrome("racecar")
    assert is_palindrome("madam")
    assert not is_palindrome("hello")
    print("SUCCESS")
except AssertionError:
    exit(1)
