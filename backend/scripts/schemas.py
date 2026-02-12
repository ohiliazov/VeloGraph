from pydantic import BaseModel

from backend.api.schemas import BikeDefinitionSchema, GeometrySpecBaseSchema


class ExtractedData(BaseModel):
    bike_definition: BikeDefinitionSchema
    geometries: list[GeometrySpecBaseSchema]
