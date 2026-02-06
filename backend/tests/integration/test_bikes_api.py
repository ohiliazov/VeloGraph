from backend.core.models import BikeProductORM, BuildKitORM, FramesetORM


def test_search_bike_products(client, mock_es, mock_db):
    # Mock ES response
    mock_es.search.return_value = {"hits": {"total": {"value": 1}, "hits": [{"_source": {"id": 1}}]}}

    # Mock DB response
    mock_fs = FramesetORM(
        id=1,
        name="Esker",
        material="Carbon",
        size_label="M",
        stack=580,
        reach=380,
        top_tube_effective_length=550,
        seat_tube_length=520,
        head_tube_length=150,
        chainstay_length=430,
        head_tube_angle=71.0,
        seat_tube_angle=73.5,
        bb_drop=70,
        wheelbase=1020,
    )
    mock_bk = BuildKitORM(id=1, name="GRX 600", groupset="Shimano GRX")
    mock_product = BikeProductORM(
        id=1, sku="ESKER-6.0", frameset_id=1, build_kit_id=1, frameset=mock_fs, build_kit=mock_bk, colors=[]
    )
    mock_db.scalars.return_value.all.return_value = [mock_product]

    response = client.get("/api/bikes/search?stack=580&reach=380")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["frameset_name"] == "Esker"
    assert data["items"][0]["products"][0]["sku"] == "ESKER-6.0"


def test_get_bike_product_found(client, mock_db):
    mock_fs = FramesetORM(
        id=1,
        name="Esker",
        material="Carbon",
        size_label="M",
        stack=580,
        reach=380,
        top_tube_effective_length=550,
        seat_tube_length=520,
        head_tube_length=150,
        chainstay_length=430,
        head_tube_angle=71.0,
        seat_tube_angle=73.5,
        bb_drop=70,
        wheelbase=1020,
    )
    mock_bk = BuildKitORM(id=1, name="GRX 600", groupset="Shimano GRX")
    mock_product = BikeProductORM(
        id=1, sku="ESKER-6.0", frameset_id=1, build_kit_id=1, frameset=mock_fs, build_kit=mock_bk, colors=[]
    )
    mock_db.scalar.return_value = mock_product
    mock_db.scalars.return_value.all.return_value = [mock_product]

    response = client.get("/api/bikes/1")

    assert response.status_code == 200
    data = response.json()
    assert data["frameset_name"] == "Esker"
    assert data["products"][0]["sku"] == "ESKER-6.0"


def test_get_bike_product_not_found(client, mock_db):
    mock_db.scalar.return_value = None

    response = client.get("/api/bikes/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Bike product not found"


def test_create_bike_product(client, mock_db, mock_es):
    mock_fs = FramesetORM(
        id=1,
        name="Esker",
        material="Carbon",
        size_label="M",
        stack=580,
        reach=380,
        top_tube_effective_length=550,
        seat_tube_length=520,
        head_tube_length=150,
        chainstay_length=430,
        head_tube_angle=71.0,
        seat_tube_angle=73.5,
        bb_drop=70,
        wheelbase=1020,
    )
    mock_bk = BuildKitORM(id=1, name="GRX 600", groupset="Shimano GRX")
    mock_product = BikeProductORM(
        id=1, sku="NEW-SKU", frameset_id=1, build_kit_id=1, frameset=mock_fs, build_kit=mock_bk, colors=[]
    )

    # Mock behavior for creation
    mock_db.refresh.side_effect = lambda x: setattr(x, "id", 1)
    mock_db.scalar.return_value = mock_product

    create_data = {"sku": "NEW-SKU", "frameset_id": 1, "build_kit_id": 1}

    response = client.post("/api/bikes/", json=create_data)

    assert response.status_code == 200
    assert response.json()["sku"] == "NEW-SKU"

    # Verify ES call
    mock_es.index.assert_called_once()
    es_call_args = mock_es.index.call_args[1]
    assert es_call_args["index"] == "bike_products"
    assert es_call_args["document"]["sku"] == "NEW-SKU"
