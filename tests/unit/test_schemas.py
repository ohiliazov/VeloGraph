import pytest
from pydantic import ValidationError

from app.api.schemas import BikeSchema, BikeUpdateSchema, GeometrySchema


def test_geometry_schema_valid():
    data = {
        "size_label": "M",
        "stack": 580,
        "reach": 380,
        "top_tube_effective_length": 550,
        "seat_tube_length": 520,
        "head_tube_length": 150,
        "chainstay_length": 430,
        "head_tube_angle": 71.0,
        "seat_tube_angle": 73.5,
        "bb_drop": 70,
        "wheelbase": 1020,
    }
    geo = GeometrySchema(**data)
    assert geo.size_label == "M"
    assert geo.stack == 580


def test_geometry_schema_invalid_types():
    data = {
        "size_label": "M",
        "stack": "high",  # Should be int
        "reach": 380,
    }
    with pytest.raises(ValidationError):
        GeometrySchema(**data)


def test_bike_schema_valid():
    data = {"id": 1, "brand": "Kross", "model_name": "Esker", "categories": ["Gravel"], "geometries": []}
    bike = BikeSchema(**data)
    assert bike.brand == "Kross"
    assert bike.geometries == []


def test_bike_update_schema_missing_fields():
    data = {
        "brand": "Kross"
        # model_name is missing
    }
    with pytest.raises(ValidationError):
        BikeUpdateSchema(**data)
