import re
import shutil
import zipfile
from pathlib import Path
from typing import ClassVar

from loguru import logger
from selectolax.lexbor import LexborHTMLParser

from api.schemas import BikeDefinitionSchema, GeometrySpecBaseSchema
from scripts.constants import artifacts_dir
from scripts.schemas import ExtractedData
from utils.helpers import extract_number


class KrossBikeExtractor:
    GEO_MAP: ClassVar[dict[str, str]] = {
        "stack_mm": "Stack",
        "reach_mm": "Reach",
        "top_tube_effective_mm": "TT - efektywna długość górnej rury",
        "seat_tube_length_mm": "ST - Długość rury podsiodłowej",
        "head_tube_length_mm": "HT - Długość główki ramy",
        "chainstay_length_mm": "CS - Długość tylnych widełek",
        "head_tube_angle": "HA - Kąt główki ramy",
        "seat_tube_angle": "SA - Kąt rury podsiodłowej",
        "bb_drop_mm": "BBDROP",
        "wheelbase_mm": "WB - Baza kół",
    }

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

    def clean_value(self, value: str) -> str | float:
        """Converts string values to float if possible."""
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

    def extract_file(self, html_path: Path) -> ExtractedData | None:
        """Extracts data from a single HTML file."""
        if not html_path.exists():
            logger.error(f"❌ File {html_path} not found")
            return None

        content = html_path.read_text(encoding="utf-8")
        return self.extract_bike_data(content)

    def finalize_extraction(self, json_dir: Path | None = None):
        """Archives extracted JSONs to a zip file and removes the original folder."""
        json_dir = json_dir or self.json_dir
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

    def process_all(self, force: bool = False):
        """Processes all HTML files in the html_dir."""
        self.process_directory(self.html_dir, self.json_dir, force=force)

    def process_directory(
        self,
        html_dir: Path,
        json_dir: Path,
        force: bool = False,
        filename: str | None = None,
    ):
        """Processes HTML files in a directory."""
        json_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📂 Scanning directory: {html_dir}...")

        if filename:
            html_path = html_dir / filename
            if not html_path.exists():
                logger.error(f"❌ File {filename} not found in directory {html_dir}")
                return
            html_files = [html_path]
        else:
            html_files = sorted(list(html_dir.glob("*.html")))

        total = len(html_files)
        files_processed = 0
        skipped_count = 0

        for idx, html_path in enumerate(html_files, 1):
            try:
                logger.info(f"📄 [{idx}/{total}] Processing {html_path.name}...")

                json_path = json_dir / html_path.with_suffix(".json").name
                if json_path.exists() and not force:
                    logger.debug(f"⏭️ Skipping {html_path.name}: JSON already exists")
                    skipped_count += 1
                    continue

                content = html_path.read_text(encoding="utf-8")
                data = self.extract_bike_data(content)

                if data:
                    json_path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
                    logger.debug(f"✅ Saved JSON: {json_path.name}")
                    files_processed += 1
                else:
                    logger.warning(f"⚠️ Skipped {html_path.name}: No data extracted")
                    skipped_count += 1
            except Exception:
                logger.exception(f"🚨 Error processing {html_path.name}")
                skipped_count += 1

        logger.success(f"🏁 Done. Processed: {files_processed} | Skipped: {skipped_count}")

    # --- Meta parsers (one function per field) ---
    def _parse_brand(self) -> str:
        return "Kross"

    def _parse_model(self, parser: LexborHTMLParser) -> str:
        title_tag = parser.css_first('meta[property="og:title"]')
        if title_tag:
            title = title_tag.attributes.get("content", "").strip()
            if " | " in title:
                return title.split(" | ")[0].strip()
            return title
        return ""

    def _parse_source_url(self, parser: LexborHTMLParser) -> str:
        url_tag = parser.css_first('meta[property="og:url"]')
        if url_tag:
            return url_tag.attributes.get("content", "").strip()
        return ""

    def _parse_categories(self, parser: LexborHTMLParser) -> list[str]:
        out: list[str] = []
        breadcrumbs = parser.css_first("div.product-breadcrumbs")
        if breadcrumbs:
            raw_text = breadcrumbs.text(strip=True)
            raw_cats = [c.strip() for c in re.split(r"\s*/\s*", raw_text)]
            for c in raw_cats:
                if not (c.isdigit() and len(c) == 4 and 2000 <= int(c) <= 2100) and c:
                    out.append(c)
        if not out:
            breadcrumbs_fallback = parser.css_first("div.breadcrumbs")
            if breadcrumbs_fallback:
                for li in breadcrumbs_fallback.css("li"):
                    classes = li.attributes.get("class", "")
                    classes = classes.split() if isinstance(classes, str) else []
                    has_category_class = any(
                        c.startswith("category") and any(char.isdigit() for char in c) for c in classes
                    )
                    if has_category_class:
                        cat_text = li.text(strip=True)
                        if cat_text:
                            out.append(cat_text)
        return out

    def _parse_model_year(self, parser: LexborHTMLParser) -> int | None:
        breadcrumbs = parser.css_first("div.product-breadcrumbs")
        if breadcrumbs:
            raw_text = breadcrumbs.text(strip=True)
            for c in re.split(r"\s*/\s*", raw_text):
                if c.isdigit() and len(c) == 4 and 2000 <= int(c) <= 2100:
                    return int(c)
        return None

    def _parse_material(self, parser: LexborHTMLParser) -> str | None:
        spec_tables = parser.css("table.additional-attributes-table")
        for table in spec_tables:
            for row in table.css("tr"):
                title_cell = row.css_first("td.box-title")
                content_cell = row.css_first("td.box-content")
                if not (title_cell and content_cell):
                    continue
                attr_name = title_cell.text(strip=True)
                attr_content = content_cell.text(strip=True)
                if "rama" in attr_name.lower():
                    return attr_content
        return None

    def extract_bike_data(self, html: str) -> ExtractedData | None:
        """Parses Kross bike HTML."""
        parser = LexborHTMLParser(html)

        model_name = self._parse_model(parser)
        category = ", ".join(categories) if (categories := self._parse_categories(parser)) else ""
        model_year = self._parse_model_year(parser)
        material = self._parse_material(parser)
        bike_definition = BikeDefinitionSchema(
            brand_name="Kross",
            model_name=model_name,
            category=category,
            year_start=model_year,
            year_end=model_year,
            material=material,
        )

        geometries = self._parse_geometry(parser)
        if not geometries:
            return None

        return ExtractedData(
            bike_definition=bike_definition,
            geometries=geometries,
        )

    def _parse_geometry(self, parser: LexborHTMLParser) -> list[GeometrySpecBaseSchema]:
        """Extracts geometry specs from HTML table."""
        target_table = None
        for table in parser.css("table"):
            thead = table.css_first("thead")
            if thead and (th := thead.css_first("th")) and "Rozmiar" in th.text():
                target_table = table
                break

        if not target_table:
            return []

        header_row = target_table.css_first("thead tr")
        if not header_row:
            return []
        sizes = [th.text(strip=True) for th in header_row.css("th")[1:]]

        # We'll build a list of dicts, one for each size
        geo_data_list = [{"size_label": size} for size in sizes]

        tbody = target_table.css_first("tbody")
        if not tbody:
            return []

        for row in tbody.css("tr"):
            cells = row.css("td")
            if not cells:
                continue

            attr_name = cells[0].text(strip=True).lower()
            mapped_key = next((k for k, label in self.GEO_MAP.items() if label.lower() in attr_name), None)

            if not mapped_key:
                continue

            for i, cell in enumerate(cells[1:]):
                if i >= len(geo_data_list):
                    break
                val_text = cell.text(strip=True)
                if not val_text:
                    continue

                try:
                    num = extract_number(val_text)
                    geo_data_list[i][mapped_key] = float(num) if "angle" in mapped_key else round(num)
                except ValueError, TypeError:
                    continue

        geometries = []
        required_keys = {
            "stack_mm",
            "reach_mm",
            "head_tube_angle",
            "seat_tube_angle",
            "chainstay_length_mm",
            "wheelbase_mm",
            "bb_drop_mm",
        }
        for data in geo_data_list:
            if all(k in data for k in required_keys):
                try:
                    geometries.append(GeometrySpecBaseSchema(**data))
                except Exception as e:
                    logger.error(f"Validation failed for size {data.get('size_label')}: {e}")

        return geometries


if __name__ == "__main__":
    raw_htmls_dir = artifacts_dir / "kross" / "raw_htmls"
    extracted_json_dir = artifacts_dir / "kross" / "extracted"

    shutil.rmtree(extracted_json_dir, ignore_errors=True)
    extracted_json_dir.mkdir(parents=True, exist_ok=True)

    extractor = KrossBikeExtractor()
    extractor.process_directory(
        raw_htmls_dir,
        extracted_json_dir,
        force=True,
    )
