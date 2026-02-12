from backend.core.models import BikeDefinitionORM, BikeProductORM, BuildKitORM, FrameDefinitionORM, GeometrySpecORM


def test_search_geometry(client, mock_es, mock_db):
    # Mock ES response
    mock_es.search.return_value = {"hits": {"total": {"value": 1}, "hits": [{"_source": {"id": 1}}]}}

    # Mock DB response
    mock_family = BikeDefinitionORM(id=1, brand_name="Kross", family_name="Esker", category="gravel")
    mock_def = FrameDefinitionORM(id=1, family_id=1, name="Esker", material="Carbon", family=mock_family)
    mock_spec = GeometrySpecORM(
        id=1,
        definition_id=1,
        size_label="M",
        stack_mm=580,
        reach_mm=380,
        top_tube_effective_mm=550,
        seat_tube_length_mm=520,
        head_tube_length_mm=150,
        chainstay_length_mm=430,
        head_tube_angle=71.0,
        seat_tube_angle=73.5,
        bb_drop_mm=70,
        wheelbase_mm=1020,
        definition=mock_def,
    )
    mock_bk = BuildKitORM(id=1, name="GRX 600", groupset="Shimano GRX")
    mock_product = BikeProductORM(
        id=1,
        sku="ESKER-6.0",
        geometry_spec_id=1,
        build_kit_id=1,
        geometry_spec=mock_spec,
        build_kit=mock_bk,
        colors=[],
    )
    mock_db.scalars.return_value.all.return_value = [mock_product]

    response = client.get("/api/bikes/search/geometry?stack=580&reach=380")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["sku"] == "ESKER-6.0"


def test_search_keyword(client, mock_es, mock_db):
    # Mock ES response
    mock_es.search.return_value = {
        "hits": {
            "total": {"value": 1},
            "hits": [{"_source": {"product_ids": [1]}}],
        }
    }

    # Mock DB response
    mock_family = BikeDefinitionORM(id=1, brand_name="Kross", family_name="Esker", category="gravel")
    mock_def = FrameDefinitionORM(id=1, family_id=1, name="Esker", material="Carbon", family=mock_family)
    mock_spec = GeometrySpecORM(
        id=1,
        definition_id=1,
        size_label="M",
        stack_mm=580,
        reach_mm=380,
        top_tube_effective_mm=550,
        seat_tube_length_mm=520,
        head_tube_length_mm=150,
        chainstay_length_mm=430,
        head_tube_angle=71.0,
        seat_tube_angle=73.5,
        bb_drop_mm=70,
        wheelbase_mm=1020,
        definition=mock_def,
    )
    mock_bk = BuildKitORM(id=1, name="GRX 600", groupset="Shimano GRX")
    mock_product = BikeProductORM(
        id=1,
        sku="ESKER-6.0",
        geometry_spec_id=1,
        build_kit_id=1,
        geometry_spec=mock_spec,
        build_kit=mock_bk,
        colors=[],
    )
    mock_db.scalars.return_value.all.return_value = [mock_product]

    response = client.get("/api/bikes/search/keyword?q=Esker")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["family"]["family_name"] == "Esker"
    assert data["items"][0]["products"][0]["sku"] == "ESKER-6.0"


def test_get_bike_product_found(client, mock_db):
    mock_family = BikeDefinitionORM(id=1, brand_name="Kross", family_name="Esker", category="gravel")
    mock_def = FrameDefinitionORM(id=1, family_id=1, name="Esker", material="Carbon", family=mock_family)
    mock_spec = GeometrySpecORM(
        id=1,
        definition_id=1,
        size_label="M",
        stack_mm=580,
        reach_mm=380,
        top_tube_effective_mm=550,
        seat_tube_length_mm=520,
        head_tube_length_mm=150,
        chainstay_length_mm=430,
        head_tube_angle=71.0,
        seat_tube_angle=73.5,
        bb_drop_mm=70,
        wheelbase_mm=1020,
        definition=mock_def,
    )
    mock_bk = BuildKitORM(id=1, name="GRX 600", groupset="Shimano GRX")
    mock_product = BikeProductORM(
        id=1,
        sku="ESKER-6.0",
        geometry_spec_id=1,
        build_kit_id=1,
        geometry_spec=mock_spec,
        build_kit=mock_bk,
        colors=[],
    )
    mock_db.scalar.return_value = mock_product
    mock_db.scalars.return_value.all.return_value = [mock_product]

    response = client.get("/api/bikes/1")

    assert response.status_code == 200
    data = response.json()
    assert data["family"]["family_name"] == "Esker"
    assert data["products"][0]["sku"] == "ESKER-6.0"


def test_get_bike_product_not_found(client, mock_db):
    mock_db.scalar.return_value = None

    response = client.get("/api/bikes/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Bike product not found"


def test_create_bike_product(client, mock_db, mock_es):
    mock_family = BikeDefinitionORM(id=1, brand_name="Kross", family_name="Esker", category="gravel")
    mock_def = FrameDefinitionORM(id=1, family_id=1, name="Esker", material="Carbon", family=mock_family)
    mock_spec = GeometrySpecORM(
        id=1,
        definition_id=1,
        size_label="M",
        stack_mm=580,
        reach_mm=380,
        top_tube_effective_mm=550,
        seat_tube_length_mm=520,
        head_tube_length_mm=150,
        chainstay_length_mm=430,
        head_tube_angle=71.0,
        seat_tube_angle=73.5,
        bb_drop_mm=70,
        wheelbase_mm=1020,
        definition=mock_def,
    )
    mock_bk = BuildKitORM(id=1, name="GRX 600", groupset="Shimano GRX")
    mock_product = BikeProductORM(
        id=1,
        sku="NEW-SKU",
        geometry_spec_id=1,
        build_kit_id=1,
        geometry_spec=mock_spec,
        build_kit=mock_bk,
        colors=[],
    )

    # Mock behavior for creation
    mock_db.refresh.side_effect = lambda x: setattr(x, "id", 1)
    mock_db.scalar.return_value = mock_product
    mock_db.scalars.return_value.all.return_value = [mock_product]

    create_data = {"sku": "NEW-SKU", "geometry_spec_id": 1, "build_kit_id": 1}

    response = client.post("/api/bikes/", json=create_data)

    assert response.status_code == 200
    assert response.json()["sku"] == "NEW-SKU"

    # Verify ES calls
    assert mock_es.index.call_count == 2
    # Second call is for the group
    group_call_args = mock_es.index.call_args_list[1][1]
    assert group_call_args["index"] == "bike_products"
    assert "NEW-SKU" in group_call_args["document"]["skus"]
