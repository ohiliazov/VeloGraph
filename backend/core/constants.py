import re

from backend.api.schemas import BikeCategory, MaterialGroup

FRAMESET_GEOMETRY_INDEX = "frameset_geometry"
BIKE_PRODUCT_INDEX = "bike_products"

CATEGORY_PATTERNS = {
    BikeCategory.GRAVEL: re.compile(r"gravel", re.IGNORECASE),
    BikeCategory.MTB: re.compile(r"mtb|górsk|fuel|supercaliber|session|caliber", re.IGNORECASE),
    BikeCategory.TREKKING: re.compile(r"trekking|mahon|suvea|zing|elan|nhoma", re.IGNORECASE),
    BikeCategory.CROSS: re.compile(r"cross|hybryd", re.IGNORECASE),
    BikeCategory.ROAD: re.compile(r"szos|road|domane|madone|emonda|checkpoint", re.IGNORECASE),
    BikeCategory.CITY: re.compile(
        r"miejsk|city|town|mieście|cruiser|loft|bali|shibori|ghostrider|zouma", re.IGNORECASE
    ),
    BikeCategory.KIDS: re.compile(r"dzieci|kids|junior|precaliber|kickster|wahoo", re.IGNORECASE),
    BikeCategory.TOURING: re.compile(r"touring|wypraw|turyst", re.IGNORECASE),
    BikeCategory.WOMEN: re.compile(r"damsk|women", re.IGNORECASE),
}

MATERIAL_PATTERNS = {
    MaterialGroup.CARBON: re.compile(r"carbon|węgiel|węglow", re.IGNORECASE),
    MaterialGroup.ALUMINUM: re.compile(r"aluminum|aluminium|aluninium|alu", re.IGNORECASE),
    MaterialGroup.STEEL: re.compile(r"steel|stal|crmo|chromoly", re.IGNORECASE),
    MaterialGroup.TITANIUM: re.compile(r"titanium|tytan", re.IGNORECASE),
}
