from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import BikeSchema, SearchResult
from app.core.db import get_db
from app.core.elasticsearch import get_es_client
from app.core.models import BikeMetaORM

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
    return bike
