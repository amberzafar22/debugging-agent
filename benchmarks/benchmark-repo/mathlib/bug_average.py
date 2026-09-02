def average(numbers):
    """BUG (easy): divides by len(numbers) - 1 instead of len(numbers)."""
    total = sum(numbers)
    return total / (len(numbers) - 1)
