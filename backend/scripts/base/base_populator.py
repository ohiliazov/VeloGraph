from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.models import BikeDefinitionORM, FrameDefinitionORM, GeometrySpecORM
from backend.utils.helpers import extract_number


class BaseBikePopulator:
    def __init__(self, brand_name: str, json_dir: Path):
        self.brand_name = brand_name
        self.json_dir = json_dir

    def populate_all(self, session: Session):
        """Populates all JSON files in the json_dir."""
        return self.populate_directory(session, self.json_dir)

    def populate_file(self, session: Session, json_path: Path):
        """Populates data from a single JSON file."""
        raise NotImplementedError

    def populate_directory(self, session: Session, json_dir: Path):
        """Populates all JSON files in a directory."""
        total_files = 0
        files = sorted(list(json_dir.glob("*.json")))
        logger.info(f"📁 Found {len(files)} JSON files to process for {self.brand_name}.")
        for item in files:
            total_files += 1
            try:
                self.populate_file(session, item)
                if total_files % 10 == 0:
                    session.commit()
                    logger.info(f"💾 Committed {total_files} files...")
            except Exception as e:
                logger.error(f"Error processing {item.name}: {e}")
                session.rollback()
        session.commit()
        return total_files


def normalize_label(label: str) -> str:
    return " ".join(str(label).strip().split())


def build_geometry_payload(specs: dict[str, list[Any]], idx: int, key_map: dict[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    # These fields are nullable in DB
    optional_dst_keys = {
        "top_tube_effective_mm",
        "seat_tube_length_mm",
        "head_tube_length_mm",
        "fork_offset_mm",
        "trail_mm",
        "standover_height_mm",
    }

    for src_key, dst_key in key_map.items():
        values = specs.get(src_key, [])
        value = values[idx] if idx < len(values) else None

        if value is None:
            if dst_key in optional_dst_keys:
                payload[dst_key] = None
                continue
            else:
                raise ValueError(f"Missing required geometry value for '{src_key}' at index {idx}")

        try:
            num = extract_number(value)
            if dst_key in {"head_tube_angle", "seat_tube_angle"}:
                payload[dst_key] = float(num)
            else:
                payload[dst_key] = round(num)
        except (ValueError, TypeError) as err:
            if dst_key in optional_dst_keys:
                payload[dst_key] = None
            else:
                raise ValueError(f"Invalid numeric value '{value}' for '{src_key}' at index {idx}") from err
    return payload


def get_or_create_family(session: Session, brand: str, family_name: str, category: str) -> BikeDefinitionORM:
    family = session.execute(
        select(BikeDefinitionORM).where(
            BikeDefinitionORM.brand_name == brand,
            BikeDefinitionORM.family_name == family_name,
        )
    ).scalar_one_or_none()

    if not family:
        family = BikeDefinitionORM(brand_name=brand, family_name=family_name, category=category)
        session.add(family)
        session.flush()
    return family


def get_or_create_definition(
    session: Session, family_id: int, name: str, material: str | None, year: int | None
) -> FrameDefinitionORM:
    frame_def = session.execute(
        select(FrameDefinitionORM).where(
            FrameDefinitionORM.family_id == family_id,
            FrameDefinitionORM.model_name == name,
            FrameDefinitionORM.material == material,
        )
    ).scalar_one_or_none()

    if not frame_def:
        frame_def = FrameDefinitionORM(
            family_id=family_id,
            name=name,
            material=material,
            year_start=year,
            year_end=year,
        )
        session.add(frame_def)
        session.flush()
    return frame_def


def get_or_create_geometry_spec(
    session: Session, definition_id: int, label: str, payload: dict[str, Any]
) -> GeometrySpecORM:
    norm_label = normalize_label(label)
    spec = session.execute(
        select(GeometrySpecORM).where(
            GeometrySpecORM.definition_id == definition_id,
            GeometrySpecORM.size_label == norm_label,
        )
    ).scalar_one_or_none()

    if not spec:
        spec = GeometrySpecORM(definition_id=definition_id, size_label=norm_label, **payload)
        session.add(spec)
        session.flush()
    else:
        # Verify if payload matches? For now we trust label uniqueness per definition.
        pass
    return spec
