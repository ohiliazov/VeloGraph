import re
import shutil
from pathlib import Path

from loguru import logger
from pydantic import ValidationError
from selectolax.lexbor import LexborHTMLParser

from api.schemas import BikeDefinitionSchema, GeometrySpecBaseSchema
from scripts.constants import artifacts_dir
from scripts.schemas import ExtractedData
from utils.helpers import extract_number

GEO_MAP = {
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
    "standover_height_mm": "Przekrok",
}

REQUIRED_GEO_KEYS = {
    "stack_mm",
    "reach_mm",
    "head_tube_angle",
    "seat_tube_angle",
    "chainstay_length_mm",
    "wheelbase_mm",
    "bb_drop_mm",
}


class KrossBikeExtractor:
    def __init__(self, input_html_path: Path, output_json_path: Path):
        self.input_html_path = input_html_path
        self.output_json_path = output_json_path

    def run(self) -> ExtractedData:
        """Extracts data and saves it to JSON."""
        content = self.input_html_path.read_text(encoding="utf-8")
        data = self.extract_bike_data(content)

        self.output_json_path.write_text(
            data.model_dump_json(indent=2, exclude_none=True, exclude_unset=True),
            encoding="utf-8",
        )
        return data

    def _parse_model(self, parser: LexborHTMLParser) -> str:
        # Priority 1: og:title
        title_tag = parser.css_first('meta[property="og:title"]')
        if title_tag:
            title = title_tag.attributes.get("content", "").strip()
            if " | " in title:
                return title.split(" | ")[0].strip()
            return title

        # Priority 2: h1.page-title
        h1 = parser.css_first("h1.page-title")
        if h1:
            return h1.text(strip=True)

        # Priority 3: title tag
        title_tag = parser.css_first("title")
        if title_tag:
            return title_tag.text(strip=True).split("|")[0].strip()

        return ""

    def _parse_categories(self, parser: LexborHTMLParser) -> list[str]:
        out: list[str] = []
        # Priority 1: product-breadcrumbs
        breadcrumbs = parser.css_first("div.product-breadcrumbs")
        if breadcrumbs:
            raw_text = breadcrumbs.text(strip=True)
            raw_cats = [c.strip() for c in re.split(r"\s*/\s*", raw_text)]
            for c in raw_cats:
                # Skip year-like strings
                if not (c.isdigit() and len(c) == 4 and 2000 <= int(c) <= 2100) and c:
                    out.append(c)

        # Priority 2: standard breadcrumbs
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
        # Priority 1: breadcrumbs
        breadcrumbs = parser.css_first("div.product-breadcrumbs")
        if breadcrumbs:
            raw_text = breadcrumbs.text(strip=True)
            for c in re.split(r"\s*/\s*", raw_text):
                if c.isdigit() and len(c) == 4 and 2000 <= int(c) <= 2100:
                    return int(c)

        # Priority 2: SKU fallback
        form = parser.css_first("form[data-product-sku]")
        if form:
            sku = form.attributes.get("data-product-sku", "")
            match = re.search(r"20\d{2}", sku)
            if match:
                return int(match.group(0))

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

    def extract_bike_data(self, html: str) -> ExtractedData:
        """Parses Kross bike HTML."""
        parser = LexborHTMLParser(html)

        model_name = self._parse_model(parser)
        categories = self._parse_categories(parser)
        category = ", ".join(categories) if categories else ""
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
            mapped_key = next((k for k, label in GEO_MAP.items() if label.lower() in attr_name), None)

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
        for data in geo_data_list:
            if all(k in data for k in REQUIRED_GEO_KEYS):
                try:
                    geometries.append(GeometrySpecBaseSchema(**data))
                except Exception as e:
                    logger.error(f"Validation failed for size {data.get('size_label')}: {e}")

        return geometries


if __name__ == "__main__":
    raw_htmls_dir = artifacts_dir / "kross" / "raw_htmls"
    extracted_json_dir = artifacts_dir / "kross" / "extracted"
    error_dir = artifacts_dir / "kross" / "invalid_htmls"

    shutil.rmtree(extracted_json_dir, ignore_errors=True)
    extracted_json_dir.mkdir(parents=True, exist_ok=True)
    error_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(list(raw_htmls_dir.glob("*.html")))
    total = len(html_files)
    files_processed = 0

    for idx, html_path in enumerate(html_files, 1):
        output_path = extracted_json_dir / html_path.with_suffix(".json").name
        extractor = KrossBikeExtractor(html_path, output_path)
        try:
            logger.info(f"📄 [{idx}/{total}] Processing {html_path.name}...")
            extractor.run()
            files_processed += 1
        except ValidationError as err:
            logger.error(f"Validation error in {html_path.name}: {err}")
            shutil.copy(html_path, error_dir / html_path.name)
        except Exception:
            logger.exception(f"🚨 Error processing {html_path.name}")
            shutil.copy(html_path, error_dir / html_path.name)

    logger.success(f"🏁 Done. Processed: {files_processed}/{total}")
