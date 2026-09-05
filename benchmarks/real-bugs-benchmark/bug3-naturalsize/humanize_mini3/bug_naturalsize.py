"""
Real bug, sourced from the humanize library (github.com/python-humanize/humanize).
Commit before fix: db9678288054dba85f5ce8959c20cc2436f7a1fa^
Fix commit: db9678288054dba85f5ce8959c20cc2436f7a1fa
Original fix commit message: "Show more than bytes for negative file sizes"

This is the REAL buggy naturalsize() function, logic unchanged from
the actual historical commit. No i18n dependency — this one is pure
arithmetic logic, fully self-contained.

The bug: naturalsize() compares the raw signed value against unit
thresholds (e.g. `bytes < base`), instead of the absolute value. For
a negative byte count like -1500000, this means it never reaches the
larger units (KB, MB, ...) and falls through incorrectly, since a
negative number is always "less than" a positive threshold.
"""

suffixes = {
    "decimal": ("kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"),
    "binary": ("KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"),
    "gnu": "KMGTPEZY",
}


def naturalsize(value, binary=False, gnu=False, format="%.1f"):
    """Format a number of bytes like a human readable filesize (eg. 10 kB). By
    default, decimal suffixes (kB, MB) are used. Passing binary=true will use
    binary suffixes (KiB, MiB) are used and the base will be 2**10 instead of
    10**3. If ``gnu`` is True, the binary argument is ignored and GNU-style
    (ls -sh style) prefixes are used (K, M) with the 2**10 definition."""
    if gnu:
        suffix = suffixes["gnu"]
    elif binary:
        suffix = suffixes["binary"]
    else:
        suffix = suffixes["decimal"]

    base = 1024 if (gnu or binary) else 1000
    bytes = float(value)

    if bytes == 1 and not gnu:
        return "1 Byte"
    elif bytes < base and not gnu:
        return "%d Bytes" % bytes
    elif bytes < base and gnu:
        return "%dB" % bytes

    for i, s in enumerate(suffix):
        unit = base ** (i + 2)
        if bytes < unit and not gnu:
            return (format + " %s") % ((base * bytes / unit), s)
        elif bytes < unit and gnu:
            return (format + "%s") % ((base * bytes / unit), s)
    if gnu:
        return (format + "%s") % ((base * bytes / unit), s)
    return (format + " %s") % ((base * bytes / unit), s)
