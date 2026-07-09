from target import merge_sort
import sys

try:
    # A perfectly balanced array might accidentally pass the buggy code
    # We must test an unbalanced array where remainders are left over.
    unsorted_arr = [38, 27, 43, 3, 9, 82, 10]
    expected_arr = [3, 9, 10, 27, 38, 43, 82]

    result = merge_sort(unsorted_arr)

    assert result == expected_arr, (
        f"Expected {expected_arr}, but got {result}. Elements were likely dropped during the merge phase."
    )
    print("SUCCESS")
except AssertionError as e:
    print(f"FAILURE\n{e}")
    sys.exit(1)
