def remove_even_numbers(nums: list):
    for n in nums:
        if n % 2 == 0:
            nums.remove(n)
    return nums
