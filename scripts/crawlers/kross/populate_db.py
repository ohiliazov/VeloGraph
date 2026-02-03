import json
import re
from typing import Any, Dict

from loguru import logger
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.config import pg_settings
from app.core.models import Base, BikeGeometryORM, BikeMetaORM
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


def _extract_number(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        m = re.search(r"[-+]?\d+(?:[.,]\d+)?", val)
        if m:
            return float(m.group(0).replace(",", "."))
    raise ValueError(f"Cannot parse numeric value from: {val!r}")


def build_geometry_payload(specs: Dict[str, list[Any]], idx: int) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for src_key, dst_key in SPEC_KEYS_MAP.items():
        values = specs.get(src_key, [])
        value = values[idx] if idx < len(values) else None
        if value is None:
            raise ValueError(f"Missing required geometry value for '{src_key}' at index {idx}")
        num = _extract_number(value)
        # Cast numeric types to expected ORM field types
        if dst_key in {"head_tube_angle", "seat_tube_angle"}:
            payload[dst_key] = float(num)
        else:
            payload[dst_key] = int(round(num))
    return payload


if __name__ == "__main__":
    engine = create_engine(pg_settings.connection_string)
    # Development-only: ensure schema matches current ORM by recreating tables
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    extracted_jsons_dir = artifacts_dir / "kross" / "extracted_jsons"

    total_files = 0
    bikes_created = 0
    geometries_inserted = 0

    with Session(engine) as session:
        for item in extracted_jsons_dir.iterdir():
            total_files += 1
            data = json.loads(item.read_text(encoding="utf-8"))
            meta = data.get("meta", {})
            sizes = data.get("sizes", [])
            specs = data.get("specs", {})

            brand = "Kross"
            model_name = meta.get("model", "").strip()
            category = " / ".join(meta.get("categories", []))

            if not model_name:
                logger.warning("⚠️ Skipping file {}: missing model name in meta", item.name)
                continue

            # Get or create BikeMetaORM
            result = session.execute(
                select(BikeMetaORM).where(
                    BikeMetaORM.brand == brand,
                    BikeMetaORM.model_name == model_name,
                    BikeMetaORM.category == category,
                )
            ).scalar_one_or_none()

            if result is None:
                bike_meta = BikeMetaORM(
                    brand=brand,
                    model_name=model_name,
                    category=category,
                )
                session.add(bike_meta)
                session.flush()  # to get bike_meta.id
                bikes_created += 1
                logger.debug("🆕 Created BikeMeta: {} {} ({})", brand, model_name, category)
            else:
                bike_meta = result
                logger.debug("♻️ Updating BikeMeta: {} {} ({})", brand, model_name, category)

            # Replace all existing geometries for this bike to keep data in sync
            session.execute(delete(BikeGeometryORM).where(BikeGeometryORM.bike_meta_id == bike_meta.id))

            # Insert geometry rows per size
            for idx, size_label in enumerate(sizes):
                payload = build_geometry_payload(specs, idx)
                geom = BikeGeometryORM(
                    bike_meta=bike_meta,
                    size_label=size_label,
                    **payload,
                )
                session.add(geom)
                geometries_inserted += 1

        session.commit()
        logger.success(
            "✅ Done populating DB with Kross bike geometry: files={}, bikes_created={}, geometries_inserted={}",
            total_files,
            bikes_created,
            geometries_inserted,
        )
