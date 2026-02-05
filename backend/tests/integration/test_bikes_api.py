from backend.core.models import BikeGeometryORM, BikeMetaORM


def test_list_bikes(client, mock_db):
    # Setup mock data
    mock_bike = BikeMetaORM(
        id=1,
        brand="Kross",
        model_name="Esker 6.0",
        categories=["Gravel"],
        model_year=2023,
        geometries=[
            BikeGeometryORM(
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
        ],
    )

    mock_db.scalars.return_value.all.return_value = [mock_bike]

    response = client.get("/api/bikes/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["brand"] == "Kross"
    assert data[0]["model_name"] == "Esker 6.0"
    assert len(data[0]["geometries"]) == 1
    assert data[0]["geometries"][0]["size_label"] == "M"


def test_get_bike_found(client, mock_db):
    mock_bike = BikeMetaORM(id=1, brand="Kross", model_name="Esker 6.0", categories=["Gravel"], geometries=[])
    mock_db.scalar.return_value = mock_bike

    response = client.get("/api/bikes/1")

    assert response.status_code == 200
    assert response.json()["brand"] == "Kross"


def test_get_bike_not_found(client, mock_db):
    mock_db.scalar.return_value = None

    response = client.get("/api/bikes/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Bike not found"


def test_search_bikes(client, mock_es, mock_db):
    # Mock ES response
    mock_es.search.return_value = {"hits": {"total": {"value": 1}, "hits": [{"_source": {"id": 1}}]}}

    # Mock DB response for the ID returned by ES
    mock_bike = BikeMetaORM(
        id=1,
        brand="Kross",
        model_name="Esker 6.0",
        categories=["Gravel"],
        geometries=[
            BikeGeometryORM(
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
        ],
    )
    mock_db.scalars.return_value.all.return_value = [mock_bike]

    response = client.get("/api/bikes/search?q=Kross")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["brand"] == "Kross"


def test_update_bike(client, mock_db, mock_es):
    # Mock existing bike
    mock_bike = BikeMetaORM(id=1, brand="Kross", model_name="Esker 6.0", categories=["Gravel"], geometries=[])
    mock_db.scalar.return_value = mock_bike

    update_data = {
        "brand": "Kross Updated",
        "model_name": "Esker 7.0",
        "model_year": 2024,
        "categories": ["Gravel", "Adventure"],
        "wheel_size": "700c",
        "frame_material": "Carbon",
        "brake_type": "Disc",
        "geometries": [
            {
                "size_label": "L",
                "stack": 600,
                "reach": 400,
                "top_tube_effective_length": 570,
                "seat_tube_length": 540,
                "head_tube_length": 170,
                "chainstay_length": 435,
                "head_tube_angle": 71.5,
                "seat_tube_angle": 73.0,
                "bb_drop": 70,
                "wheelbase": 1030,
            }
        ],
    }

    response = client.put("/api/bikes/1", json=update_data)

    assert response.status_code == 200
    assert response.json()["brand"] == "Kross Updated"
    assert response.json()["model_name"] == "Esker 7.0"

    # Verify DB calls
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_bike)

    # Verify ES call
    mock_es.index.assert_called_once()
    es_call_args = mock_es.index.call_args[1]
    assert es_call_args["index"] == "bikes"
    assert es_call_args["id"] == "1"
    assert es_call_args["document"]["brand"] == "Kross Updated"
