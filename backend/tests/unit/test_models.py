import pytest
from pydantic import ValidationError

from core.models import GeometryData


def test_geometry_data_valid():
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
    geo = GeometryData(**data)
    assert geo.stack == 600


def test_geometry_data_invalid_angles():
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
        GeometryData(**data)


def test_geometry_data_negative_values():
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
        GeometryData(**data)
