from pydantic import BaseModel, ConfigDict


class GeometrySchema(BaseModel):
    id: int
    size_label: str
    stack: int
    reach: int
    top_tube_effective_length: int
    seat_tube_length: int
    head_tube_length: int
    chainstay_length: int
    head_tube_angle: float
    seat_tube_angle: float
    bb_drop: int
    wheelbase: int

    model_config = ConfigDict(from_attributes=True)


class FramesetSchema(BaseModel):
    id: int
    name: str
    material: str | None = None
    geometry_id: int
    geometry_data: GeometrySchema

    model_config = ConfigDict(from_attributes=True)


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
    frameset: FramesetSchema
    build_kit: BuildKitSchema

    model_config = ConfigDict(from_attributes=True)


class BikeProductCreateSchema(BaseModel):
    sku: str
    frameset_id: int
    build_kit_id: int


class GeometryCreateSchema(BaseModel):
    size_label: str
    stack: int
    reach: int
    top_tube_effective_length: int
    seat_tube_length: int
    head_tube_length: int
    chainstay_length: int
    head_tube_angle: float
    seat_tube_angle: float
    bb_drop: int
    wheelbase: int


class FramesetCreateSchema(BaseModel):
    name: str
    material: str | None = None
    geometry_id: int


class BuildKitCreateSchema(BaseModel):
    name: str
    groupset: str | None = None
    wheelset: str | None = None
    cockpit: str | None = None
    tires: str | None = None


class SearchResult(BaseModel):
    total: int
    items: list[BikeProductSchema]
