def factorial(n):
    """BUG (medium): loop range excludes n itself, off-by-one in range()."""
    result = 1
    for i in range(1, n):
        result *= i
    return result
