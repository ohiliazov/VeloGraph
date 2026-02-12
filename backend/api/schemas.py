from pydantic import BaseModel, ConfigDict, model_validator

from core.constants import BikeCategory, MaterialGroup
from core.utils import get_bike_categories, get_material_group


class BikeDefinitionSchema(BaseModel):
    id: int | None = None
    brand_name: str
    model_name: str
    category: str
    year_start: int | None = None
    year_end: int | None = None
    material: str | None = None

    model_config = ConfigDict(from_attributes=True)

    simple_categories: list[BikeCategory] = []
    simple_material: MaterialGroup | None = None

    @model_validator(mode="after")
    def set_simple_fields(self):
        self.simple_categories = get_bike_categories(self.category)
        if self.material:
            self.simple_material = get_material_group(self.material)
        return self


class GeometrySpecBaseSchema(BaseModel):
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


class GeometrySpecSchema(GeometrySpecBaseSchema):
    id: int
    definition_id: int

    model_config = ConfigDict(from_attributes=True)


class BikeDefinitionExtendedSchema(BikeDefinitionSchema):
    geometries: list[GeometrySpecSchema] = []


class GeometrySpecExtendedSchema(GeometrySpecSchema):
    definition: BikeDefinitionSchema


class BikeDefinitionCreateSchema(BaseModel):
    brand_name: str
    model_name: str
    category: str
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


class SearchResult(BaseModel):
    total: int
    items: list[GeometrySpecExtendedSchema] = []


class GroupedSearchResult(BaseModel):
    total: int
    items: list[BikeDefinitionExtendedSchema] = []
