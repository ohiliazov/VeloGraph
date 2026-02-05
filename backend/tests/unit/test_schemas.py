from backend.api.schemas import BikeProductSchema, FramesetSchema


def test_frameset_schema_valid():
    data = {
        "id": 1,
        "name": "Esker",
        "material": "Carbon",
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
    fs = FramesetSchema(**data)
    assert fs.name == "Esker"
    assert fs.stack == 580


def test_bike_product_schema_valid():
    data = {
        "id": 1,
        "sku": "ESKER-6.0-2023",
        "frameset": {
            "id": 1,
            "name": "Esker",
            "material": "Carbon",
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
    assert product.frameset.name == "Esker"
    assert product.build_kit.groupset == "Shimano GRX"
