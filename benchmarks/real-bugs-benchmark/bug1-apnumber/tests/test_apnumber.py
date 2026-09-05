from humanize_mini.bug_apnumber import apnumber


def test_apnumber_zero():
    # This is the exact case the real historical fix commit added:
    # apnumber(0) should return "zero", per AP style, but the buggy
    # range check `0 < value < 10` excludes 0 entirely.
    assert apnumber(0) == "zero"


def test_apnumber_one_to_nine_still_work():
    # Sanity check that the working cases aren't broken.
    assert apnumber(1) == "one"
    assert apnumber(9) == "nine"
