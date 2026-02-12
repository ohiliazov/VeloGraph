from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.api.schemas import (
    BikeCategory,
    BikeDefinitionCreateSchema,
    BikeDefinitionExtendedSchema,
    BikeDefinitionSchema,
    GeometrySpecCreateSchema,
    GeometrySpecExtendedSchema,
    GeometrySpecSchema,
    GroupedSearchResult,
    SearchResult,
)
from backend.core.constants import BIKE_PRODUCT_INDEX, FRAMESET_GEOMETRY_INDEX, MaterialGroup
from backend.core.db import get_db
from backend.core.elasticsearch import get_es_client
from backend.core.models import BikeDefinitionORM, GeometrySpecORM
from backend.core.utils import get_material_group

router = APIRouter()


@router.get("/definitions", response_model=list[BikeDefinitionSchema])
def list_definitions(db: Annotated[Session, Depends(get_db)], limit: int = 100):
    stmt = select(BikeDefinitionORM).limit(limit)
    return db.scalars(stmt).all()


@router.post("/definitions", response_model=BikeDefinitionSchema)
def create_definition(data: BikeDefinitionCreateSchema, db: Annotated[Session, Depends(get_db)]):
    new_def = BikeDefinitionORM(**data.model_dump())
    db.add(new_def)
    db.commit()
    db.refresh(new_def)
    return new_def


@router.post("/geometry-specs", response_model=GeometrySpecSchema)
def create_geometry_spec(data: GeometrySpecCreateSchema, db: Annotated[Session, Depends(get_db)]):
    new_spec = GeometrySpecORM(**data.model_dump())
    db.add(new_spec)
    db.commit()
    db.refresh(new_spec)
    return new_spec


@router.get("/search/geometry", response_model=SearchResult)
async def search_geometry(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
    db: Annotated[Session, Depends(get_db)],
    stack: Annotated[int, Query(description="Target stack in mm")],
    reach: Annotated[int, Query(description="Target reach in mm")],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    category: Annotated[BikeCategory | None, Query()] = None,
    material: Annotated[MaterialGroup | None, Query()] = None,
):
    filters = []
    if category:
        filters.append({"term": {"definition.category": category.value}})
    if material:
        filters.append({"term": {"definition.material_group": material.value}})

    sort = [
        {
            "_script": {
                "type": "number",
                "script": {
                    "lang": "painless",
                    "source": """
                    double dStack = doc['geometry_spec.stack_mm'].value - params.targetStack;
                    double dReach = doc['geometry_spec.reach_mm'].value - params.targetReach;
                    return Math.sqrt(dStack * dStack + dReach * dReach);
                """,
                    "params": {"targetStack": stack, "targetReach": reach},
                },
                "order": "asc",
            }
        }
    ]

    query = {"bool": {"filter": filters}}
    from_ = (page - 1) * size

    resp = await es.search(index=FRAMESET_GEOMETRY_INDEX, query=query, sort=sort, from_=from_, size=size)
    total = resp["hits"]["total"]["value"]
    spec_ids = [hit["_source"]["id"] for hit in resp["hits"]["hits"]]

    if not spec_ids:
        return {"total": total, "items": []}

    stmt = (
        select(GeometrySpecORM)
        .where(GeometrySpecORM.id.in_(spec_ids))
        .options(
            selectinload(GeometrySpecORM.definition),
        )
    )
    specs = db.scalars(stmt).all()
    spec_map = {s.id: s for s in specs}
    sorted_specs = [spec_map[sid] for sid in spec_ids if sid in spec_map]

    return {"total": total, "items": sorted_specs}


