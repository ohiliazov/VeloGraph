from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import BikeSchema, BikeUpdateSchema, SearchResult
from app.core.db import get_db
from app.core.elasticsearch import get_es_client
from app.core.models import BikeGeometryORM, BikeMetaORM
from app.core.utils import get_simple_types

router = APIRouter()


@router.get("/", response_model=list[BikeSchema])
def list_bikes(db: Annotated[Session, Depends(get_db)], limit: int = 10):
    stmt = select(BikeMetaORM).options(selectinload(BikeMetaORM.geometries)).limit(limit)
    return db.scalars(stmt).all()


@router.get("/search", response_model=SearchResult)
async def search_bikes(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(None),
    brand: str = Query(None),
    category: str = Query(None),
    stack_min: int = Query(None),
    stack_max: int = Query(None),
    reach_min: int = Query(None),
    reach_max: int = Query(None),
):
    must = []
    if q:
        must.append({"multi_match": {"query": q, "fields": ["brand", "model_name"]}})

    filters = []
    if brand:
        filters.append({"term": {"brand.keyword": brand}})
    if category:
        # Since simple_type is now an array, "term" will find documents
        # where the array contains the value.
        filters.append({"term": {"simple_type": category}})

    # Nested filters for stack and reach
    nested_must = []
    if stack_min is not None or stack_max is not None:
        range_filter = {}
        if stack_min is not None:
            range_filter["gte"] = stack_min
        if stack_max is not None:
            range_filter["lte"] = stack_max
        nested_must.append({"range": {"geometries.stack": range_filter}})

    if reach_min is not None or reach_max is not None:
        range_filter = {}
        if reach_min is not None:
            range_filter["gte"] = reach_min
        if reach_max is not None:
            range_filter["lte"] = reach_max
        nested_must.append({"range": {"geometries.reach": range_filter}})

    if nested_must:
        filters.append({"nested": {"path": "geometries", "query": {"bool": {"filter": nested_must}}}})

    query = {"bool": {"must": must, "filter": filters}}

    if not must and not filters:
        query = {"match_all": {}}

    resp = await es.search(index="bikes", query=query, size=20)

    total = resp["hits"]["total"]["value"]
    bike_ids = [hit["_source"]["id"] for hit in resp["hits"]["hits"]]

    if not bike_ids:
        return {"total": total, "items": []}

    # Fetch full data from DB to ensure consistency and get all geometry sizes
    stmt = select(BikeMetaORM).where(BikeMetaORM.id.in_(bike_ids)).options(selectinload(BikeMetaORM.geometries))
    bikes = db.scalars(stmt).all()

    # Sort by the order in ES results
    bike_map = {b.id: b for b in bikes}
    sorted_bikes = []
    for bid in bike_ids:
        if bid not in bike_map:
            continue
        bike = bike_map[bid]

        # In-memory filter geometries to match the search criteria for the response
        if any(v is not None for v in [stack_min, stack_max, reach_min, reach_max]):
            filtered_geoms = []
            for g in bike.geometries:
                match = True
                if stack_min is not None and g.stack < stack_min:
                    match = False
                if stack_max is not None and g.stack > stack_max:
                    match = False
                if reach_min is not None and g.reach < reach_min:
                    match = False
                if reach_max is not None and g.reach > reach_max:
                    match = False
                if match:
                    filtered_geoms.append(g)
            bike.geometries = filtered_geoms

        sorted_bikes.append(bike)

    return {"total": total, "items": sorted_bikes}


@router.get("/{bike_id}", response_model=BikeSchema)
def get_bike(bike_id: int, db: Annotated[Session, Depends(get_db)]):
    stmt = select(BikeMetaORM).where(BikeMetaORM.id == bike_id).options(selectinload(BikeMetaORM.geometries))
    bike = db.scalar(stmt)
    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")
    return bike


