import argparse
import json
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.core.db import SessionLocal
from backend.core.models import BikeGeometryORM, BikeMetaORM
from backend.scripts.constants import artifacts_dir
from backend.utils.helpers import extract_number

# Normalize wheel size values to BSD string codes used by FE
INCH_TO_BSD: dict[float, str] = {
    12.0: "203",
    14.0: "254",
    16.0: "305",
    20.0: "406",
    24.0: "507",
    26.0: "559",
    27.5: "584",
    28.0: "700",  # many 28" are 622 BSD
    29.0: "700",  # marketing 29" -> 622 BSD
}
BSD_SET = {"700", "584", "559", "507", "406", "305", "254", "203"}


def normalize_wheel_size(ws: Any) -> str | None:
    """Return BSD code as string (e.g., "254"), or None if cannot normalize.

    Accepts values like 14, 14.0, "14.0", '14"', or already BSD codes as strings.
    """
    if ws is None:
        return None
    s = str(ws).strip().replace('"', "")
    # If it's already a known BSD code, return as-is
    if s in BSD_SET:
        return s
    try:
        v = float(s)
    except ValueError:
        # Not a float, return None to avoid storing bad values
        return None
    return INCH_TO_BSD.get(v)


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
    color = meta.get("color")

    brand = "Kross"
    model_name = meta.get("model", "").strip()
    color = str(meta.get("color")).strip() if meta.get("color") else None
    categories = meta.get("categories", [])
    model_year = meta.get("model_year")
    wheel_size_raw = meta.get("wheel_size")
    wheel_size = normalize_wheel_size(wheel_size_raw)
    max_tire_width = meta.get("max_tire_width")
    # Prefer explicit source_url, fallback to Open Graph URL if available
    source_url = meta.get("source_url") or meta.get("og:url")

    if not model_name:
        logger.warning("⚠️ Skipping file {}: missing model name in meta", json_path.name)
        return

    # Get or create BikeMetaORM
    result = session.execute(
        select(BikeMetaORM).where(
            BikeMetaORM.brand == brand,
            BikeMetaORM.model_name == model_name,
            BikeMetaORM.color == color,
        )
    ).scalar_one_or_none()

    if result is None:
        bike_meta = BikeMetaORM(
            brand=brand,
            model_name=model_name,
            color=color,
            categories=categories,
            model_year=model_year,
            wheel_size=wheel_size,
            source_url=source_url,
            max_tire_width=str(max_tire_width) if max_tire_width else None,
        )
        session.add(bike_meta)
        session.flush()  # to get bike_meta.id
        logger.debug("🆕 Created BikeMeta: {} {} {} ({})", brand, model_name, color, categories)
    else:
        bike_meta = result
        bike_meta.categories = categories  # Update categories
        if model_year:
            bike_meta.model_year = model_year
        if color:
            bike_meta.color = color
        if wheel_size:
            bike_meta.wheel_size = str(wheel_size)
        if source_url:
            bike_meta.source_url = source_url
        if max_tire_width:
            bike_meta.max_tire_width = str(max_tire_width)
        logger.debug("♻️ Updating BikeMeta: {} {} {} ({})", brand, model_name, color, categories)

    # Load existing geometries to avoid duplicates across files/colors
    existing_geoms = (
        session.execute(select(BikeGeometryORM).where(BikeGeometryORM.bike_meta_id == bike_meta.id)).scalars().all()
    )

    # Map (size_label, specs_tuple) -> BikeGeometryORM to allow color merging
    def get_specs_tuple(g):
        return (
            g.stack,
            g.reach,
            g.top_tube_effective_length,
            g.seat_tube_length,
            g.head_tube_length,
            g.chainstay_length,
            g.head_tube_angle,
            g.seat_tube_angle,
            g.bb_drop,
            g.wheelbase,
        )

    geoms_map: dict[tuple[str, tuple], BikeGeometryORM] = {
        (g.size_label, get_specs_tuple(g)): g for g in existing_geoms
    }

    def normalize_label(label: str) -> str:
        return " ".join(str(label).strip().split())

    for idx, size_label in enumerate(sizes):
        norm_label = normalize_label(size_label)

        try:
            payload = build_geometry_payload(specs, idx)
            specs_key = tuple(
                payload.get(k)
                for k in (
                    "stack",
                    "reach",
                    "top_tube_effective_length",
                    "seat_tube_length",
                    "head_tube_length",
                    "chainstay_length",
                    "head_tube_angle",
                    "seat_tube_angle",
                    "bb_drop",
                    "wheelbase",
                )
            )

            key = (norm_label, specs_key)
            if key in geoms_map:
                # Geometry already exists for this bike (now bike is brand+model+color)
                pass
            else:
                geom = BikeGeometryORM(
                    bike_meta=bike_meta,
                    size_label=norm_label,
                    **payload,
                )
                session.add(geom)
                geoms_map[key] = geom
                logger.debug(
                    "🆕 Added geometry for %s size %s",
                    model_name,
                    norm_label,
                )
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
        # Clear existing Kross bikes before repopulating
        logger.info("🗑️ Clearing existing 'Kross' bikes from database...")
        session.execute(delete(BikeMetaORM).where(BikeMetaORM.brand == "Kross"))
        session.flush()

        count = populate_directory(session, args.input)
        session.commit()
        logger.success(f"✅ Done populating DB with Kross bike geometry: {count} files processed.")


if __name__ == "__main__":
    main()
