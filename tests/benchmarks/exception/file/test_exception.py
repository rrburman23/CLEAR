from target import read_first_line

try:
    assert read_first_line("does_not_exist.txt") is None
    print("SUCCESS")
except FileNotFoundError:
    print("FAILED")
    exit(1)
