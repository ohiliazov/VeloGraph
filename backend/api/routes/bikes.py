from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.schemas import (
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
from core.constants import MaterialGroup
from core.db import get_async_db
from core.elasticsearch import BIKE_INDEX_NAME, GEOMETRY_INDEX_NAME, get_es_client
from core.models import BikeDefinitionORM, GeometrySpecORM
from core.utils import get_material_group

router = APIRouter()


@router.get("/definitions", response_model=list[BikeDefinitionSchema])
async def list_definitions(db: Annotated[AsyncSession, Depends(get_async_db)], limit: int = 100):
    result = await db.execute(select(BikeDefinitionORM).limit(limit))
    return result.all()


@router.post("/definitions", response_model=BikeDefinitionSchema)
async def create_definition(data: BikeDefinitionCreateSchema, db: Annotated[AsyncSession, Depends(get_async_db)]):
    new_def = BikeDefinitionORM(**data.model_dump())
    db.add(new_def)
    await db.commit()
    await db.refresh(new_def)
    return new_def


@router.post("/geometry-specs", response_model=GeometrySpecSchema)
async def create_geometry_spec(data: GeometrySpecCreateSchema, db: Annotated[AsyncSession, Depends(get_async_db)]):
    new_spec = GeometrySpecORM(**data.model_dump())
    db.add(new_spec)
    await db.commit()
    await db.refresh(new_spec)
    return new_spec


@router.get("/search/geometry", response_model=SearchResult)
async def search_geometry(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
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
        filters.append({"term": {"definition.material": material.value}})

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

    resp = await es.search(index=GEOMETRY_INDEX_NAME, query=query, sort=sort, from_=from_, size=size)
    total = resp["hits"]["total"]["value"]
    spec_ids = [hit["_source"]["id"] for hit in resp["hits"]["hits"]]

    if not spec_ids:
        return {"total": total, "items": []}

    result = await db.scalars(
        select(GeometrySpecORM)
        .where(GeometrySpecORM.id.in_(spec_ids))
        .options(
            selectinload(GeometrySpecORM.definition),
        )
    )
    specs = result.all()
    spec_map = {s.id: s for s in specs}
    sorted_specs = [spec_map[sid] for sid in spec_ids if sid in spec_map]

    return {"total": total, "items": sorted_specs}


@router.get("/search/keyword", response_model=GroupedSearchResult)
async def search_keyword(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
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
        filters.append({"term": {"definition.material": material.value}})

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
        sort.append({"definition.brand_name": "asc"})

    query = {"bool": {"must": must, "filter": filters}}
    from_ = (page - 1) * size

    resp = await es.search(index=BIKE_INDEX_NAME, query=query, sort=sort, from_=from_, size=size)
    total = resp["hits"]["total"]["value"]

    def_ids = [hit["_source"]["id"] for hit in resp["hits"]["hits"]]

    if not def_ids:
        return {"total": total, "items": []}

    result = await db.scalars(
        select(BikeDefinitionORM)
        .where(BikeDefinitionORM.id.in_(def_ids))
        .options(
            selectinload(BikeDefinitionORM.geometries),
        )
    )
    definitions = result.all()
    def_map = {d.id: d for d in definitions}
    sorted_defs = [def_map[sid] for sid in def_ids if sid in def_map]

    return {"total": total, "items": sorted_defs}


@router.get("/definitions/{def_id}", response_model=BikeDefinitionExtendedSchema)
async def get_bike_definition(def_id: int, db: Annotated[AsyncSession, Depends(get_async_db)]):
    definition = await db.scalar(
        select(BikeDefinitionORM)
        .where(BikeDefinitionORM.id == def_id)
        .options(
            selectinload(BikeDefinitionORM.geometries),
        )
    )
    if not definition:
        raise HTTPException(status_code=404, detail="Bike definition not found")

    return definition


@router.get("/specs/{spec_id}", response_model=GeometrySpecExtendedSchema)
async def get_geometry_spec(spec_id: int, db: Annotated[AsyncSession, Depends(get_async_db)]):
    spec = await db.scalar(
        select(GeometrySpecORM)
        .where(GeometrySpecORM.id == spec_id)
        .options(
            selectinload(GeometrySpecORM.definition),
        )
    )
    if not spec:
        raise HTTPException(status_code=404, detail="Geometry spec not found")

    return spec


@router.delete("/specs/{spec_id}")
async def delete_geometry_spec(
    spec_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
):
    spec = await db.scalar(select(GeometrySpecORM).where(GeometrySpecORM.id == spec_id))
    if not spec:
        raise HTTPException(status_code=404, detail="Geometry spec not found")

    await db.delete(spec)
    await db.commit()

    await es.delete(index=GEOMETRY_INDEX_NAME, id=str(spec_id), ignore=[404], refresh=True)

    def_id = spec.definition_id
    definition = await db.scalar(
        select(BikeDefinitionORM)
        .where(BikeDefinitionORM.id == def_id)
        .options(
            selectinload(BikeDefinitionORM.geometries),
        )
    )
    if not definition or not definition.geometries:
        await es.delete(index=BIKE_INDEX_NAME, id=str(def_id), ignore=[404], refresh=True)
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
    await es.index(index=BIKE_INDEX_NAME, id=str(definition.id), document=doc, refresh=True)
