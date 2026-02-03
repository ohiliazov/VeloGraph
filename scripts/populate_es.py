from elasticsearch import Elasticsearch, helpers
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import es_settings
from app.core.db import SessionLocal
from app.core.models import BikeMetaORM

INDEX_NAME = "bikes"


def get_simple_type(category_str: str) -> str:
    """Normalizes messy categories into strict filter types."""
    if not category_str:
        return "other"

    cat = category_str.lower()

    if "gravel" in cat:
        return "gravel"
    if "mtb" in cat or "górskie" in cat:
        return "mtb"
    if "trekking" in cat:
        return "trekking"
    if "cross" in cat:
        return "cross"
    if "szosa" in cat or "road" in cat:
        return "road"
    if "miejskie" in cat or "city" in cat:
        return "city"
    if "dzieci" in cat or "kids" in cat or "junior" in cat:
        return "kids"

    return "other"


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
            "frame_material": bike.frame_material,
            "simple_type": get_simple_type(bike.category),  # Normalized
            "category_original": bike.category,  # Original for display
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


def create_index(es):
    """Creates the index with the correct mapping if it doesn't exist."""
    mapping = {
        "mappings": {
            "properties": {
                "brand": {"type": "text"},
                "model_name": {"type": "text"},
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

    if es.indices.exists(index=INDEX_NAME):
        logger.info(f"🗑️ Index '{INDEX_NAME}' exists. Deleting to start fresh...")
        es.indices.delete(index=INDEX_NAME)

    es.indices.create(index=INDEX_NAME, body=mapping)
    logger.info(f"✅ Created index '{INDEX_NAME}'.")


def main():
    # 1. Connect to DB and ES
    es = Elasticsearch(es_settings.url)

    if not es.ping():
        logger.error("❌ Could not connect to Elasticsearch!")
        return

    # 2. Reset Index
    create_index(es)

    # 3. Fetch Data (Optimized)
    with SessionLocal() as session:
        logger.info("🔍 Fetching bikes from PostgreSQL...")

        # selectinload is CRITICAL: it fetches all geometries in 1 extra query
        # instead of 1 query per bike (N+1 problem).
        stmt = select(BikeMetaORM).options(selectinload(BikeMetaORM.geometries))

        # If you have huge data (100k+), use yield_per or paging here.
        # For standard catalogs (e.g. <10k bikes), .all() is fine.
        bikes = session.scalars(stmt).all()
        logger.info(f"📊 Found {len(bikes)} bikes. Serializing...")

        # 4. Prepare Generator for Bulk Indexing
        actions = (serialize_bike(bike) for bike in bikes)

        # 5. Execute Bulk Index
        logger.info("🚀 Pushing to Elasticsearch...")
        success, failed = helpers.bulk(es, actions, stats_only=True)

        logger.info(f"🏁 Done! Successfully indexed: {success}, Failed: {failed}")


if __name__ == "__main__":
    main()
