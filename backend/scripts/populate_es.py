import time

from elasticsearch import Elasticsearch, helpers
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import es_settings
from core.db import SessionLocal
from core.elasticsearch import BIKE_INDEX_BODY, BIKE_INDEX_NAME, GEOMETRY_INDEX_BODY, GEOMETRY_INDEX_NAME
from core.models import BikeDefinitionORM, GeometrySpecORM
from core.utils import get_bike_categories, get_material_group


def wait_for_elasticsearch(es: Elasticsearch, timeout: int = 60):
    """Retries connection until ES is ready (essential for Docker)."""
    start = time.time()
    while time.time() - start < timeout:
        if es.ping():
            logger.info("✅ Connected to Elasticsearch")
            return True
        logger.warning("⏳ Waiting for Elasticsearch to start...")
        time.sleep(2)
    return False


def create_index(es: Elasticsearch, name: str, body: dict):
    if es.indices.exists(index=name):
        es.indices.delete(index=name)
        logger.info(f"🗑️ Deleted existing index: {name}")
    es.indices.create(index=name, body=body)
    logger.info(f"✨ Created index: {name}")


def serialize_spec(spec: GeometrySpecORM) -> dict:
    # Safety check: Handle None values for integer fields
    stack = int(spec.stack_mm) if spec.stack_mm is not None else 0
    reach = int(spec.reach_mm) if spec.reach_mm is not None else 0

    return {
        "_index": GEOMETRY_INDEX_NAME,
        "_id": spec.id,
        "_source": {
            "id": spec.id,
            "geometry_spec": {
                "size_label": spec.size_label,
                "stack_mm": stack,
                "reach_mm": reach,
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
        "_id": definition.id,
        "_source": {
            "id": definition.id,
            "definition": {
                "brand_name": definition.brand_name,
                "model_name": definition.model_name,
                "category": get_bike_categories(definition.category),
                "material": get_material_group(definition.material),
            },
            "sizes": [s.size_label for s in definition.geometries],
        },
    }


def actions_generator(session):
    """Generator that yields actions for bulk indexing."""

    # 1. Stream Specs
    # execution_options({"yield_per": 100}) ensures we fetch in batches
    logger.info("Streaming Geometry Specs...")
    spec_stmt = (
        select(GeometrySpecORM).options(selectinload(GeometrySpecORM.definition)).execution_options(yield_per=100)
    )
    for spec in session.scalars(spec_stmt):
        yield serialize_spec(spec)

    # 2. Stream Definitions
    logger.info("Streaming Bike Definitions...")
    def_stmt = (
        select(BikeDefinitionORM).options(selectinload(BikeDefinitionORM.geometries)).execution_options(yield_per=100)
    )
    for definition in session.scalars(def_stmt):
        yield serialize_definition(definition)


def populate_index(es, session):
    logger.info("🚀 Starting bulk upload...")

    # Use the generator directly in the bulk helper
    success, failed = helpers.bulk(
        es,
        actions_generator(session),
        chunk_size=500,
        stats_only=True,
        raise_on_error=False,  # Don't stop the whole process if one doc fails
    )

    logger.success(f"🏁 Done! Successfully indexed: {success}, Failed: {failed}")
    return success, failed


if __name__ == "__main__":
    es = Elasticsearch(es_settings.url)

    if not wait_for_elasticsearch(es):
        logger.error(f"❌ Could not connect to {es_settings.url}")
        exit(1)

    create_index(es, BIKE_INDEX_NAME, BIKE_INDEX_BODY)
    create_index(es, GEOMETRY_INDEX_NAME, GEOMETRY_INDEX_BODY)

    with SessionLocal() as session:
        try:
            populate_index(es, session)
        except Exception as e:
            logger.exception(f"🚨 Population failed: {e}")
            exit(1)
