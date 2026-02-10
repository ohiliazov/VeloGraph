import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.core.db import SessionLocal
from backend.core.models import BikeFamilyORM, BikeProductORM
from backend.core.utils import get_simple_types
from backend.scripts.base.base_populator import (
    add_bike_product,
    build_geometry_payload,
    get_or_create_build_kit,
    get_or_create_definition,
    get_or_create_family,
    get_or_create_geometry_spec,
    normalize_label,
)
from backend.scripts.constants import artifacts_dir

SPEC_KEYS_MAP = {
    "stack": "stack_mm",
    "reach": "reach_mm",
    "TT": "top_tube_effective_mm",
    "ST": "seat_tube_length_mm",
    "HT": "head_tube_length_mm",
    "CS": "chainstay_length_mm",
    "HA": "head_tube_angle",
    "SA": "seat_tube_angle",
    "bb_drop": "bb_drop_mm",
    "WB": "wheelbase_mm",
}


def populate_from_json_data(session: Session, data: dict[str, Any], source_name: str, added_skus: set[str]):
    meta = data.get("meta", {})
    build_kit_data = data.get("build_kit", {})
    sizes = data.get("sizes", [])
    specs = data.get("specs", {})

    brand = "Kross"
    model_name = meta.get("model", "").strip()
    material = meta.get("material")
    categories = meta.get("categories", [])
    model_year = meta.get("model_year")

    category = get_simple_types(categories)[0] if categories else "other"
    colors_data = meta.get("colors", [])
    colors = [str(c.get("color")).strip() for c in colors_data if c.get("color")] or [None]

    family = get_or_create_family(session, brand, model_name, category)

    def_name = f"{model_name} {material or ''}".strip()
    frame_def = get_or_create_definition(session, family.id, def_name, material, model_year)
    build_kit = get_or_create_build_kit(session, build_kit_data)

    for idx, size_label in enumerate(sizes):
        try:
            payload = build_geometry_payload(specs, idx, SPEC_KEYS_MAP)
            norm_label = normalize_label(size_label)
            geometry_spec = get_or_create_geometry_spec(session, frame_def.id, norm_label, payload)

            sku_parts = [brand, model_name, str(model_year or ""), build_kit.name, norm_label]
            sku = "-".join(p.replace(" ", "-") for p in sku_parts if p).upper()

            add_bike_product(
                session=session,
                sku=sku,
                colors=[c for c in colors if c],
                spec_id=geometry_spec.id,
                bk_id=build_kit.id,
                source_url=meta.get("source_url"),
                added_skus=added_skus,
            )
        except Exception as e:
            logger.error(f"Failed to process {model_name} size {size_label}: {e}")


def populate_from_json(session: Session, json_path: Path, added_skus: set[str]):
    data = json.loads(json_path.read_text(encoding="utf-8"))
    populate_from_json_data(session, data, json_path.name, added_skus)


def populate_directory(session: Session, json_dir: Path):
    total_files = 0
    files = list(json_dir.glob("*.json"))
    added_skus: set[str] = set()
    logger.info(f"📁 Found {len(files)} JSON files to process.")
    for item in files:
        total_files += 1
        try:
            populate_from_json(session, item, added_skus)
            if total_files % 10 == 0:
                session.commit()
                logger.info(f"💾 Committed {total_files} files...")
        except Exception as e:
            logger.error(f"Error processing {item.name}: {e}")
            session.rollback()
    session.commit()
    return total_files


def populate_from_archive(session: Session, json_zip: Path):
    total_files = 0
    added_skus: set[str] = set()
    with zipfile.ZipFile(json_zip, "r") as z:
        json_files = [n for n in z.namelist() if n.endswith(".json")]
        logger.info(f"📦 Found {len(json_files)} JSON files in archive {json_zip.name}.")

        for json_name in json_files:
            total_files += 1
            try:
                data = json.loads(z.read(json_name).decode("utf-8"))
                populate_from_json_data(session, data, json_name, added_skus)
                if total_files % 10 == 0:
                    session.commit()
                    logger.info(f"💾 Committed {total_files} files...")
            except Exception as e:
                logger.error(f"Error processing {json_name}: {e}")
                session.rollback()

    session.commit()
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

    with SessionLocal() as session:
        logger.info("🗑️ Clearing existing 'Kross' products and families from database...")
        session.execute(delete(BikeProductORM).where(BikeProductORM.sku.like("KROSS-%")))
        session.execute(delete(BikeFamilyORM).where(BikeFamilyORM.brand_name == "Kross"))
        session.commit()

    with SessionLocal() as session:
        archive_input = args.input.with_suffix(".zip")
        if archive_input.exists():
            count = populate_from_archive(session, archive_input)
        elif args.input.exists():
            count = populate_directory(session, args.input)
        else:
            logger.error(f"❌ Input '{args.input}' (directory or zip) not found.")
            return

        session.commit()
        logger.success(f"✅ Done populating DB with Kross bike geometry: {count} files processed.")


if __name__ == "__main__":
    main()
