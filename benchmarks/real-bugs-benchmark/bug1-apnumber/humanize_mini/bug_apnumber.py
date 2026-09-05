"""
Real bug, sourced from the humanize library (github.com/python-humanize/humanize).
Commit before fix: 2f179b6b5c1e2eb88240e3ec42ff9edeb946ea65^
Fix commit: 2f179b6b5c1e2eb88240e3ec42ff9edeb946ea65
Original fix commit message: "Fix: AP style for 0 is 'zero'"

This is the REAL buggy apnumber() function, logic unchanged from the
actual historical commit. Only the internal i18n/gettext translation
wrapper has been stripped out (replaced with a plain identity function)
since it's unrelated infrastructure, not part of the bug itself.
"""


def _(text):
    """Stand-in for the library's real gettext wrapper — not part of the bug."""
    return text


def apnumber(value):
    """For numbers 1-9, returns the number spelled out. Otherwise, returns the
    number. This follows Associated Press style. This always returns a string
    unless the value was not int-able, unlike the Django filter."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    if not 0 < value < 10:
        return str(value)
    return (
        _("one"),
        _("two"),
        _("three"),
        _("four"),
        _("five"),
        _("six"),
        _("seven"),
        _("eight"),
        _("nine"),
    )[value - 1]
