from backend.api.schemas import BikeCategory, MaterialGroup
from backend.core.constants import CATEGORY_PATTERNS, MATERIAL_PATTERNS


def get_simple_types(categories: list[str]) -> list[str]:
    if not categories:
        return [BikeCategory.OTHER.value]

    results = set()
    for category_str in categories:
        for cat_enum, pattern in CATEGORY_PATTERNS.items():
            if pattern.search(category_str):
                results.add(cat_enum.value)

    if not results:
        results.add(BikeCategory.OTHER.value)

    return sorted(list(results))


def get_material_group(material: str | None) -> str:
    if not material:
        return MaterialGroup.OTHER.value

    for mat_enum, pattern in MATERIAL_PATTERNS.items():
        if pattern.search(material):
            return mat_enum.value

    return MaterialGroup.OTHER.value
