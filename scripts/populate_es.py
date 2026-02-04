from elasticsearch import Elasticsearch, helpers
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import es_settings
from app.core.db import SessionLocal
from app.core.models import BikeMetaORM
from app.core.utils import get_simple_types

INDEX_NAME = "bikes"


def serialize_bike(bike) -> dict:
    """Converts ORM object to ES Document Dictionary."""
    return {
        "_index": INDEX_NAME,  # Required for bulk helper
        "_id": bike.id,  # Use DB ID as ES ID
        "_source": {
            "id": bike.id,
            "brand": bike.brand,
            "model_name": bike.model_name,
            "model_year": bike.model_year,
            "color": bike.color,
            "frame_material": bike.frame_material,
            "source_url": bike.source_url,
            "max_tire_width": bike.max_tire_width,
            "simple_type": get_simple_types(bike.categories),  # Normalized list
            "category_original": " / ".join(bike.categories),  # For display
            # Nested Geometries
            "geometries": [
                {
                    "size_label": geo.size_label,
                    "stack": geo.stack,
                    "reach": geo.reach,
                    "top_tube_effective_length": geo.top_tube_effective_length,
                    "seat_tube_length": geo.seat_tube_length,
                    "head_tube_angle": geo.head_tube_angle,
                    "seat_tube_angle": geo.seat_tube_angle,
                    "wheelbase": geo.wheelbase,
                }
                for geo in bike.geometries
            ],
        },
    }


def create_index(es, index_name: str = INDEX_NAME):
    """Creates the index with the correct mapping if it doesn't exist."""
    mapping = {
        "mappings": {
            "properties": {
                "brand": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "model_name": {"type": "text"},
                "color": {"type": "keyword"},
                "source_url": {"type": "keyword", "index": False},
                "max_tire_width": {"type": "keyword", "index": False},
                "simple_type": {"type": "keyword"},  # FAST filtering
                "model_year": {"type": "integer"},
                "geometries": {
                    "type": "nested",  # Crucial for accurate size searching
                    "properties": {
                        "size_label": {"type": "keyword"},
                        "stack": {"type": "integer"},
                        "reach": {"type": "integer"},
                        "top_tube_effective_length": {"type": "integer"},
                        "seat_tube_length": {"type": "integer"},
                        "head_tube_angle": {"type": "float"},
                        "seat_tube_angle": {"type": "float"},
                        "wheelbase": {"type": "integer"},
                    },
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
    logger.info(f"🔍 Fetching bikes from PostgreSQL for index '{index_name}'...")

    # selectinload is CRITICAL: it fetches all geometries in 1 extra query
    # instead of 1 query per bike (N+1 problem).
    stmt = select(BikeMetaORM).options(selectinload(BikeMetaORM.geometries))

    bikes = session.scalars(stmt).all()
    logger.info(f"📊 Found {len(bikes)} bikes. Serializing...")

    # Prepare Generator for Bulk Indexing
    def actions_generator():
        for bike in bikes:
            doc = serialize_bike(bike)
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
