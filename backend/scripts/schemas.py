from pydantic import BaseModel

from api.schemas import BikeDefinitionSchema, GeometrySpecSchema


class ExtractedData(BaseModel):
    bike_definition: BikeDefinitionSchema
    geometries: list[GeometrySpecSchema]
