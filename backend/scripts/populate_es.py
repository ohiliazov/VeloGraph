from elasticsearch import Elasticsearch, helpers
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import es_settings
from backend.core.constants import BIKE_PRODUCT_INDEX, FRAMESET_GEOMETRY_INDEX
from backend.core.db import SessionLocal
from backend.core.models import BikeProductORM
from backend.core.utils import get_material_group


def serialize_bike(product: BikeProductORM) -> dict:
    """Converts ORM object to ES Document Dictionary."""
    return {
        "_index": FRAMESET_GEOMETRY_INDEX,
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


def serialize_group(group_key: tuple, products: list[BikeProductORM]) -> dict:
    """Converts a group of products to an ES Document."""
    # group_key = (name, material, build_kit_id)
    rep = products[0]
    # Create a deterministic ID for the group
    group_id = f"{rep.frameset.name}-{rep.frameset.material}-{rep.build_kit_id}".replace(" ", "-").lower()

    return {
        "_index": BIKE_PRODUCT_INDEX,
        "_id": group_id,
        "_source": {
            "frameset_name": rep.frameset.name,
            "material": rep.frameset.material,
            "material_group": get_material_group(rep.frameset.material),
            "category": rep.frameset.category,
            "build_kit": {
                "name": rep.build_kit.name,
                "groupset": rep.build_kit.groupset,
                "wheelset": rep.build_kit.wheelset,
                "cockpit": rep.build_kit.cockpit,
                "tires": rep.build_kit.tires,
            },
            "skus": [p.sku for p in products],
            "product_ids": [p.id for p in products],
            "sizes": [p.frameset.size_label for p in products],
        },
    }


def create_index(es, index_name: str = FRAMESET_GEOMETRY_INDEX):
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


def create_group_index(es, index_name: str = BIKE_PRODUCT_INDEX):
    """Creates the group index with appropriate mapping."""
    mapping = {
        "mappings": {
            "properties": {
                "frameset_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "material": {"type": "keyword"},
                "material_group": {"type": "keyword"},
                "category": {"type": "keyword"},
                "skus": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "product_ids": {"type": "integer", "index": False},
                "sizes": {"type": "keyword", "index": False},
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


def populate_index(es, session):
    """Fetches all bikes from DB and pushes them to both ES indices."""
    logger.info("🔍 Fetching bike products from PostgreSQL...")

    stmt = select(BikeProductORM).options(
        selectinload(BikeProductORM.frameset),
        selectinload(BikeProductORM.build_kit),
    )

    products = session.scalars(stmt).all()
    logger.info(f"📊 Found {len(products)} products. Serializing for both indices...")

    groups = {}
    for p in products:
        key = (p.frameset.name, p.frameset.material, p.build_kit_id)
        if key not in groups:
            groups[key] = []
        groups[key].append(p)

    # Prepare Generator for Bulk Indexing
    def actions_generator():
        # Individual products
        for product in products:
            doc = serialize_bike(product)
            doc["_index"] = FRAMESET_GEOMETRY_INDEX
            yield doc
        # Groups
        for key, group_products in groups.items():
            doc = serialize_group(key, group_products)
            doc["_index"] = BIKE_PRODUCT_INDEX
            yield doc

    # Execute Bulk Index
    logger.info("🚀 Pushing to Elasticsearch...")
    success, failed = helpers.bulk(es, actions_generator(), stats_only=True)

    logger.info(f"🏁 Done! Successfully indexed: {success}, Failed: {failed}")
    return success, failed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Populate Elasticsearch index with bike data.")
    parser.add_argument("--url", type=str, default=es_settings.url, help="Elasticsearch URL")
    parser.add_argument("--index", type=str, default=FRAMESET_GEOMETRY_INDEX, help="Elasticsearch index name")
    parser.add_argument("--recreate", action="store_true", default=True, help="Recreate index if it exists")

    args = parser.parse_args()

    # 1. Connect to DB and ES
    es = Elasticsearch(args.url)

    if not es.ping():
        logger.error(f"❌ Could not connect to Elasticsearch at {args.url}!")
        return

    # 2. Reset Indices
    if args.recreate:
        create_index(es, FRAMESET_GEOMETRY_INDEX)
        create_group_index(es, BIKE_PRODUCT_INDEX)

    # 3. Fetch Data and Populate
    with SessionLocal() as session:
        populate_index(es, session)


if __name__ == "__main__":
    main()
