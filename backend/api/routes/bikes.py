from typing import Annotated, cast

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.api.schemas import (
    BikeCategory,
    BikeGroupSchema,
    BikeProductCreateSchema,
    BikeProductSchema,
    BuildKitCreateSchema,
    BuildKitSchema,
    FramesetCreateSchema,
    FramesetSchema,
    GroupedSearchResult,
    MaterialGroup,
    SearchResult,
)
from backend.core.db import get_db
from backend.core.elasticsearch import get_es_client
from backend.core.models import BikeProductORM, BuildKitORM, FramesetORM
from backend.core.utils import get_material_group

router = APIRouter()


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
        filters.append({"term": {"frameset.category": category.value}})
    if material:
        filters.append({"term": {"frameset.material_group": material.value}})

    # Script-based sorting for Euclidean distance from target (stack, reach)
    sort = [
        {
            "_script": {
                "type": "number",
                "script": {
                    "lang": "painless",
                    "source": """
                    double dStack = doc['frameset.stack'].value - params.targetStack;
                    double dReach = doc['frameset.reach'].value - params.targetReach;
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

    resp = await es.search(index="bike_products", query=query, sort=sort, from_=from_, size=size)
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
    product_map = {p.id: p for p in products}
    sorted_products = [product_map[pid] for pid in product_ids if pid in product_map]

    return {"total": total, "items": sorted_products}


@router.get("/search/keyword", response_model=GroupedSearchResult)
async def search_keyword(
    es: Annotated[AsyncElasticsearch, Depends(get_es_client)],
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(description="Search by brand, model or SKU")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    category: Annotated[BikeCategory | None, Query()] = None,
    material: Annotated[MaterialGroup | None, Query()] = None,
):
    filters = []
    if category:
        filters.append({"term": {"frameset.category": category.value}})
    if material:
        filters.append({"term": {"frameset.material_group": material.value}})

    must = []
    if q:
        must.append(
            {
                "multi_match": {
                    "query": q,
                    "fields": ["frameset.name^3", "sku", "build_kit.name", "build_kit.groupset"],
                    "fuzziness": "AUTO",
                }
            }
        )

    sort = []
    if q:
        sort.append("_score")
    else:
        sort.append({"frameset.name.keyword": "asc"})

    query = {"bool": {"must": must, "filter": filters}}
    from_ = (page - 1) * size

    resp = await es.search(index="bike_products", query=query, sort=sort, from_=from_, size=size)
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
    products = cast(list[BikeProductORM], db.scalars(stmt).all())

    grouped = _group_products(products)

    return {"total": total, "items": grouped}


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
    siblings = cast(list[BikeProductORM], db.scalars(sibling_stmt).all())
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
        "source_url": product.source_url,
        "frameset": {
            "name": product.frameset.name,
            "material": product.frameset.material,
            "material_group": get_material_group(product.frameset.material),
            "size_label": product.frameset.size_label,
            "category": product.frameset.category,
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
