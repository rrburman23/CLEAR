from target import factorial

try:
    assert factorial(0) == 1
    assert factorial(5) == 120
    assert factorial(7) == 5040
    print("SUCCESS")
except AssertionError as e:
    print(e)
    exit(1)
