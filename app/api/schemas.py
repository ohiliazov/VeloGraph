from pydantic import BaseModel


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

    class Config:
        from_attributes = True


class BikeSchema(BaseModel):
    id: int
    brand: str
    model_name: str
    model_year: int | None
    categories: list[str]
    wheel_size: str | None
    frame_material: str | None
    brake_type: str | None
    geometries: list[GeometrySchema]

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    total: int
    items: list[BikeSchema]
