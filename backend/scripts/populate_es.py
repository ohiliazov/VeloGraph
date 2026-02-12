from elasticsearch import Elasticsearch, helpers
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import es_settings
from backend.core.constants import BIKE_PRODUCT_INDEX, FRAMESET_GEOMETRY_INDEX
from backend.core.db import SessionLocal
from backend.core.models import BikeDefinitionORM, GeometrySpecORM
from backend.core.utils import get_material_group


def _recreate_index(es, name, settings, mapping):
    if es.indices.exists(index=name):
        es.indices.delete(index=name)
    es.indices.create(index=name, body={"settings": settings, "mappings": mapping["mappings"]})
    logger.info(f"✅ Recreated index: {name}")


def create_index(es, index_name: str = FRAMESET_GEOMETRY_INDEX):
    settings = {
        "analysis": {
            "analyzer": {
                "bike_name_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                }
            }
        }
    }
    mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "geometry_spec": {
                    "properties": {
                        "size_label": {"type": "keyword"},
                        "stack_mm": {"type": "integer"},  # Optimized for range queries
                        "reach_mm": {"type": "integer"},
                    }
                },
                "definition": {
                    "properties": {
                        # Change 'name' to 'model_name' to match your serialization
                        "model_name": {
                            "type": "text",
                            "analyzer": "bike_name_analyzer",
                            "fields": {"keyword": {"type": "keyword"}},
                        },
                        "material": {"type": "keyword"},
                        "material_group": {"type": "keyword"},
                    }
                },
                "family": {
                    "properties": {
                        "brand_name": {"type": "keyword"},
                        "family_name": {
                            "type": "text",
                            "analyzer": "bike_name_analyzer",
                            "fields": {"keyword": {"type": "keyword"}},
                        },
                        "category": {"type": "keyword"},
                    }
                },
            }
        }
    }

    _recreate_index(es, index_name, settings, mapping)


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
                        "model_name": {  # Fixed name to match serialize_definition
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword"}},
                        },
                        "material": {"type": "keyword"},
                        "material_group": {"type": "keyword"},
                    }
                },
                # Enabled keyword indexing for sizes to allow filtering
                "sizes": {"type": "keyword"},
            }
        }
    }
    _recreate_index(es, index_name, {}, mapping)


def serialize_spec(spec: GeometrySpecORM) -> dict:
    definition = spec.definition
    # Note: Using .brand_name/model_name directly from your ORM structure
    return {
        "_index": FRAMESET_GEOMETRY_INDEX,
        "_id": f"spec_{spec.id}",
        "_source": {
            "id": spec.id,
            "geometry_spec": {
                "size_label": spec.size_label,
                "stack_mm": int(spec.stack_mm),
                "reach_mm": int(spec.reach_mm),
            },
            "definition": {
                "model_name": definition.model_name,
                "material": definition.material,
                "material_group": get_material_group(definition.material),
            },
            "family": {
                "brand_name": definition.brand_name,
                "family_name": definition.model_name,  # Or family name if you add that table
                "category": definition.category,
            },
        },
    }


def serialize_definition(definition: BikeDefinitionORM) -> dict:
    return {
        "_index": BIKE_PRODUCT_INDEX,
        "_id": f"def_{definition.id}",
        "_source": {
            "id": definition.id,
            "family": {
                "brand_name": definition.brand_name,
                "family_name": definition.model_name,
                "category": definition.category,
            },
            "definition": {
                "model_name": definition.model_name,
                "material": definition.material,
                "material_group": get_material_group(definition.material),
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
        # Index individual geometry specs (for Fit Search)
        for spec in specs:
            yield serialize_spec(spec)

        # Index high-level bike definitions (for Catalog Search)
        for definition in definitions:
            yield serialize_definition(definition)

    logger.info("🚀 Pushing to Elasticsearch...")
    # chunk_size helps keep the request payload manageable
    success, failed = helpers.bulk(es, actions_generator(), chunk_size=500, stats_only=True)

    logger.success(f"🏁 Done! Successfully indexed: {success}, Failed: {failed}")
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
