def remove_even_numbers(nums: list):
    # BUG: Modifying list while iterating over it causes skip errors
    for n in nums:
        if n % 2 == 0:
            nums.remove(n)
    return nums
