import argparse
import shutil
import zipfile
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from pydantic import BaseModel, Field

from backend.core.models import BuildKit
from backend.utils.helpers import extract_number


class ColorVariant(BaseModel):
    html_path: str
    color: str
    url: str


class BikeMeta(BaseModel):
    brand: str
    model: str
    categories: list[str] = Field(default_factory=list)
    model_year: int | None = None
    wheel_size: str | None = None
    max_tire_width: float | str | None = None
    material: str | None = None
    source_url: str = ""
    colors: list[ColorVariant] = Field(default_factory=list)


class ExtractedBikeData(BaseModel):
    meta: BikeMeta
    build_kit: BuildKit
    sizes: list[str]
    specs: dict[str, list[float | int | str | None]]


class BaseBikeExtractor:
    GEO_MAP: ClassVar[dict[str, list[str]]] = {}
    COMPONENT_KEYWORDS: ClassVar[dict[str, set[str]]] = {
        "groupset": {
            "przerzutka",
            "manetki",
            "korba",
            "kaseta",
            "łańcuch",
            "oś suportu",
            "mechanizm korbowy",
            "hamulce",
            "hamulcowy",
            "klamkomanetki",
        },
        "wheelset": {"piasta", "obręcze", "obręcz", "szprychy", "nyple", "koła", "koło"},
        "cockpit": {
            "kierownica",
            "wspornik",
            "siodło",
            "stery",
            "chwyty",
            "owijka",
            "pedał",
            "sztyca",
            "wspornik siodełka",
            "mostek",
        },
        "tires": {"opony", "opona"},
    }

    def __init__(self, brand_name: str):
        self.brand_name = brand_name

    def clean_value(self, value: str) -> str | int | float:
        """Converts string values to int or float if possible."""
        if not value:
            return ""
        # Common cleanup
        value = value.replace("°", "").strip()
        try:
            return extract_number(value)
        except ValueError:
            return value

    def normalize_wheel_size(self, value: str | int | float | None) -> str | None:
        """Converts wheel size to standardized string representation."""
        if value is None:
            return None
        val_str = str(value).strip().lower()
        val_str = val_str.replace('"', "").replace("''", "").replace("c", "")

        mapping = {
            "29": "700",
            "28": "700",
            "700": "700",
            "27.5": "584",
            "27,5": "584",
            "26": "559",
            "24": "507",
            "20": "406",
            "16": "305",
            "12": "203",
        }
        return mapping.get(val_str, val_str)

    def _categorize_component(self, attr_name: str, attr_content: str, components: dict[str, list[str]]):
        """Categorizes a component attribute into the components dictionary."""
        attr_lower = attr_name.lower()
        for cat, keywords in self.COMPONENT_KEYWORDS.items():
            if any(kw in attr_lower for kw in keywords):
                if cat == "tires":
                    components[cat].append(attr_content)
                elif cat == "wheelset" and "rozmiar" in attr_lower:
                    continue
                else:
                    components[cat].append(f"{attr_name.capitalize()}: {attr_content}")
                return True
        return False

    def _assemble_build_kit(self, components: dict[str, list[str]]) -> BuildKit:
        """Assembles the final BuildKit model from categorized components."""
        bk_data = {k: " | ".join(dict.fromkeys(v)) if v else None for k, v in components.items()}
        bk_data["name"] = "Standard Build"

        # Heuristic for BuildKit name
        groupset = components.get("groupset", [])
        if groupset:
            # Look for rear derailleur (Przerzutka tył/tylna)
            rd = next((s for s in groupset if "Przerzutka tył" in s or "Przerzutka tylna" in s), None)
            if rd and ": " in rd:
                rd_val = rd.split(": ", 1)[1]
                words = rd_val.split()
                if len(words) >= 2:
                    name = " ".join(words[:2])
                    # Special case for Shimano RXXXX
                    if len(words) >= 3 and words[2].startswith("R"):
                        name = " ".join(words[:3])
                    bk_data["name"] = name
                else:
                    bk_data["name"] = rd_val
        return BuildKit(**bk_data)

    def extract_bike_data(self, html: str, additional_data: Any = None) -> ExtractedBikeData | None:
        """To be implemented by subclasses."""
        raise NotImplementedError

    def finalize_extraction(self, json_dir: Path):
        """Archives extracted JSONs to a zip file and removes the original folder."""
        if not json_dir.exists():
            logger.warning(f"⚠️ Cannot finalize: {json_dir} does not exist")
            return

        archive_path = json_dir.parent / "extracted_jsons.zip"
        logger.info("📦 Archiving extracted_jsons to {}...", archive_path)

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for json_file in sorted(json_dir.glob("*.json")):
                zipf.write(json_file, arcname=json_file.name)

        logger.success("✅ JSON archive created: {}", archive_path)
        shutil.rmtree(json_dir)
        logger.info("🗑️ Removed original folder: {}", json_dir)

    def process_archive(self, html_zip: Path, json_dir: Path, force: bool = False):
        """Processes all HTML files in a zip archive."""
        json_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📦 Scanning archive: {html_zip}...")

        processed_htmls = set()
        files_processed = 0
        skipped_count = 0

        with zipfile.ZipFile(html_zip, "r") as z:
            names = set(z.namelist())
            html_files = sorted([n for n in names if n.endswith(".html")])
            total = len(html_files)

            for idx, html_name in enumerate(html_files, 1):
                if html_name in processed_htmls:
                    continue

                try:
                    logger.info(f"📄 [{idx}/{total}] Processing {html_name}...")
                    content = z.read(html_name).decode("utf-8")

                    # Handle brand-specific additional data (like Trek's sizing JSON)
                    additional_data = self._get_additional_data(html_name, names, z)

                    data = self.extract_bike_data(content, additional_data)

                    if data:
                        # Mark variants as processed to avoid duplicates
                        for v in data.meta.colors:
                            processed_htmls.add(v.html_path)
                        processed_htmls.add(html_name)

                        json_name = Path(html_name).with_suffix(".json").name
                        json_path = json_dir / json_name
                        if json_path.exists() and not force:
                            logger.debug(f"⏭️ Skipping {html_name}: JSON already exists")
                            skipped_count += 1
                            continue

                        json_path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
                        logger.debug(f"✅ Saved JSON: {json_path.name}")
                        files_processed += 1
                    else:
                        logger.warning(f"⚠️ Skipped {html_name}: No data extracted")
                        skipped_count += 1
                        processed_htmls.add(html_name)
                except Exception:
                    logger.exception(f"🚨 Error processing {html_name}")
                    skipped_count += 1

        logger.success(f"🏁 Done. Processed: {files_processed} | Skipped: {skipped_count}")

    def process_directory(self, html_dir: Path, json_dir: Path, force: bool = False):
        """Processes all HTML files in a directory."""
        json_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📂 Scanning directory: {html_dir}...")

        html_files = sorted(list(html_dir.glob("*.html")))
        total = len(html_files)
        processed_htmls = set()
        files_processed = 0
        skipped_count = 0

        for idx, html_path in enumerate(html_files, 1):
            if html_path.name in processed_htmls:
                continue

            try:
                logger.info(f"📄 [{idx}/{total}] Processing {html_path.name}...")
                content = html_path.read_text(encoding="utf-8")

                additional_data = self._get_additional_data_dir(html_path)

                data = self.extract_bike_data(content, additional_data)

                if data:
                    for v in data.meta.colors:
                        processed_htmls.add(v.html_path)
                    processed_htmls.add(html_path.name)

                    json_path = json_dir / html_path.with_suffix(".json").name
                    if json_path.exists() and not force:
                        logger.debug(f"⏭️ Skipping {html_path.name}: JSON already exists")
                        skipped_count += 1
                        continue

                    json_path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
                    logger.debug(f"✅ Saved JSON: {json_path.name}")
                    files_processed += 1
                else:
                    logger.warning(f"⚠️ Skipped {html_path.name}: No data extracted")
                    skipped_count += 1
                    processed_htmls.add(html_path.name)
            except Exception:
                logger.exception(f"🚨 Error processing {html_path.name}")
                skipped_count += 1

        logger.success(f"🏁 Done. Processed: {files_processed} | Skipped: {skipped_count}")

    def _get_additional_data(self, html_name: str, all_names: set[str], archive: zipfile.ZipFile) -> Any:
        """Override in subclasses to load companion files from zip."""
        return None

    def _get_additional_data_dir(self, html_path: Path) -> Any:
        """Override in subclasses to load companion files from directory."""
        return None

    @classmethod
    def get_base_parser(cls, brand: str, artifacts_dir: Path) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=f"Extract {brand.capitalize()} bike data from HTML files.")
        parser.add_argument(
            "--input",
            type=Path,
            default=artifacts_dir / brand.lower() / "raw_htmls",
            help="Directory or zip containing raw HTML files.",
        )
        parser.add_argument(
            "--output",
            type=Path,
            default=artifacts_dir / brand.lower() / "extracted_jsons",
            help="Directory to save extracted JSON files.",
        )
        parser.add_argument("--force", action="store_true", help="Overwrite existing JSON files.")
        return parser
