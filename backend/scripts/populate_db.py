from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.schemas import BikeDefinitionSchema, GeometrySpecSchema
from core.db import SessionLocal
from core.models import BikeDefinitionORM, GeometrySpecORM
from scripts.constants import artifacts_dir
from scripts.schemas import ExtractedData


class Populator:
    def __init__(self, extracted_json_path: Path, db: Session):
        self.extracted_json_path = extracted_json_path
        self.db = db

    def get_or_create_definition(self, bike_def: BikeDefinitionSchema, overwrite: bool = False) -> BikeDefinitionORM:
        family_stmt = self.db.execute(
            select(BikeDefinitionORM).where(
                BikeDefinitionORM.brand_name == bike_def.brand_name,
                BikeDefinitionORM.model_name == bike_def.model_name,
            )
        )

        if not (bike_definition := family_stmt.scalar_one_or_none()) or overwrite:
            bike_definition = BikeDefinitionORM(
                brand_name=bike_def.brand_name,
                model_name=bike_def.model_name,
                category=bike_def.category,
                material=bike_def.material,
                year_start=bike_def.year_start,
                year_end=bike_def.year_end,
            )
            self.db.add(bike_definition)
            self.db.flush()

        return bike_definition

    def get_or_create_geometry_spec(
        self,
        geo_data: GeometrySpecSchema,
        definition: BikeDefinitionORM,
        overwrite: bool = False,
    ) -> GeometrySpecORM:
        geom_spec = list(
            self.db.execute(
                select(GeometrySpecORM).where(
                    GeometrySpecORM.definition == definition,
                    GeometrySpecORM.size_label == geo_data.size_label,
                )
            ).scalars()
        )

        if len(geom_spec) > 1:
            raise ValueError(f"Multiple specs found for definition {definition.id} and size {geo_data.size_label}")

        if len(geom_spec) == 1 and not overwrite:
            return geom_spec[0]

        spec = GeometrySpecORM(
            definition=definition,
            size_label=geo_data.size_label,
            stack_mm=geo_data.stack_mm,
            reach_mm=geo_data.reach_mm,
            top_tube_effective_mm=geo_data.top_tube_effective_mm,
            seat_tube_length_mm=geo_data.seat_tube_length_mm,
            head_tube_length_mm=geo_data.head_tube_length_mm,
            chainstay_length_mm=geo_data.chainstay_length_mm,
            head_tube_angle=geo_data.head_tube_angle,
            seat_tube_angle=geo_data.seat_tube_angle,
            bb_drop_mm=geo_data.bb_drop_mm,
            wheelbase_mm=geo_data.wheelbase_mm,
            fork_offset_mm=geo_data.fork_offset_mm,
            trail_mm=geo_data.trail_mm,
            standover_height_mm=geo_data.standover_height_mm,
        )
        self.db.add(spec)
        self.db.flush()
        return spec

    def run(self, overwrite: bool = False):
        data = ExtractedData.model_validate_json(self.extracted_json_path.read_text())

        bike_def = self.get_or_create_definition(data.bike_definition, overwrite)
        for geo_data in data.geometries:
            self.get_or_create_geometry_spec(geo_data, bike_def, overwrite)

        self.db.commit()


if __name__ == "__main__":
    extracted_data_dir = artifacts_dir / "trek" / "extracted"

    with SessionLocal() as session:
        session.execute(delete(BikeDefinitionORM).where(BikeDefinitionORM.brand_name == "Trek"))
        session.commit()
        session.flush()

        for item in extracted_data_dir.iterdir():
            print(item.name)
            populator = Populator(item, session)
            populator.run()
