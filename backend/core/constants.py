import re
from enum import StrEnum

FRAMESET_GEOMETRY_INDEX = "frameset_geometry"
BIKE_PRODUCT_INDEX = "bike_products"


class BikeCategory(StrEnum):
    ROAD = "road"
    MOUNTAIN = "mountain"
    GRAVEL = "gravel"
    TOURING = "touring"
    HYBRID = "hybrid"
    CITY = "city"
    KIDS = "kids"
    OTHER = "other"


class MaterialGroup(StrEnum):
    CARBON = "carbon"
    ALUMINUM = "aluminum"
    STEEL = "steel"
    TITANIUM = "titanium"
    OTHER = "other"


CATEGORY_PATTERNS = {
    BikeCategory.ROAD: re.compile(r"road|triathlon", re.IGNORECASE),
    BikeCategory.MOUNTAIN: re.compile(r"mountain|trail|downhill", re.IGNORECASE),
    BikeCategory.GRAVEL: re.compile(r"gravel|cross country", re.IGNORECASE),
    BikeCategory.TOURING: re.compile(r"touring|trekking", re.IGNORECASE),
    BikeCategory.HYBRID: re.compile(r"hybrid|fitness|active|verve|city", re.IGNORECASE),
    BikeCategory.KIDS: re.compile(r"kids", re.IGNORECASE),
}

MATERIAL_PATTERNS = {
    MaterialGroup.CARBON: re.compile(r"carbon|węgiel|węglow", re.IGNORECASE),
    MaterialGroup.ALUMINUM: re.compile(r"aluminum|aluminium|aluninium|alu", re.IGNORECASE),
    MaterialGroup.STEEL: re.compile(r"steel|stal|crmo|chromoly", re.IGNORECASE),
    MaterialGroup.TITANIUM: re.compile(r"titanium|tytan", re.IGNORECASE),
}
