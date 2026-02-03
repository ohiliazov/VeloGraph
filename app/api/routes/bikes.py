from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.annotation import Annotated

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
    q: Annotated[str, Query(None)],
    brand: Annotated[str, Query(None)],
    category: Annotated[str, Query(None)],
):
    must = []
    if q:
        must.append({"multi_match": {"query": q, "fields": ["brand", "model_name"]}})

    filters = []
    if brand:
        filters.append({"term": {"brand.keyword": brand}})
    if category:
        filters.append({"term": {"simple_type": category}})

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
    sorted_bikes = [bike_map[bid] for bid in bike_ids if bid in bike_map]

    return {"total": total, "items": sorted_bikes}


@router.get("/{bike_id}", response_model=BikeSchema)
def get_bike(bike_id: int, db: Annotated[Session, Depends(get_db)]):
    stmt = select(BikeMetaORM).where(BikeMetaORM.id == bike_id).options(selectinload(BikeMetaORM.geometries))
    bike = db.scalar(stmt)
    return bike
