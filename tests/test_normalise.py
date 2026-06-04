from meridian_inducements.normalise import to_canonical_adviser_id, to_concur_adviser_ref


def test_canonical_from_registry_form():
    assert to_canonical_adviser_id("ADV-001") == "ADV-001"
    assert to_canonical_adviser_id("ADV-025") == "ADV-025"


def test_canonical_from_concur_form():
    assert to_canonical_adviser_id("A-00001") == "ADV-001"
    assert to_canonical_adviser_id("A-00025") == "ADV-025"


def test_canonical_handles_whitespace_and_case():
    assert to_canonical_adviser_id(" adv-007 ") == "ADV-007"
    assert to_canonical_adviser_id("a-00007") == "ADV-007"


def test_canonical_invalid_inputs():
    assert to_canonical_adviser_id(None) is None
    assert to_canonical_adviser_id("") is None
    assert to_canonical_adviser_id("ADVISER-001") is None
    assert to_canonical_adviser_id("A-XXXX") is None
    assert to_canonical_adviser_id("ADV-000") is None


def test_round_trip():
    assert to_concur_adviser_ref("ADV-001") == "A-00001"
    assert to_concur_adviser_ref("ADV-025") == "A-00025"