@router.post("/", response_model=BikeSchema)
async def create_bike(
    bike_data: BikeUpdateSchema,
    db: Annotated[Session, Depends(get_db)],
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
):
    # For custom bikes, source_url should be empty and user_id should be provided
    new_bike = BikeMetaORM(
        brand=bike_data.brand,
        model_name=bike_data.model_name,
        model_year=bike_data.model_year,
        color=bike_data.color,
        categories=bike_data.categories,
        wheel_size=bike_data.wheel_size,
        frame_material=bike_data.frame_material,
        brake_type=bike_data.brake_type,
        source_url=bike_data.source_url,
        max_tire_width=bike_data.max_tire_width,
        user_id=bike_data.user_id,
    )
    db.add(new_bike)
    db.flush()  # To get new_bike.id

    for geo_data in bike_data.geometries:
        new_geo = BikeGeometryORM(
            bike_meta_id=new_bike.id,
            size_label=geo_data.size_label,
            stack=geo_data.stack,
            reach=geo_data.reach,
            top_tube_effective_length=geo_data.top_tube_effective_length,
            seat_tube_length=geo_data.seat_tube_length,
            head_tube_length=geo_data.head_tube_length,
            chainstay_length=geo_data.chainstay_length,
            head_tube_angle=geo_data.head_tube_angle,
            seat_tube_angle=geo_data.seat_tube_angle,
            bb_drop=geo_data.bb_drop,
            wheelbase=geo_data.wheelbase,
        )
        db.add(new_geo)

    db.commit()
    db.refresh(new_bike)

    # Sync to Elasticsearch
    await sync_bike_to_es(new_bike, es)

    return new_bike


async def sync_bike_to_es(bike: BikeMetaORM, es: AsyncElasticsearch):
    es_doc = {
        "id": bike.id,
        "brand": bike.brand,
        "model_name": bike.model_name,
        "model_year": bike.model_year,
        "color": bike.color,
        "frame_material": bike.frame_material,
        "source_url": bike.source_url,
        "max_tire_width": bike.max_tire_width,
        "user_id": bike.user_id,
        "simple_type": get_simple_types(bike.categories),
        "category_original": " / ".join(bike.categories),
        "geometries": [
            {
                "size_label": geo.size_label,
                "stack": geo.stack,
                "reach": geo.reach,
                "top_tube_effective_length": geo.top_tube_effective_length,
                "seat_tube_length": geo.seat_tube_length,
                "head_tube_angle": geo.head_tube_angle,
                "seat_tube_angle": geo.seat_tube_angle,
                "wheelbase": geo.wheelbase,
            }
            for geo in bike.geometries
        ],
    }
    await es.index(index="bikes", id=str(bike.id), document=es_doc, refresh=True)


@router.put("/{bike_id}", response_model=BikeSchema)
async def update_bike(
    bike_id: int,
    bike_update: BikeUpdateSchema,
    db: Annotated[Session, Depends(get_db)],
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
):
    stmt = select(BikeMetaORM).where(BikeMetaORM.id == bike_id).options(selectinload(BikeMetaORM.geometries))
    bike = db.scalar(stmt)
    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")

    # Only custom bikes can be edited.
    # Custom bikes have source_url empty (None or empty string).
    if bike.source_url and bike.source_url.strip():
        raise HTTPException(status_code=403, detail="Only custom bikes can be edited")

    bike.brand = bike_update.brand
    bike.model_name = bike_update.model_name
    bike.model_year = bike_update.model_year
    bike.color = bike_update.color
    bike.categories = bike_update.categories
    bike.wheel_size = bike_update.wheel_size
    bike.frame_material = bike_update.frame_material
    bike.brake_type = bike_update.brake_type
    bike.source_url = bike_update.source_url
    bike.max_tire_width = bike_update.max_tire_width
    bike.user_id = bike_update.user_id

    # Simple approach for geometries: replace them all
    # Delete existing geometries
    bike.geometries = []
    # Add new ones
    for geo_update in bike_update.geometries:
        new_geo = BikeGeometryORM(
            bike_meta_id=bike.id,
            size_label=geo_update.size_label,
            stack=geo_update.stack,
            reach=geo_update.reach,
            top_tube_effective_length=geo_update.top_tube_effective_length,
            seat_tube_length=geo_update.seat_tube_length,
            head_tube_length=geo_update.head_tube_length,
            chainstay_length=geo_update.chainstay_length,
            head_tube_angle=geo_update.head_tube_angle,
            seat_tube_angle=geo_update.seat_tube_angle,
            bb_drop=geo_update.bb_drop,
            wheelbase=geo_update.wheelbase,
        )
        bike.geometries.append(new_geo)

    db.commit()
    db.refresh(bike)

    # Sync to Elasticsearch
    await sync_bike_to_es(bike, es)

    return bike


@router.delete("/{bike_id}")
async def delete_bike(
    bike_id: int,
    db: Annotated[Session, Depends(get_db)],
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
):
    stmt = select(BikeMetaORM).where(BikeMetaORM.id == bike_id)
    bike = db.scalar(stmt)
    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")

    # Only custom bikes can be removed.
    if bike.source_url and bike.source_url.strip():
        raise HTTPException(status_code=403, detail="Only custom bikes can be removed")

    db.delete(bike)
    db.commit()

    # Remove from Elasticsearch
    await es.delete(index="bikes", id=str(bike_id), ignore=[404], refresh=True)

    return {"detail": "Bike deleted"}
