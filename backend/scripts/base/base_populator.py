from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.models import BikeFamilyORM, BikeProductORM, BuildKitORM, FrameDefinitionORM, GeometrySpecORM
from backend.utils.helpers import extract_number


def normalize_label(label: str) -> str:
    return " ".join(str(label).strip().split())


def build_geometry_payload(specs: dict[str, list[Any]], idx: int, key_map: dict[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for src_key, dst_key in key_map.items():
        values = specs.get(src_key, [])
        value = values[idx] if idx < len(values) else None
        if value is None:
            raise ValueError(f"Missing required geometry value for '{src_key}' at index {idx}")
        num = extract_number(value)
        if dst_key in {"head_tube_angle", "seat_tube_angle"}:
            payload[dst_key] = float(num)
        else:
            payload[dst_key] = round(num)
    return payload


def get_or_create_family(session: Session, brand: str, family_name: str, category: str) -> BikeFamilyORM:
    family = session.execute(
        select(BikeFamilyORM).where(
            BikeFamilyORM.brand_name == brand,
            BikeFamilyORM.family_name == family_name,
        )
    ).scalar_one_or_none()

    if not family:
        family = BikeFamilyORM(brand_name=brand, family_name=family_name, category=category)
        session.add(family)
        session.flush()
    return family


def get_or_create_definition(
    session: Session, family_id: int, name: str, material: str | None, year: int | None
) -> FrameDefinitionORM:
    frame_def = session.execute(
        select(FrameDefinitionORM).where(
            FrameDefinitionORM.family_id == family_id,
            FrameDefinitionORM.name == name,
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


def get_or_create_build_kit(session: Session, data: dict[str, Any]) -> BuildKitORM:
    name = data.get("name") or "Standard Build"
    groupset = data.get("groupset")
    wheelset = data.get("wheelset")
    cockpit = data.get("cockpit")
    tires = data.get("tires")

    build_kit = session.execute(
        select(BuildKitORM).where(
            BuildKitORM.name == name,
            BuildKitORM.groupset == groupset,
            BuildKitORM.wheelset == wheelset,
            BuildKitORM.cockpit == cockpit,
            BuildKitORM.tires == tires,
        )
    ).scalar_one_or_none()

    if not build_kit:
        build_kit = BuildKitORM(
            name=name,
            groupset=groupset,
            wheelset=wheelset,
            cockpit=cockpit,
            tires=tires,
        )
        session.add(build_kit)
        session.flush()
    return build_kit


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


def add_bike_product(
    session: Session,
    sku: str,
    colors: list[str],
    spec_id: int,
    bk_id: int,
    source_url: str | None,
    added_skus: set[str],
):
    # Check by Unique constraint (Geometry + BuildKit)
    existing = session.execute(
        select(BikeProductORM).where(BikeProductORM.geometry_spec_id == spec_id, BikeProductORM.build_kit_id == bk_id)
    ).scalar_one_or_none()

    if existing:
        # Merge colors
        new_colors = set(existing.colors or [])
        new_colors.update(colors)
        existing.colors = sorted(list(new_colors))
        logger.debug("🔄 Merged colors for existing product: {}", existing.sku)
        return existing

    # Check by SKU
    final_sku = sku
    if final_sku in added_skus:
        suffix = 1
        while f"{final_sku}-{suffix}" in added_skus:
            suffix += 1
        final_sku = f"{final_sku}-{suffix}"

    product = BikeProductORM(
        sku=final_sku,
        colors=sorted(list(set(colors))),
        geometry_spec_id=spec_id,
        build_kit_id=bk_id,
        source_url=source_url,
    )
    session.add(product)
    session.flush()
    added_skus.add(final_sku)
    logger.debug("🆕 Added BikeProduct: {}", final_sku)
    return product
