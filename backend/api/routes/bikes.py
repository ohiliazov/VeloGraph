from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.api.schemas import (
    BikeGroupSchema,
    BikeProductCreateSchema,
    BikeProductSchema,
    BuildKitCreateSchema,
    BuildKitSchema,
    FramesetCreateSchema,
    FramesetSchema,
    SearchResult,
)
from backend.core.db import get_db
from backend.core.elasticsearch import get_es_client
from backend.core.models import BikeProductORM, BuildKitORM, FramesetORM

router = APIRouter()


@router.get("/", response_model=list[BikeGroupSchema])
def list_bike_products(db: Annotated[Session, Depends(get_db)], limit: int = 50):
    stmt = (
        select(BikeProductORM)
        .options(
            selectinload(BikeProductORM.frameset),
            selectinload(BikeProductORM.build_kit),
        )
        .limit(limit)
    )
    products = db.scalars(stmt).all()
    return _group_products(products)


def _group_products(products: list[BikeProductORM]) -> list[dict]:
    """Helper to group BikeProductORM objects by Frameset name and BuildKit."""
    groups = {}
    for p in products:
        # Group by Frameset Name + Material + BuildKit ID
        key = (p.frameset.name, p.frameset.material, p.build_kit_id)
        if key not in groups:
            groups[key] = {
                "frameset_name": p.frameset.name,
                "material": p.frameset.material,
                "build_kit": p.build_kit,
                "products": [],
            }
        groups[key]["products"].append(p)

    # Sort products within each group by stack (smallest to largest)
    for group in groups.values():
        group["products"].sort(key=lambda x: x.frameset.stack)

    return list(groups.values())


@router.get("/framesets", response_model=list[FramesetSchema])
def list_framesets(db: Annotated[Session, Depends(get_db)], limit: int = 10):
    stmt = select(FramesetORM).limit(limit)
    return db.scalars(stmt).all()


@router.post("/framesets", response_model=FramesetSchema)
def create_frameset(data: FramesetCreateSchema, db: Annotated[Session, Depends(get_db)]):
    new_fs = FramesetORM(**data.model_dump())
    db.add(new_fs)
    db.commit()
    db.refresh(new_fs)
    return new_fs


@router.post("/build-kits", response_model=BuildKitSchema)
def create_build_kit(data: BuildKitCreateSchema, db: Annotated[Session, Depends(get_db)]):
    new_bk = BuildKitORM(**data.model_dump())
    db.add(new_bk)
    db.commit()
    db.refresh(new_bk)
    return new_bk


@router.get("/search", response_model=SearchResult)
async def search_bike_products(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(None),
    material: str = Query(None),
    groupset: str = Query(None),
    stack_min: int = Query(None),
    stack_max: int = Query(None),
    reach_min: int = Query(None),
    reach_max: int = Query(None),
):
    must = []
    if q:
        must.append({"multi_match": {"query": q, "fields": ["sku", "frameset.name", "build_kit.name"]}})

    filters = []
    if material:
        filters.append({"term": {"frameset.material.keyword": material}})
    if groupset:
        filters.append({"term": {"build_kit.groupset.keyword": groupset}})

    if stack_min is not None or stack_max is not None:
        range_filter = {}
        if stack_min is not None:
            range_filter["gte"] = stack_min
        if stack_max is not None:
            range_filter["lte"] = stack_max
        filters.append({"range": {"frameset.stack": range_filter}})

    if reach_min is not None or reach_max is not None:
        range_filter = {}
        if reach_min is not None:
            range_filter["gte"] = reach_min
        if reach_max is not None:
            range_filter["lte"] = reach_max
        filters.append({"range": {"frameset.reach": range_filter}})

    query = {"bool": {"must": must, "filter": filters}}

    if not must and not filters:
        query = {"match_all": {}}

    resp = await es.search(index="bike_products", query=query, size=20)

    total = resp["hits"]["total"]["value"]
    product_ids = [hit["_source"]["id"] for hit in resp["hits"]["hits"]]

    if not product_ids:
        return {"total": total, "items": []}

    stmt = (
        select(BikeProductORM)
        .where(BikeProductORM.id.in_(product_ids))
        .options(
            selectinload(BikeProductORM.frameset),
            selectinload(BikeProductORM.build_kit),
        )
    )
    products = db.scalars(stmt).all()

    # Sort by the order in ES results
    product_map = {p.id: p for p in products}
    sorted_products = [product_map[pid] for pid in product_ids if pid in product_map]

    grouped = _group_products(sorted_products)
    return {"total": len(grouped), "items": grouped}


@router.get("/{product_id}", response_model=BikeGroupSchema)
def get_bike_product(product_id: int, db: Annotated[Session, Depends(get_db)]):
    stmt = (
        select(BikeProductORM)
        .where(BikeProductORM.id == product_id)
        .options(
            selectinload(BikeProductORM.frameset),
            selectinload(BikeProductORM.build_kit),
        )
    )
    product = db.scalar(stmt)
    if not product:
        raise HTTPException(status_code=404, detail="Bike product not found")

    # Find sibling products (other sizes of the same model/build kit)
    sibling_stmt = (
        select(BikeProductORM)
        .where(
            BikeProductORM.frameset_id.in_(
                select(FramesetORM.id).where(
                    FramesetORM.name == product.frameset.name,
                    FramesetORM.material == product.frameset.material,
                )
            ),
            BikeProductORM.build_kit_id == product.build_kit_id,
        )
        .options(
            selectinload(BikeProductORM.frameset),
            selectinload(BikeProductORM.build_kit),
        )
    )
    siblings = db.scalars(sibling_stmt).all()
    siblings.sort(key=lambda x: x.frameset.stack)

    return {
        "frameset_name": product.frameset.name,
        "material": product.frameset.material,
        "build_kit": product.build_kit,
        "products": siblings,
    }


@router.post("/", response_model=BikeProductSchema)
async def create_bike_product(
    product_data: BikeProductCreateSchema,
    db: Annotated[Session, Depends(get_db)],
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
):
    new_product = BikeProductORM(**product_data.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # Re-fetch with relations for ES sync
    stmt = (
        select(BikeProductORM)
        .where(BikeProductORM.id == new_product.id)
        .options(
            selectinload(BikeProductORM.frameset),
            selectinload(BikeProductORM.build_kit),
        )
    )
    product = db.scalar(stmt)

    # Sync to Elasticsearch
    await sync_product_to_es(product, es)

    return product


async def sync_product_to_es(product: BikeProductORM, es: AsyncElasticsearch):
    es_doc = {
        "id": product.id,
        "sku": product.sku,
        "colors": product.colors,
        "frameset": {
            "name": product.frameset.name,
            "material": product.frameset.material,
            "size_label": product.frameset.size_label,
            "stack": product.frameset.stack,
            "reach": product.frameset.reach,
        },
        "build_kit": {
            "name": product.build_kit.name,
            "groupset": product.build_kit.groupset,
            "wheelset": product.build_kit.wheelset,
        },
    }
    await es.index(index="bike_products", id=str(product.id), document=es_doc, refresh=True)


@router.delete("/{product_id}")
async def delete_bike_product(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
):
    stmt = select(BikeProductORM).where(BikeProductORM.id == product_id)
    product = db.scalar(stmt)
    if not product:
        raise HTTPException(status_code=404, detail="Bike product not found")

    db.delete(product)
    db.commit()

    # Remove from Elasticsearch
    await es.delete(index="bike_products", id=str(product_id), ignore=[404], refresh=True)

    return {"detail": "Bike product deleted"}
