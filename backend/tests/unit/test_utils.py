from backend.core.utils import get_simple_types


def test_get_simple_types_empty():
    assert get_simple_types([]) == ["other"]
    assert get_simple_types(None) == ["other"]


def test_get_simple_types_gravel():
    assert get_simple_types(["Gravel"]) == ["gravel"]
    assert get_simple_types(["Rowery Gravelowe"]) == ["gravel"]


def test_get_simple_types_mtb():
    assert get_simple_types(["MTB"]) == ["mtb"]
    assert get_simple_types(["Górskie"]) == ["mtb"]


def test_get_simple_types_multiple():
    # Sorts and removes duplicates
    categories = ["MTB", "Górskie", "Szosowe", "Road"]
    assert get_simple_types(categories) == ["mtb", "road"]


def test_get_simple_types_other():
    assert get_simple_types(["Some weird category"]) == ["other"]


def test_get_simple_types_all_known():
    categories = [
        "gravel",
        "mtb",
        "górsk",
        "trekking",
        "cross",
        "szos",
        "road",
        "miejsk",
        "city",
        "dzieci",
        "kids",
        "junior",
        "turyst",
        "damsk",
        "women",
    ]
    expected = sorted(["gravel", "mtb", "trekking", "cross", "road", "city", "kids", "touring", "women"])
    assert get_simple_types(categories) == expected
