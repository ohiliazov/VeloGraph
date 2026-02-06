from elasticsearch import Elasticsearch, helpers
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import es_settings
from backend.core.db import SessionLocal
from backend.core.models import BikeProductORM
from backend.core.utils import get_material_group

INDEX_NAME = "bike_products"


def serialize_bike(product: BikeProductORM) -> dict:
    """Converts ORM object to ES Document Dictionary."""
    return {
        "_index": INDEX_NAME,
        "_id": product.id,
        "_source": {
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
                "cockpit": product.build_kit.cockpit,
                "tires": product.build_kit.tires,
            },
        },
    }


def create_index(es, index_name: str = INDEX_NAME):
    """Creates the index with the correct mapping if it doesn't exist."""
    mapping = {
        "mappings": {
            "properties": {
                "sku": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "colors": {"type": "keyword"},
                "source_url": {"type": "keyword", "index": False},
                "frameset": {
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "material": {"type": "keyword"},
                        "material_group": {"type": "keyword"},
                        "size_label": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "stack": {"type": "integer"},
                        "reach": {"type": "integer"},
                    }
                },
                "build_kit": {
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "groupset": {"type": "keyword"},
                        "wheelset": {"type": "keyword"},
                        "cockpit": {"type": "keyword"},
                        "tires": {"type": "keyword"},
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


def populate_index(es, session, index_name: str = INDEX_NAME):
    """Fetches all bikes from DB and pushes them to ES."""
    logger.info(f"🔍 Fetching bike products from PostgreSQL for index '{index_name}'...")

    stmt = select(BikeProductORM).options(
        selectinload(BikeProductORM.frameset),
        selectinload(BikeProductORM.build_kit),
    )

    products = session.scalars(stmt).all()
    logger.info(f"📊 Found {len(products)} products. Serializing...")

    # Prepare Generator for Bulk Indexing
    def actions_generator():
        for product in products:
            doc = serialize_bike(product)
            doc["_index"] = index_name
            yield doc

    # Execute Bulk Index
    logger.info(f"🚀 Pushing to Elasticsearch index '{index_name}'...")
    success, failed = helpers.bulk(es, actions_generator(), stats_only=True)

    logger.info(f"🏁 Done! Successfully indexed: {success}, Failed: {failed}")
    return success, failed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Populate Elasticsearch index with bike data.")
    parser.add_argument("--url", type=str, default=es_settings.url, help="Elasticsearch URL")
    parser.add_argument("--index", type=str, default=INDEX_NAME, help="Elasticsearch index name")
    parser.add_argument("--recreate", action="store_true", default=True, help="Recreate index if it exists")

    args = parser.parse_args()

    # 1. Connect to DB and ES
    es = Elasticsearch(args.url)

    if not es.ping():
        logger.error(f"❌ Could not connect to Elasticsearch at {args.url}!")
        return

    # 2. Reset Index
    if args.recreate:
        create_index(es, args.index)

    # 3. Fetch Data and Populate
    with SessionLocal() as session:
        populate_index(es, session, args.index)


if __name__ == "__main__":
    main()
