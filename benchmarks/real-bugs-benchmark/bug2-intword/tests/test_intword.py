from humanize_mini2.bug_intword import intword


def test_intword_rounds_up_to_next_unit():
    # This is the exact case from the real historical fix commit:
    # 999,999,999 rounds to "1000.0" million at 1-decimal precision,
    # but should roll over and display as "1.0 billion" instead.
    assert intword(999999999) == "1.0 billion"


def test_intword_normal_case_still_works():
    # Sanity check the common, non-edge-case path isn't broken.
    assert intword(1200000) == "1.2 million"
