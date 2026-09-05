"""
Real bug, sourced from the humanize library (github.com/python-humanize/humanize).
Commit before fix: 818c9b3f1654a8f488c0c6fb828b45fdca0fade6^
Fix commit: 818c9b3f1654a8f488c0c6fb828b45fdca0fade6
Original fix commit message:
"fixed intword returning 1000.0 million instead of 1.0 billion"

This is the REAL buggy intword() function, logic unchanged from the
actual historical commit. Only the i18n/gettext translation wrapper
has been stripped out (replaced with identity functions) since it's
unrelated infrastructure, not part of the bug itself.

This bug is HARDER than a simple off-by-one: it's a rounding edge
case. When a number rounds UP to exactly the next power of 1000
(e.g. 999,999,999 rounds to "1000.0" million), the function should
roll over to the next unit ("1.0 billion") instead of displaying an
out-of-range value like "1000.0 million".
"""


def _(text):
    """Stand-in for the library's real gettext wrapper — not part of the bug."""
    return text


powers = [10 ** x for x in (6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 100)]
human_powers = (
    "million",
    "billion",
    "trillion",
    "quadrillion",
    "quintillion",
    "sextillion",
    "septillion",
    "octillion",
    "nonillion",
    "decillion",
    "googol",
)


def intword(value, format="%.1f"):
    """Converts a large integer to a friendly text representation. Works best for
    numbers over 1 million. For example, 1000000 becomes '1.0 million', 1200000
    becomes '1.2 million' and '1200000000' becomes '1.2 billion'. Supports up to
    decillion (33 digits) and googol (100 digits). You can pass format to change
    the number of decimal or general format of the number portion. This function
    returns a string unless the value passed was unable to be coaxed into an int."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value

    if value < powers[0]:
        return str(value)
    for ordinal, power in enumerate(powers[1:], 1):
        if value < power:
            chopped = value / float(powers[ordinal - 1])
            return (" ".join([format, _(human_powers[ordinal - 1])])) % chopped
    return str(value)
