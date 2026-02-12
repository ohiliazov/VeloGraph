from backend.core.constants import CATEGORY_PATTERNS, MATERIAL_PATTERNS, BikeCategory, MaterialGroup


def get_bike_categories(category_str: str) -> list[BikeCategory]:
    if not category_str:
        return [BikeCategory.OTHER]

    results = set()
    for cat_enum, pattern in CATEGORY_PATTERNS.items():
        if pattern.search(category_str):
            results.add(cat_enum)

    if not results:
        results.add(BikeCategory.OTHER)

    return sorted(list(results))


def get_material_group(material: str | None) -> MaterialGroup:
    if not material:
        return MaterialGroup.OTHER

    for mat_enum, pattern in MATERIAL_PATTERNS.items():
        if pattern.search(material):
            return mat_enum

    return MaterialGroup.OTHER
