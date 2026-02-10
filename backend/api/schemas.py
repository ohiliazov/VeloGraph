from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class BikeCategory(StrEnum):
    GRAVEL = "gravel"
    MTB = "mtb"
    TREKKING = "trekking"
    CROSS = "cross"
    ROAD = "road"
    CITY = "city"
    KIDS = "kids"
    TOURING = "touring"
    WOMEN = "women"
    OTHER = "other"


class MaterialGroup(StrEnum):
    CARBON = "carbon"
    ALUMINUM = "aluminum"
    STEEL = "steel"
    TITANIUM = "titanium"
    OTHER = "other"


class BikeFamilySchema(BaseModel):
    id: int
    brand_name: str
    family_name: str
    category: str

    model_config = ConfigDict(from_attributes=True)


class GeometrySpecSchema(BaseModel):
    id: int
    definition_id: int
    size_label: str
    stack_mm: int
    reach_mm: int
    top_tube_effective_mm: int | None = None
    seat_tube_length_mm: int | None = None
    head_tube_length_mm: int | None = None
    head_tube_angle: float
    seat_tube_angle: float
    chainstay_length_mm: int
    wheelbase_mm: int
    bb_drop_mm: int
    fork_offset_mm: int | None = None
    trail_mm: int | None = None
    standover_height_mm: int | None = None

    model_config = ConfigDict(from_attributes=True)


class FrameDefinitionSchema(BaseModel):
    id: int
    family_id: int
    name: str
    year_start: int | None = None
    year_end: int | None = None
    material: str | None = None
    family: BikeFamilySchema | None = None

    model_config = ConfigDict(from_attributes=True)


class GeometrySpecExtendedSchema(GeometrySpecSchema):
    definition: FrameDefinitionSchema


class BuildKitSchema(BaseModel):
    id: int
    name: str
    groupset: str | None = None
    wheelset: str | None = None
    cockpit: str | None = None
    tires: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BikeProductSchema(BaseModel):
    id: int
    sku: str
    colors: list[str | None] = []
    source_url: str | None = None
    geometry_spec: GeometrySpecExtendedSchema
    build_kit: BuildKitSchema

    model_config = ConfigDict(from_attributes=True)


class BikeGroupSchema(BaseModel):
    """A group of bike products (different sizes of the same model/build kit)."""

    family: BikeFamilySchema
    definition: FrameDefinitionSchema
    build_kit: BuildKitSchema
    products: list[BikeProductSchema]

    model_config = ConfigDict(from_attributes=True)


class BikeProductCreateSchema(BaseModel):
    sku: str
    colors: list[str] = []
    geometry_spec_id: int
    build_kit_id: int


class BikeFamilyCreateSchema(BaseModel):
    brand_name: str
    family_name: str
    category: str


class FrameDefinitionCreateSchema(BaseModel):
    family_id: int
    name: str
    year_start: int | None = None
    year_end: int | None = None
    material: str | None = None


class GeometrySpecCreateSchema(BaseModel):
    definition_id: int
    size_label: str
    stack_mm: int
    reach_mm: int
    top_tube_effective_mm: int | None = None
    seat_tube_length_mm: int | None = None
    head_tube_length_mm: int | None = None
    head_tube_angle: float
    seat_tube_angle: float
    chainstay_length_mm: int
    wheelbase_mm: int
    bb_drop_mm: int
    fork_offset_mm: int | None = None
    trail_mm: int | None = None
    standover_height_mm: int | None = None


class BuildKitCreateSchema(BaseModel):
    name: str
    groupset: str | None = None
    wheelset: str | None = None
    cockpit: str | None = None
    tires: str | None = None


class SearchResult(BaseModel):
    total: int
    items: list[BikeProductSchema]


class GroupedSearchResult(BaseModel):
    total: int
    items: list[BikeGroupSchema]
