from pathlib import Path

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.schemas import BikeDefinitionSchema, GeometrySpecBaseSchema
from core.db import SessionLocal
from core.models import BikeDefinitionORM, GeometrySpecORM
from scripts.constants import artifacts_dir
from scripts.schemas import ExtractedData


class Populator:
    def __init__(self, extracted_json_path: Path, db: Session, brand: str):
        self.extracted_json_path = extracted_json_path
        self.db = db
        self.brand = brand

    def _geometries_match(self, existing_def: BikeDefinitionORM, new_geometries: list[GeometrySpecBaseSchema]) -> bool:
        """
        Check if the existing bike definition has the same set of geometries as the new ones.
        """
        existing_geometries = existing_def.geometries
        if len(existing_geometries) != len(new_geometries):
            return False

        # Create a map for easy comparison (size_label -> geometry data)
        # We compare only a subset of fields or a dump.
        # For simplicity and robustness, let's compare all relevant fields.
        existing_map = {g.size_label: g for g in existing_geometries}
        for new_geo in new_geometries:
            existing_geo = existing_map.get(new_geo.size_label)
            if not existing_geo:
                return False

            # Compare key fields. Using model_dump to compare with ORM attributes.
            # We skip definition_id and id.
            new_geo_data = new_geo.model_dump()
            for key, value in new_geo_data.items():
                if hasattr(existing_geo, key):
                    existing_val = getattr(existing_geo, key)
                    # Handle potential float/int comparison or None
                    if existing_val != value:
                        return False
        return True

    def get_or_create_definition(
        self, bike_def: BikeDefinitionSchema, geometries: list[GeometrySpecBaseSchema]
    ) -> BikeDefinitionORM:
        brand_name = bike_def.brand_name
        base_model_name = bike_def.model_name

        # Find all variations of this model name for this brand
        stmt = select(BikeDefinitionORM).where(
            BikeDefinitionORM.brand_name == brand_name,
            BikeDefinitionORM.model_name.like(f"{base_model_name}%"),
            BikeDefinitionORM.year_start == bike_def.year_start,
            BikeDefinitionORM.year_end == bike_def.year_end,
        )
        existing_defs = list(self.db.execute(stmt).scalars())

        # 1. Check if any existing definition matches the geometries exactly
        for existing_def in existing_defs:
            if self._geometries_match(existing_def, geometries):
                logger.debug(f"Found matching definition for {brand_name} {existing_def.model_name}")
                return existing_def

        # 2. If no match, we need to create a new one.
        # But we must ensure the model_name is unique.
        all_model_names = {d.model_name for d in existing_defs}

        new_model_name = base_model_name
        if new_model_name in all_model_names:
            i = 2
            while f"{base_model_name} ({i})" in all_model_names:
                i += 1
            new_model_name = f"{base_model_name} ({i})"
            logger.info(f"Model name conflict. Renaming '{base_model_name}' to '{new_model_name}'")

        bike_definition = BikeDefinitionORM(
            brand_name=brand_name,
            model_name=new_model_name,
            category=bike_def.category,
            material=bike_def.material,
            year_start=bike_def.year_start,
            year_end=bike_def.year_end,
        )
        self.db.add(bike_definition)
        self.db.flush()
        logger.info(f"Created new definition: {brand_name} {new_model_name}")

        return bike_definition

    def get_or_create_geometry_spec(
        self, geo_data: GeometrySpecBaseSchema, definition: BikeDefinitionORM, overwrite: bool = False
    ) -> GeometrySpecORM:
        stmt = select(GeometrySpecORM).where(
            GeometrySpecORM.definition_id == definition.id,
            GeometrySpecORM.size_label == geo_data.size_label,
        )
        existing_spec = self.db.execute(stmt).scalar_one_or_none()

        if existing_spec:
            if not overwrite:
                logger.debug(
                    f"Geometry spec for {definition.model_name} size {geo_data.size_label} already exists. Skipping."
                )
                return existing_spec

            logger.debug(f"Updating existing geometry spec for {definition.model_name} size {geo_data.size_label}")
            # Update fields
            for key, value in geo_data.model_dump().items():
                setattr(existing_spec, key, value)
            self.db.flush()
            return existing_spec

        spec = GeometrySpecORM(definition=definition, **geo_data.model_dump())
        self.db.add(spec)
        self.db.flush()
        logger.debug(f"Added geometry spec for {definition.model_name} size {geo_data.size_label}")
        return spec

    def run(self, overwrite: bool = False):
        try:
            data = ExtractedData.model_validate_json(self.extracted_json_path.read_text())
        except Exception as e:
            logger.error(f"Failed to parse JSON from {self.extracted_json_path}: {e}")
            return

        if not data.geometries:
            logger.warning(f"No geometries found in {self.extracted_json_path}. Skipping.")
            return

        bike_def = self.get_or_create_definition(data.bike_definition, data.geometries)

        for geo_data in data.geometries:
            self.get_or_create_geometry_spec(geo_data, bike_def, overwrite)

        self.db.commit()
        logger.info(f"Successfully processed {self.extracted_json_path.name}")


def populate_brand(brand: str, overwrite: bool = False, clear: bool = False):
    extracted_data_dir = artifacts_dir / brand.lower() / "extracted"
    if not extracted_data_dir.exists():
        logger.error(f"Directory {extracted_data_dir} does not exist.")
        return

    logger.info(f"Starting population for brand: {brand} (overwrite={overwrite}, clear={clear})")

    with SessionLocal() as session:
        if clear:
            logger.info(f"Clearing existing data for brand: {brand}")
            session.execute(delete(BikeDefinitionORM).where(BikeDefinitionORM.brand_name == brand))
            session.commit()

        for item in extracted_data_dir.glob("*.json"):
            populator = Populator(item, session, brand)
            populator.run(overwrite=overwrite)


if __name__ == "__main__":
    for brand in ["Kross", "Trek"]:
        populate_brand(brand, overwrite=False, clear=True)
