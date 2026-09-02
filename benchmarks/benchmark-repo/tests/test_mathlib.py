from mathlib.bug_average import average
from mathlib.bug_is_even import is_even
from mathlib.bug_factorial import factorial
from mathlib.bug_find_max import find_max
from mathlib.bug_count_vowels import count_vowels


def test_average():
    assert average([2, 4, 6]) == 4


def test_is_even():
    assert is_even(4) is True
    assert is_even(3) is False


def test_factorial():
    assert factorial(5) == 120


def test_find_max():
    # numbers[0] IS the true max here — this catches BUG 4
    assert find_max([9, 2, 5, 1]) == 9


def test_count_vowels():
    # "Apple" has an uppercase vowel (A) — THIS is what actually
    # catches the case-sensitivity bug. "Hello World" did NOT catch
    # it, since it has no uppercase vowels at all.
    assert count_vowels("Apple") == 2
