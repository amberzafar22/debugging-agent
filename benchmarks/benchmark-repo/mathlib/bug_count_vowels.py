def count_vowels(text):
    """BUG (harder): only checks lowercase vowels, so uppercase
    vowels in the input are silently missed."""
    vowels = "aeiou"
    return sum(1 for ch in text if ch in vowels)
