from target import celsius_to_fahrenheit

try:
    assert celsius_to_fahrenheit(0) == 32
    assert celsius_to_fahrenheit(100) == 212
    print("SUCCESS")
except AssertionError:
    exit(1)
