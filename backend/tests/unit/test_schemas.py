from backend.api.schemas import BikeProductSchema, GeometrySpecExtendedSchema


def test_geometry_spec_schema_valid():
    data = {
        "id": 1,
        "definition_id": 1,
        "size_label": "M",
        "stack_mm": 580,
        "reach_mm": 380,
        "top_tube_effective_mm": 550,
        "seat_tube_length_mm": 520,
        "head_tube_length_mm": 150,
        "chainstay_length_mm": 430,
        "head_tube_angle": 71.0,
        "seat_tube_angle": 73.5,
        "bb_drop_mm": 70,
        "wheelbase_mm": 1020,
        "definition": {
            "id": 1,
            "family_id": 1,
            "name": "Esker",
            "material": "Carbon",
            "family": {"id": 1, "brand_name": "Kross", "family_name": "Esker", "category": "gravel"},
        },
    }
    gs = GeometrySpecExtendedSchema(**data)
    assert gs.definition.model_name == "Esker"
    assert gs.stack_mm == 580


def test_bike_product_schema_valid():
    data = {
        "id": 1,
        "sku": "ESKER-6.0-2023",
        "geometry_spec": {
            "id": 1,
            "definition_id": 1,
            "size_label": "M",
            "stack_mm": 580,
            "reach_mm": 380,
            "top_tube_effective_mm": 550,
            "seat_tube_length_mm": 520,
            "head_tube_length_mm": 150,
            "chainstay_length_mm": 430,
            "head_tube_angle": 71.0,
            "seat_tube_angle": 73.5,
            "bb_drop_mm": 70,
            "wheelbase_mm": 1020,
            "definition": {
                "id": 1,
                "family_id": 1,
                "name": "Esker",
                "material": "Carbon",
                "family": {
                    "id": 1,
                    "brand_name": "Kross",
                    "family_name": "Esker",
                    "category": "gravel",
                },
            },
        },
        "build_kit": {
            "id": 1,
            "name": "GRX 600",
            "groupset": "Shimano GRX",
            "wheelset": "DT Swiss",
            "cockpit": "Easton",
            "tires": "WTB",
        },
    }
    product = BikeProductSchema(**data)
    assert product.sku == "ESKER-6.0-2023"
    assert product.geometry_spec.definition.model_name == "Esker"
    assert product.build_kit.groupset == "Shimano GRX"
