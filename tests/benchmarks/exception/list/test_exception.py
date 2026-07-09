from target import first_item

try:
    assert first_item([1]) == 1
    assert first_item([]) is None
    print("SUCCESS")
except IndexError:
    exit(1)
