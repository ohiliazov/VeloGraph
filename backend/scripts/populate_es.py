from elasticsearch import Elasticsearch, helpers
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import es_settings
from core.db import SessionLocal
from core.elasticsearch import (
    BIKE_INDEX_MAPPING,
    BIKE_INDEX_NAME,
    GEOMETRY_INDEX_MAPPING,
    GEOMETRY_INDEX_NAME,
    GEOMETRY_INDEX_SETTINGS,
)
from core.models import BikeDefinitionORM, GeometrySpecORM
from core.utils import get_bike_categories, get_material_group


def create_index(es: Elasticsearch, name: str, mapping: dict, settings: dict | None = None):
    if es.indices.exists(index=name):
        es.indices.delete(index=name)
        logger.info(f"✅ Deleted index: {name}")
    es.indices.create(index=name, body={"settings": settings or {}, "mappings": mapping["mappings"]})
    logger.info(f"✅ Recreated index: {name}")


def serialize_spec(spec: GeometrySpecORM) -> dict:
    return {
        "_index": GEOMETRY_INDEX_NAME,
        "_id": f"spec_{spec.id}",
        "_source": {
            "id": spec.id,
            "geometry_spec": {
                "size_label": spec.size_label,
                "stack_mm": int(spec.stack_mm),
                "reach_mm": int(spec.reach_mm),
            },
            "definition": {
                "brand_name": spec.definition.brand_name,
                "model_name": spec.definition.model_name,
                "category": get_bike_categories(spec.definition.category),
                "material": get_material_group(spec.definition.material),
            },
        },
    }


def serialize_definition(definition: BikeDefinitionORM) -> dict:
    return {
        "_index": BIKE_INDEX_NAME,
        "_id": f"def_{definition.id}",
        "_source": {
            "id": definition.id,
            "definition": {
                "brand_name": definition.brand_name,
                "category": get_bike_categories(definition.category),
                "model_name": definition.model_name,
                "material": get_material_group(definition.material),
            },
            "sizes": [s.size_label for s in definition.geometries],
        },
    }


def populate_index(es, session):
    logger.info("🔍 Fetching data from PostgreSQL...")

    # 1. Fetch Specs with Definition loaded (no .family, as per your ORM)
    spec_stmt = select(GeometrySpecORM).options(selectinload(GeometrySpecORM.definition))
    specs = session.scalars(spec_stmt).all()
    logger.info(f"📐 Found {len(specs)} geometry specs.")

    # 2. Fetch Definitions with Geometries loaded
    def_stmt = select(BikeDefinitionORM).options(selectinload(BikeDefinitionORM.geometries))
    definitions = session.scalars(def_stmt).all()
    logger.info(f"🧱 Found {len(definitions)} bike definitions.")

    def actions_generator():
        for spec in specs:
            yield serialize_spec(spec)
            print(".", end="")

        for definition in definitions:
            yield serialize_definition(definition)
            print(".", end="")
        print()

    logger.info("🚀 Pushing to Elasticsearch...")
    success, failed = helpers.bulk(es, actions_generator(), chunk_size=500, stats_only=True)

    logger.success(f"🏁 Done! Successfully indexed: {success}, Failed: {failed}")
    return success, failed


if __name__ == "__main__":
    es = Elasticsearch(es_settings.url)

    if not es.ping():
        logger.error(f"❌ Connection failed: {es_settings.url}")
        exit(1)

    create_index(es, BIKE_INDEX_NAME, BIKE_INDEX_MAPPING)
    create_index(es, GEOMETRY_INDEX_NAME, GEOMETRY_INDEX_MAPPING, GEOMETRY_INDEX_SETTINGS)

    with SessionLocal() as session:
        try:
            populate_index(es, session)
        except Exception as e:
            logger.exception(f"🚨 Population failed: {e}")
