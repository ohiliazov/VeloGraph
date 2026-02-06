from backend.api.schemas import BikeCategory, MaterialGroup
from backend.core.constants import CATEGORY_PATTERNS, MATERIAL_PATTERNS
from backend.core.models import BikeProductORM


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


def group_bike_product(product: BikeProductORM, siblings: list[BikeProductORM]) -> dict:
    return {
        "frameset_name": product.frameset.name,
        "material": product.frameset.material,
        "material_group": get_material_group(product.frameset.material),
        "category": product.frameset.category,
        "build_kit": {
            "name": product.build_kit.name,
            "groupset": product.build_kit.groupset,
            "wheelset": product.build_kit.wheelset,
            "cockpit": product.build_kit.cockpit,
            "tires": product.build_kit.tires,
        },
        "skus": [p.sku for p in siblings],
        "product_ids": [p.id for p in siblings],
        "sizes": [p.frameset.size_label for p in siblings],
    }
