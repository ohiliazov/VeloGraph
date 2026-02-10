import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.core.db import SessionLocal
from backend.core.models import BikeFamilyORM
from backend.core.utils import get_simple_types
from backend.scripts.base.base_populator import (
    BaseBikePopulator,
    build_geometry_payload,
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


class TrekBikePopulator(BaseBikePopulator):
    def __init__(self, json_dir: Path | None = None):
        brand_name = "trek"
        json_dir = json_dir or (artifacts_dir / brand_name / "extracted_jsons")
        super().__init__(brand_name="Trek", json_dir=json_dir)

    def populate_file(self, session: Session, json_path: Path):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self.populate_from_json_data(session, data, json_path.name)

    def populate_from_json_data(self, session: Session, data: dict[str, Any], source_name: str):
        meta = data.get("meta", {})
        sizes = data.get("sizes", [])
        specs = data.get("specs", {})

        brand = "Trek"
        model_name = meta.get("model", "").strip()
        frame_name = meta.get("frame_name")
        material = meta.get("material")
        categories = meta.get("categories", [])
        model_year = meta.get("model_year")

        category = get_simple_types(categories)[0] if categories else "other"

        # Use frame_name if available to determine the family more accurately
        # but still use the broad family name (e.g. Madone) if possible.
        # Actually, Trek's family is usually the first part of the frame name.
        family_base = model_name.split()[0] if model_name else "Other"
        family = get_or_create_family(session, brand, family_base, category)

        # The frame definition name can be the specific frame series (e.g. Madone SL)
        def_name = (frame_name if frame_name else model_name).strip()
        frame_def = get_or_create_definition(session, family.id, def_name, material, model_year)

        for idx, size_label in enumerate(sizes):
            try:
                payload = build_geometry_payload(specs, idx, SPEC_KEYS_MAP)
                norm_label = normalize_label(size_label)
                _ = get_or_create_geometry_spec(session, frame_def.id, norm_label, payload)
            except Exception as e:
                logger.error(f"Failed to process {model_name} size {size_label}: {e}")

    def populate_from_archive(self, session: Session, json_zip: Path):
        total_files = 0
        with zipfile.ZipFile(json_zip, "r") as z:
            json_files = [n for n in z.namelist() if n.endswith(".json")]
            logger.info(f"📦 Found {len(json_files)} JSON files in archive {json_zip.name}.")

            for json_name in json_files:
                total_files += 1
                try:
                    data = json.loads(z.read(json_name).decode("utf-8"))
                    self.populate_from_json_data(session, data, json_name)
                    if total_files % 10 == 0:
                        session.commit()
                        logger.info(f"💾 Committed {total_files} files...")
                except Exception as e:
                    logger.error(f"Error processing {json_name}: {e}")
                    session.rollback()

        session.commit()
        return total_files


def main():
    parser = argparse.ArgumentParser(description="Populate database with Trek bike data from JSON files.")
    parser.add_argument(
        "--input",
        type=Path,
        default=artifacts_dir / "trek" / "extracted_jsons",
        help="Directory containing extracted JSON files.",
    )

    args = parser.parse_args()
    populator = TrekBikePopulator(json_dir=args.input)

    with SessionLocal() as session:
        logger.info("🗑️ Clearing existing 'Trek' families from database...")
        session.execute(delete(BikeFamilyORM).where(BikeFamilyORM.brand_name == "Trek"))
        session.commit()

    with SessionLocal() as session:
        archive_input = args.input.with_suffix(".zip")
        if archive_input.exists():
            count = populator.populate_from_archive(session, archive_input)
        elif args.input.exists():
            count = populator.populate_all(session)
        else:
            logger.error(f"❌ Input '{args.input}' (directory or zip) not found.")
            return

        session.commit()
        logger.success(f"✅ Done populating DB with Trek bike geometry: {count} files processed.")


if __name__ == "__main__":
    main()
