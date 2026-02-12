from pydantic import BaseModel

from api.schemas import BikeDefinitionSchema, GeometrySpecBaseSchema


class ExtractedData(BaseModel):
    bike_definition: BikeDefinitionSchema
    geometries: list[GeometrySpecBaseSchema]
