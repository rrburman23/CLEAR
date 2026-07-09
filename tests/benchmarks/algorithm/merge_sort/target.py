def merge_sort(arr: list[int]) -> list[int]:
    """
    Sorts an array of integers in ascending order using divide and conquer.

    BUG: Failing to append the remainder of the lists after the main while loop.
    If one half is exhausted before the other, the remaining elements are lost.
    """
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])

    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        if left[i] < right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    # BUG: Missing code here.
    # The agent must append left[i:] and right[j:] to the result array.

    return result
