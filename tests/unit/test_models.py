import pytest
from pydantic import ValidationError

from app.core.models import BikeGeometry


def test_bike_geometry_valid():
    data = {
        "stack": 600,
        "reach": 400,
        "top_tube_effective_length": 560,
        "seat_tube_length": 540,
        "head_tube_length": 160,
        "chainstay_length": 430,
        "head_tube_angle": 71.0,
        "seat_tube_angle": 73.0,
        "bb_drop": 70,
        "wheelbase": 1020,
    }
    geo = BikeGeometry(**data)
    assert geo.stack == 600


def test_bike_geometry_invalid_angles():
    data = {
        "stack": 600,
        "reach": 400,
        "top_tube_effective_length": 560,
        "seat_tube_length": 540,
        "head_tube_length": 160,
        "chainstay_length": 430,
        "head_tube_angle": 85.0,  # Max is 75.0
        "seat_tube_angle": 73.0,
        "bb_drop": 70,
        "wheelbase": 1020,
    }
    with pytest.raises(ValidationError):
        BikeGeometry(**data)


def test_bike_geometry_negative_values():
    data = {
        "stack": -100,  # Must be positive
        "reach": 400,
        "top_tube_effective_length": 560,
        "seat_tube_length": 540,
        "head_tube_length": 160,
        "chainstay_length": 430,
        "head_tube_angle": 71.0,
        "seat_tube_angle": 73.0,
        "bb_drop": 70,
        "wheelbase": 1020,
    }
    with pytest.raises(ValidationError):
        BikeGeometry(**data)
