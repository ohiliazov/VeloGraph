import argparse
import json
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.models import BikeGeometryORM, BikeMetaORM
from app.utils.helpers import extract_number
from scripts.constants import artifacts_dir

SPEC_KEYS_MAP = {
    "Stack": "stack",
    "Reach": "reach",
    "TT - efektywna długość górnej rury": "top_tube_effective_length",
    "ST - Długość rury podsiodłowej": "seat_tube_length",
    "HT - Długość główki ramy": "head_tube_length",
    "CS - Długość tylnych widełek": "chainstay_length",
    "HA - Kąt główki ramy": "head_tube_angle",
    "SA - Kąt rury podsiodłowej": "seat_tube_angle",
    "BBDROP": "bb_drop",
    "WB - Baza kół": "wheelbase",
}


def build_geometry_payload(specs: dict[str, list[Any]], idx: int) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for src_key, dst_key in SPEC_KEYS_MAP.items():
        values = specs.get(src_key, [])
        value = values[idx] if idx < len(values) else None
        if value is None:
            raise ValueError(f"Missing required geometry value for '{src_key}' at index {idx}")
        num = extract_number(value)
        # Cast numeric types to expected ORM field types
        if dst_key in {"head_tube_angle", "seat_tube_angle"}:
            payload[dst_key] = float(num)
        else:
            payload[dst_key] = round(num)
    return payload


def populate_from_json(session: Session, json_path: Path):
    """
    Populates the database with data from a single JSON file.
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    sizes = data.get("sizes", [])
    specs = data.get("specs", {})

    brand = "Kross"
    model_name = meta.get("model", "").strip()
    categories = meta.get("categories", [])
    model_year = meta.get("model_year")
    wheel_size = meta.get("wheel_size")

    if not model_name:
        logger.warning("⚠️ Skipping file {}: missing model name in meta", json_path.name)
        return

    # Get or create BikeMetaORM
    result = session.execute(
        select(BikeMetaORM).where(
            BikeMetaORM.brand == brand,
            BikeMetaORM.model_name == model_name,
        )
    ).scalar_one_or_none()

    if result is None:
        bike_meta = BikeMetaORM(
            brand=brand,
            model_name=model_name,
            categories=categories,
            model_year=model_year,
            wheel_size=str(wheel_size) if wheel_size else None,
        )
        session.add(bike_meta)
        session.flush()  # to get bike_meta.id
        logger.debug("🆕 Created BikeMeta: {} {} ({})", brand, model_name, categories)
    else:
        bike_meta = result
        bike_meta.categories = categories  # Update categories
        if model_year:
            bike_meta.model_year = model_year
        if wheel_size:
            bike_meta.wheel_size = str(wheel_size)
        logger.debug("♻️ Updating BikeMeta: {} {} ({})", brand, model_name, categories)

    # Replace all existing geometries for this bike to keep data in sync
    session.execute(delete(BikeGeometryORM).where(BikeGeometryORM.bike_meta_id == bike_meta.id))

    # Insert geometry rows per size
    for idx, size_label in enumerate(sizes):
        try:
            payload = build_geometry_payload(specs, idx)
            geom = BikeGeometryORM(
                bike_meta=bike_meta,
                size_label=size_label,
                **payload,
            )
            session.add(geom)
        except Exception as e:
            logger.error(f"Failed to build geometry for {model_name} size {size_label}: {e}")


def populate_directory(session: Session, json_dir: Path):
    """
    Processes all JSON files in a directory and populates the database.
    """
    total_files = 0
    for item in json_dir.glob("*.json"):
        total_files += 1
        populate_from_json(session, item)
    return total_files


def main():
    parser = argparse.ArgumentParser(description="Populate database with Kross bike data from JSON files.")
    parser.add_argument(
        "--input",
        type=Path,
        default=artifacts_dir / "kross" / "extracted_jsons",
        help="Directory containing extracted JSON files.",
    )

    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"❌ Input directory '{args.input}' not found.")
        return

    with SessionLocal() as session:
        count = populate_directory(session, args.input)
        session.commit()
        logger.success(f"✅ Done populating DB with Kross bike geometry: {count} files processed.")


if __name__ == "__main__":
    main()
