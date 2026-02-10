from elasticsearch import Elasticsearch, helpers
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import es_settings
from backend.core.constants import BIKE_PRODUCT_INDEX, FRAMESET_GEOMETRY_INDEX
from backend.core.db import SessionLocal
from backend.core.models import FrameDefinitionORM, GeometrySpecORM
from backend.core.utils import get_material_group


def serialize_spec(spec: GeometrySpecORM) -> dict:
    definition = spec.definition
    family = definition.family
    return {
        "_index": FRAMESET_GEOMETRY_INDEX,
        "_id": spec.id,
        "_source": {
            "id": spec.id,
            "geometry_spec": {
                "size_label": spec.size_label,
                "stack_mm": spec.stack_mm,
                "reach_mm": spec.reach_mm,
            },
            "definition": {
                "name": definition.name,
                "material": definition.material,
                "material_group": get_material_group(definition.material),
            },
            "family": {
                "brand_name": family.brand_name,
                "family_name": family.family_name,
                "category": family.category,
            },
        },
    }


def serialize_definition(definition: FrameDefinitionORM) -> dict:
    family = definition.family
    return {
        "_index": BIKE_PRODUCT_INDEX,
        "_id": definition.id,
        "_source": {
            "id": definition.id,
            "family": {
                "brand_name": family.brand_name,
                "family_name": family.family_name,
                "category": family.category,
            },
            "definition": {
                "name": definition.name,
                "material": definition.material,
                "material_group": get_material_group(definition.material),
            },
            "sizes": [s.size_label for s in definition.geometries],
        },
    }


def create_index(es, index_name: str = FRAMESET_GEOMETRY_INDEX):
    mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "geometry_spec": {
                    "properties": {
                        "size_label": {"type": "keyword"},
                        "stack_mm": {"type": "integer"},
                        "reach_mm": {"type": "integer"},
                    }
                },
                "definition": {
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "material": {"type": "keyword"},
                        "material_group": {"type": "keyword"},
                    }
                },
                "family": {
                    "properties": {
                        "brand_name": {"type": "keyword"},
                        "family_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "category": {"type": "keyword"},
                    }
                },
            }
        }
    }

    if es.indices.exists(index=index_name):
        logger.info(f"🗑️ Index '{index_name}' exists. Deleting to start fresh...")
        es.indices.delete(index=index_name)

    es.indices.create(index=index_name, body=mapping)
    logger.info(f"✅ Created index '{index_name}'.")


def create_group_index(es, index_name: str = BIKE_PRODUCT_INDEX):
    mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "family": {
                    "properties": {
                        "brand_name": {"type": "keyword"},
                        "family_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "category": {"type": "keyword"},
                    }
                },
                "definition": {
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "material": {"type": "keyword"},
                        "material_group": {"type": "keyword"},
                    }
                },
                "sizes": {"type": "keyword", "index": False},
            }
        }
    }

    if es.indices.exists(index=index_name):
        logger.info(f"🗑️ Index '{index_name}' exists. Deleting to start fresh...")
        es.indices.delete(index=index_name)

    es.indices.create(index=index_name, body=mapping)
    logger.info(f"✅ Created index '{index_name}'.")


def populate_index(es, session):
    logger.info("🔍 Fetching geometry specs and frame definitions from PostgreSQL...")

    spec_stmt = select(GeometrySpecORM).options(
        selectinload(GeometrySpecORM.definition).selectinload(FrameDefinitionORM.family)
    )
    specs = session.scalars(spec_stmt).all()
    logger.info(f"📐 Found {len(specs)} geometry specs. Serializing...")

    def_stmt = select(FrameDefinitionORM).options(
        selectinload(FrameDefinitionORM.family),
        selectinload(FrameDefinitionORM.geometries),
    )
    definitions = session.scalars(def_stmt).all()
    logger.info(f"🧱 Found {len(definitions)} frame definitions. Serializing groups...")

    def actions_generator():
        for spec in specs:
            yield serialize_spec(spec)
        for definition in definitions:
            yield serialize_definition(definition)

    logger.info("🚀 Pushing to Elasticsearch...")
    success, failed = helpers.bulk(es, actions_generator(), stats_only=True)

    logger.info(f"🏁 Done! Successfully indexed: {success}, Failed: {failed}")
    return success, failed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Populate Elasticsearch index with bike data.")
    parser.add_argument("--url", type=str, default=es_settings.url, help="Elasticsearch URL")
    parser.add_argument("--index", type=str, default=FRAMESET_GEOMETRY_INDEX, help="Elasticsearch index name")
    parser.add_argument("--recreate", action="store_true", default=False, help="Recreate index if it exists")

    args = parser.parse_args()

    es = Elasticsearch(args.url)

    if not es.ping():
        logger.error(f"❌ Could not connect to Elasticsearch at {args.url}!")
        return

    if args.recreate:
        create_index(es, FRAMESET_GEOMETRY_INDEX)
        create_group_index(es, BIKE_PRODUCT_INDEX)

    with SessionLocal() as session:
        populate_index(es, session)


if __name__ == "__main__":
    main()
