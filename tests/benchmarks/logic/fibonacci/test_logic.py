from target import fibonacci

try:
    assert fibonacci(2) == 1
    assert fibonacci(6) == 8
    assert fibonacci(10) == 55
    print("SUCCESS")
except AssertionError as e:
    print(e)
    exit(1)
