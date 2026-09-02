def find_max(numbers):
    """BUG (medium): starts comparison at index 1, so index 0 is
    never actually considered as a candidate for the max — wrong if
    numbers[0] is the true maximum."""
    max_val = numbers[1]
    for n in numbers[1:]:
        if n > max_val:
            max_val = n
    return max_val
