from elasticsearch import Elasticsearch, helpers
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import es_settings
from backend.core.constants import BIKE_PRODUCT_INDEX, FRAMESET_GEOMETRY_INDEX
from backend.core.db import SessionLocal
from backend.core.models import BikeProductORM, FrameDefinitionORM, GeometrySpecORM
from backend.core.utils import get_material_group, group_bike_product


def serialize_bike(product: BikeProductORM) -> dict:
    spec = product.geometry_spec
    definition = spec.definition
    family = definition.family
    return {
        "_index": FRAMESET_GEOMETRY_INDEX,
        "_id": product.id,
        "_source": {
            "id": product.id,
            "sku": product.sku,
            "colors": product.colors,
            "source_url": product.source_url,
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
    rep = products[0]
    definition = rep.geometry_spec.definition
    family = definition.family
    group_id = f"{family.family_name}-{definition.name}-{rep.build_kit_id}".replace(" ", "-").lower()

    return {
        "_index": BIKE_PRODUCT_INDEX,
        "_id": group_id,
        "_source": group_bike_product(rep, products),
    }


def create_index(es, index_name: str = FRAMESET_GEOMETRY_INDEX):
    mapping = {
        "mappings": {
            "properties": {
                "sku": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "colors": {"type": "keyword"},
                "source_url": {"type": "keyword", "index": False},
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
    mapping = {
        "mappings": {
            "properties": {
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
    logger.info("🔍 Fetching bike products from PostgreSQL...")

    stmt = select(BikeProductORM).options(
        selectinload(BikeProductORM.geometry_spec)
        .selectinload(GeometrySpecORM.definition)
        .selectinload(FrameDefinitionORM.family),
        selectinload(BikeProductORM.build_kit),
    )

    products = session.scalars(stmt).all()
    logger.info(f"📊 Found {len(products)} products. Serializing for both indices...")

    groups = {}
    for p in products:
        definition = p.geometry_spec.definition
        family = definition.family
        key = (family.id, definition.id, p.build_kit_id)
        if key not in groups:
            groups[key] = []
        groups[key].append(p)

    def actions_generator():
        for product in products:
            doc = serialize_bike(product)
            doc["_index"] = FRAMESET_GEOMETRY_INDEX
            yield doc
        for key, group_products in groups.items():
            doc = serialize_group(key, group_products)
            doc["_index"] = BIKE_PRODUCT_INDEX
            yield doc

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