@router.get("/search/keyword", response_model=GroupedSearchResult)
async def search_keyword(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(description="Search by brand or model")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    category: Annotated[BikeCategory | None, Query()] = None,
    material: Annotated[MaterialGroup | None, Query()] = None,
):
    filters = []
    if category:
        filters.append({"term": {"definition.category": category.value}})
    if material:
        filters.append({"term": {"definition.material_group": material.value}})

    must = []
    if q:
        must.append(
            {
                "multi_match": {
                    "query": q,
                    "fields": [
                        "definition.brand_name^3",
                        "definition.model_name^2",
                    ],
                    "fuzziness": "AUTO",
                }
            }
        )

    sort = []
    if q:
        sort.append("_score")
    else:
        sort.append({"definition.brand_name.keyword": "asc"})

    query = {"bool": {"must": must, "filter": filters}}
    from_ = (page - 1) * size

    resp = await es.search(index=BIKE_PRODUCT_INDEX, query=query, sort=sort, from_=from_, size=size)
    total = resp["hits"]["total"]["value"]

    def_ids = [hit["_source"]["id"] for hit in resp["hits"]["hits"]]

    if not def_ids:
        return {"total": total, "items": []}

    stmt = (
        select(BikeDefinitionORM)
        .where(BikeDefinitionORM.id.in_(def_ids))
        .options(
            selectinload(BikeDefinitionORM.geometries),
        )
    )
    definitions = db.scalars(stmt).all()
    def_map = {d.id: d for d in definitions}
    sorted_defs = [def_map[sid] for sid in def_ids if sid in def_map]

    return {"total": total, "items": sorted_defs}


@router.get("/definitions/{def_id}", response_model=BikeDefinitionExtendedSchema)
def get_bike_definition(def_id: int, db: Annotated[Session, Depends(get_db)]):
    stmt = (
        select(BikeDefinitionORM)
        .where(BikeDefinitionORM.id == def_id)
        .options(
            selectinload(BikeDefinitionORM.geometries),
        )
    )
    definition = db.scalar(stmt)
    if not definition:
        raise HTTPException(status_code=404, detail="Bike definition not found")

    return definition


@router.get("/specs/{spec_id}", response_model=GeometrySpecExtendedSchema)
def get_geometry_spec(spec_id: int, db: Annotated[Session, Depends(get_db)]):
    stmt = (
        select(GeometrySpecORM)
        .where(GeometrySpecORM.id == spec_id)
        .options(
            selectinload(GeometrySpecORM.definition),
        )
    )
    spec = db.scalar(stmt)
    if not spec:
        raise HTTPException(status_code=404, detail="Geometry spec not found")

    return spec


@router.delete("/specs/{spec_id}")
async def delete_geometry_spec(
    spec_id: int,
    db: Annotated[Session, Depends(get_db)],
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
):
    stmt = select(GeometrySpecORM).where(GeometrySpecORM.id == spec_id)
    spec = db.scalar(stmt)
    if not spec:
        raise HTTPException(status_code=404, detail="Geometry spec not found")

    def_id = spec.definition_id
    db.delete(spec)
    db.commit()

    await es.delete(index=FRAMESET_GEOMETRY_INDEX, id=str(spec_id), ignore=[404], refresh=True)

    # Re-sync parent definition to BIKE_PRODUCT_INDEX
    stmt = (
        select(BikeDefinitionORM)
        .where(BikeDefinitionORM.id == def_id)
        .options(
            selectinload(BikeDefinitionORM.geometries),
        )
    )
    definition = db.scalar(stmt)
    if not definition or not definition.geometries:
        await es.delete(index=BIKE_PRODUCT_INDEX, id=str(def_id), ignore=[404], refresh=True)
    else:
        await sync_definition_to_es(definition, es)

    return {"detail": "Geometry spec deleted"}


async def sync_definition_to_es(definition: BikeDefinitionORM, es: AsyncElasticsearch):
    # This will be used to populate BIKE_PRODUCT_INDEX (grouped view)
    doc = {
        "id": definition.id,
        "definition": {
            "brand_name": definition.brand_name,
            "model_name": definition.model_name,
            "category": definition.category,
            "material": definition.material,
            "material_group": get_material_group(definition.material),
        },
        "sizes": [s.size_label for s in definition.geometries],
    }
    await es.index(index=BIKE_PRODUCT_INDEX, id=str(definition.id), document=doc, refresh=True)
