import re
import shutil
from decimal import Decimal
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.api.schemas import BikeDefinitionSchema, GeometrySpecSchema
from backend.scripts.constants import artifacts_dir
from backend.scripts.schemas import ExtractedData

FLOAT_REGEX = re.compile(r"-?\d+(?:\.\d+)?")

GEOMETRY_FIELDS = {
    "size_label": ["geometryFrameSizeLetter", "geometryFrameSizeNumber", "geometrySeattube"],
    "stack_mm": ["geometryFrameStack"],
    "reach_mm": ["geometryFrameReach"],
    "top_tube_effective_mm": ["geometryEffToptube"],
    "seat_tube_length_mm": ["geometrySeattube"],
    "head_tube_length_mm": ["geometryLengthHeadtube"],
    "chainstay_length_mm": ["geometryLengthChainstay"],
    "head_tube_angle": ["geometryAngleHead"],
    "seat_tube_angle": ["geometryAngleSeattube", "geometryAngleEffSeattube"],
    "wheelbase_mm": ["geometryWheelbase"],
    "bb_drop_mm": ["geometryBBDrop"],
    "fork_offset_mm": ["geometryOffset"],
    "trail_mm": ["geometryTrail"],
    "standover_height_mm": ["geometryStandover"],
}

NUMERIC_FIELDS = {
    "stack_mm",
    "reach_mm",
    "top_tube_effective_mm",
    "seat_tube_length_mm",
    "head_tube_length_mm",
    "chainstay_length_mm",
    "wheelbase_mm",
    "bb_drop_mm",
    "fork_offset_mm",
    "trail_mm",
    "standover_height_mm",
    "head_tube_angle",
    "seat_tube_angle",
}
ANGLE_FIELDS = {"head_tube_angle", "seat_tube_angle"}


class InputDetailsSpec(BaseModel):
    shortSpecFrame: str | None = None
    shortSpecFork: str | None = None
    shortSpecWeight: str | None = None
    shortSpecTires: str | None = None

    specFrame: str | None = None
    specFork: str | None = None
    specWeight: str | None = None
    specTires: str | None = None
    specTireSizeMax: str | None = None


class InputDetails(BaseModel):
    name: str
    code: str
    default_category: str = Field(alias="defaultCategory")
    model_year: str | None = Field(None, alias="marketingModelYear")
    specs: InputDetailsSpec

    model_config = ConfigDict(validate_by_alias=True)

    @property
    def year_start(self) -> int | None:
        if self.model_year:
            if "-" in self.model_year:
                return int(self.model_year.split("-")[0])
            else:
                return int(self.model_year)
        return None

    @property
    def year_end(self) -> int | None:
        if self.model_year:
            if "-" in self.model_year:
                return int(self.model_year.split("-")[1])
            else:
                return int(self.model_year)
        return None


class InputGeometryRow(BaseModel):
    # The JSON structure for 'geometryData' is a list of objects
    # where the key 'geometry' contains the list of values.
    geometry: list[str]


class InputSizing(BaseModel):
    geometryDataHeaders: list[str]
    geometryData: list[InputGeometryRow]


class InputData(BaseModel):
    details: InputDetails
    sizing: InputSizing


class TrekBikeExtractor:
    def __init__(self, input_json_path: Path, output_json_path: Path):
        self.input_json_path = input_json_path
        self.output_json_path = output_json_path
        self.data: InputData | None = None

    def run(self) -> ExtractedData:
        data = InputData.model_validate_json(self.input_json_path.read_text())

        bike_definition = BikeDefinitionSchema(
            brand_name="Trek",
            model_name=data.details.name,
            category=data.details.default_category,
            year_start=data.details.year_start,
            year_end=data.details.year_end,
            material=data.details.specs.specFrame or data.details.specs.shortSpecFrame,
        )
        geometries = []
        headers = data.sizing.geometryDataHeaders
        for row in data.sizing.geometryData:
            raw_row_dict = dict(zip(headers, row.geometry, strict=False))
            geo_spec = {}

            for model_key, trek_keys in GEOMETRY_FIELDS.items():
                for trek_key in trek_keys:
                    val = raw_row_dict.get(trek_key)
                    if val is not None:
                        break
                else:
                    continue

                val = val.replace("°", ".")
                if model_key in NUMERIC_FIELDS:
                    m = FLOAT_REGEX.match(val)
                    assert m is not None, f"Invalid numeric value '{val}' for '{model_key}'"
                    val = Decimal(m.group(0))
                    if val not in ANGLE_FIELDS:
                        val = Decimal(m.group(0)) * 10

                geo_spec[model_key] = val

            geometries.append(GeometrySpecSchema(**geo_spec))

        extracted_data = ExtractedData(
            bike_definition=bike_definition,
            geometries=geometries,
        )

        self.output_json_path.write_text(extracted_data.model_dump_json(indent=2, exclude_none=True))

        return extracted_data


if __name__ == "__main__":
    raw_jsons_dir = artifacts_dir / "trek" / "raw_jsons"
    extracted_json_dir = artifacts_dir / "trek" / "extracted"
    error_dir = artifacts_dir / "trek" / "invalid_jsons"

    shutil.rmtree(extracted_json_dir, ignore_errors=True)
    extracted_json_dir.mkdir(parents=True, exist_ok=True)
    error_dir.mkdir(parents=True, exist_ok=True)

    for item in raw_jsons_dir.iterdir():
        extractor = TrekBikeExtractor(item, extracted_json_dir / item.name)
        try:
            extractor.run()
        except ValidationError as err:
            logger.error(f"Invalid JSON {item.name}:")
            for error in err.errors():
                logger.error(f"  {error['msg']}: {'.'.join(error['loc'])}")
            error_path = error_dir / item.name
            error_path.write_text(item.read_text())
