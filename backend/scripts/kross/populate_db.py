import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.core.db import SessionLocal
from backend.core.models import BikeProductORM, BuildKitORM, FramesetORM
from backend.core.utils import get_simple_types
from backend.scripts.constants import artifacts_dir
from backend.utils.helpers import extract_number

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


def populate_from_json_data(session: Session, data: dict[str, Any], source_name: str):
    """
    Populates the database with data from a JSON-like dictionary.
    """
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

    # Get all colors to process from the new 'colors' field.
    colors_data = meta.get("colors", [])
    colors = [str(c.get("color")).strip() for c in colors_data] if colors_data else [None]

    if not model_name:
        logger.warning("⚠️ Skipping {}: missing model name in meta", source_name)
        return

    # 1. Get or create BuildKit
    bk_name = build_kit_data.get("name") or "Standard Build"
    build_kit = session.execute(
        select(BuildKitORM).where(
            BuildKitORM.name == bk_name,
            BuildKitORM.groupset == build_kit_data.get("groupset"),
            BuildKitORM.wheelset == build_kit_data.get("wheelset"),
            BuildKitORM.cockpit == build_kit_data.get("cockpit"),
            BuildKitORM.tires == build_kit_data.get("tires"),
        )
    ).scalar_one_or_none()

    if not build_kit:
        build_kit = BuildKitORM(
            name=bk_name,
            groupset=build_kit_data.get("groupset"),
            wheelset=build_kit_data.get("wheelset"),
            cockpit=build_kit_data.get("cockpit"),
            tires=build_kit_data.get("tires"),
        )
        session.add(build_kit)
        session.flush()

    def normalize_label(label: str) -> str:
        return " ".join(str(label).strip().split())

    # Use a local cache for SKUs added in this SESSION to avoid DB roundtrips and flush errors
    added_skus: set[str] = set()

    # 2. Process each size
    for idx, size_label in enumerate(sizes):
        norm_label = normalize_label(size_label)

        try:
            payload = build_geometry_payload(specs, idx)

            # 3. Get or create Frameset (with embedded geometry)
            fs_name = f"{brand} {model_name}"
            frameset = session.execute(
                select(FramesetORM).where(
                    FramesetORM.name == fs_name,
                    FramesetORM.material == material,
                    FramesetORM.size_label == norm_label,
                    FramesetORM.stack == payload["stack"],
                    FramesetORM.reach == payload["reach"],
                    FramesetORM.top_tube_effective_length == payload["top_tube_effective_length"],
                    FramesetORM.seat_tube_length == payload["seat_tube_length"],
                    FramesetORM.head_tube_length == payload["head_tube_length"],
                    FramesetORM.chainstay_length == payload["chainstay_length"],
                    FramesetORM.head_tube_angle == payload["head_tube_angle"],
                    FramesetORM.seat_tube_angle == payload["seat_tube_angle"],
                    FramesetORM.bb_drop == payload["bb_drop"],
                    FramesetORM.wheelbase == payload["wheelbase"],
                )
            ).scalar_one_or_none()

            if not frameset:
                frameset = FramesetORM(
                    name=fs_name, material=material, category=category, size_label=norm_label, **payload
                )
                session.add(frameset)
                session.flush()

            # 4. Create BikeProduct with color list
            unique_colors = sorted(list(set(colors)))
            # SKU = Brand-Model-Year-BuildKit-Size
            sku_parts = [brand, model_name, str(model_year or ""), bk_name, norm_label]
            sku = "-".join(p.replace(" ", "-") for p in sku_parts if p).upper()

            final_sku = sku
            if final_sku in added_skus:
                # Try to find a unique one
                suffix = 1
                while f"{final_sku}-{suffix}" in added_skus:
                    suffix += 1
                final_sku = f"{final_sku}-{suffix}"

            # Double check DB
            existing_product = session.execute(
                select(BikeProductORM).where(BikeProductORM.sku == final_sku)
            ).scalar_one_or_none()

            if not existing_product:
                product = BikeProductORM(
                    sku=final_sku,
                    colors=unique_colors,
                    frameset_id=frameset.id,
                    build_kit_id=build_kit.id,
                    source_url=meta.get("source_url"),
                )
                session.add(product)
                added_skus.add(final_sku)
                logger.debug("🆕 Added BikeProduct: {} (Colors: {})", final_sku, unique_colors)
            else:
                added_skus.add(final_sku)
                logger.warning("⚠️ SKU already exists in DB: {}", final_sku)

        except Exception as e:
            logger.error(f"Failed to process {model_name} size {size_label}: {e}")


def populate_from_json(session: Session, json_path: Path):
    """
    Populates the database with data from a single JSON file.
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    populate_from_json_data(session, data, json_path.name)


def populate_directory(session: Session, json_dir: Path):
    """
    Processes all JSON files in a directory and populates the database.
    """
    total_files = 0
    files = list(json_dir.glob("*.json"))
    logger.info(f"📁 Found {len(files)} JSON files to process.")
    for item in files:
        total_files += 1
        try:
            populate_from_json(session, item)
            if total_files % 10 == 0:
                session.commit()
                logger.info(f"💾 Committed {total_files} files...")
        except Exception as e:
            logger.error(f"Error processing {item.name}: {e}")
            session.rollback()
    session.commit()
    return total_files


def populate_from_archive(session: Session, json_zip: Path):
    """
    Processes all JSON files in a zip archive and populates the database.
    """
    total_files = 0
    with zipfile.ZipFile(json_zip, "r") as z:
        json_files = [n for n in z.namelist() if n.endswith(".json")]
        logger.info(f"📦 Found {len(json_files)} JSON files in archive {json_zip.name}.")

        for json_name in json_files:
            total_files += 1
            try:
                data = json.loads(z.read(json_name).decode("utf-8"))
                populate_from_json_data(session, data, json_name)
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

    # Clear existing Kross bikes before repopulating
    with SessionLocal() as session:
        logger.info("🗑️ Clearing existing 'Kross' products and framesets from database...")
        # Order matters for foreign keys
        session.execute(delete(BikeProductORM).where(BikeProductORM.sku.like("KROSS-%")))
        session.execute(delete(FramesetORM).where(FramesetORM.name.like("Kross %")))
        session.commit()

    with SessionLocal() as session:
        # Priority to archive if it exists
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
