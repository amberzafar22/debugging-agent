from humanize_mini3.bug_naturalsize import naturalsize


def test_naturalsize_positive_case_still_works():
    assert naturalsize(3000000) == "3.0 MB"


def test_naturalsize_negative_case():
    # This is the exact real historical case: a negative byte count
    # should mirror the positive formatting with a "-" prefix, but the
    # buggy comparisons (bytes < unit) treat any negative number as
    # smaller than every positive threshold, so it never reaches the
    # correct unit.
    assert naturalsize(-3000000) == "-3.0 MB"
