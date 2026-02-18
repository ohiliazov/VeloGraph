from pydantic import BaseModel, ConfigDict, Field, computed_field

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

    @computed_field
    @property
    def simple_categories(self) -> list[BikeCategory]:
        return get_bike_categories(self.category)

    @computed_field
    @property
    def simple_material(self) -> MaterialGroup | None:
        if self.material:
            return get_material_group(self.material)
        return None


class GeometrySpecSchema(BaseModel):
    size_label: str
    stack_mm: int = Field(gt=0)
    reach_mm: int = Field(gt=0)
    top_tube_effective_mm: int | None = Field(default=None, gt=0)
    seat_tube_length_mm: int | None = Field(default=None, gt=0)
    head_tube_length_mm: int | None = Field(default=None, gt=0)
    head_tube_angle: float = Field(gt=0, lt=90)
    seat_tube_angle: float = Field(gt=0, lt=90)
    chainstay_length_mm: int = Field(gt=0)
    wheelbase_mm: int = Field(gt=0)
    bb_drop_mm: int = Field(ge=0)
    fork_offset_mm: int | None = Field(default=None, ge=0)
    trail_mm: int | None = Field(default=None, gt=0)
    standover_height_mm: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(from_attributes=True)


class GeometrySpecExtendedSchema(GeometrySpecSchema):
    definition: BikeDefinitionSchema


class GeometrySpecCreateSchema(GeometrySpecSchema):
    definition_id: int


class BikeDefinitionExtendedSchema(BikeDefinitionSchema):
    geometries: list[GeometrySpecSchema] = Field(default_factory=list)


class BikeDefinitionCreateSchema(BaseModel):
    brand_name: str
    model_name: str
    category: str
    year_start: int | None = None
    year_end: int | None = None
    material: str | None = None


class SearchResult(BaseModel):
    total: int
    items: list[GeometrySpecExtendedSchema] = Field(default_factory=list)


class GroupedSearchResult(BaseModel):
    total: int
    items: list[BikeDefinitionExtendedSchema] = Field(default_factory=list)


class MessageResponse(BaseModel):
    detail: str
