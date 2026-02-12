from backend.core.utils import get_bike_categories


def test_get_simple_types_empty():
    assert get_bike_categories([]) == ["other"]
    assert get_bike_categories(None) == ["other"]


def test_get_simple_types_gravel():
    assert get_bike_categories(["Gravel"]) == ["gravel"]
    assert get_bike_categories(["Rowery Gravelowe"]) == ["gravel"]


def test_get_simple_types_mtb():
    assert get_bike_categories(["MTB"]) == ["mtb"]
    assert get_bike_categories(["Górskie"]) == ["mtb"]


def test_get_simple_types_multiple():
    # Sorts and removes duplicates
    categories = ["MTB", "Górskie", "Szosowe", "Road"]
    assert get_bike_categories(categories) == ["mtb", "road"]


def test_get_simple_types_other():
    assert get_bike_categories(["Some weird category"]) == ["other"]


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
    assert get_bike_categories(categories) == expected
