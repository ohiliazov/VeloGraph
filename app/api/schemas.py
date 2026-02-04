from pydantic import BaseModel, ConfigDict


class GeometrySchema(BaseModel):
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


class BikeSchema(BaseModel):
    id: int
    brand: str
    model_name: str
    model_year: int | None = None
    color: str | None = None
    categories: list[str]
    wheel_size: str | None = None
    frame_material: str | None = None
    brake_type: str | None = None
    source_url: str | None = None
    max_tire_width: str | None = None
    geometries: list[GeometrySchema]

    model_config = ConfigDict(from_attributes=True)


class GeometryUpdateSchema(BaseModel):
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


class BikeUpdateSchema(BaseModel):
    brand: str
    model_name: str
    model_year: int | None = None
    color: str | None = None
    categories: list[str]
    wheel_size: str | None = None
    frame_material: str | None = None
    brake_type: str | None = None
    source_url: str | None = None
    max_tire_width: str | None = None
    geometries: list[GeometryUpdateSchema]


class SearchResult(BaseModel):
    total: int
    items: list[BikeSchema]
