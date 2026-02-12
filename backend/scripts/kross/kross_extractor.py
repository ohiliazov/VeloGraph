import re
import shutil
import zipfile
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from pydantic import BaseModel, Field
from selectolax.lexbor import LexborHTMLParser

from backend.scripts.constants import artifacts_dir
from backend.utils.helpers import extract_number


class BuildKit(BaseModel):
    name: str
    groupset: str | None = None
    wheelset: str | None = None
    cockpit: str | None = None
    tires: str | None = None


class ColorVariant(BaseModel):
    html_path: str
    color: str
    url: str


class BikeMeta(BaseModel):
    brand: str
    model: str
    frame_name: str | None = None
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


class KrossBikeExtractor:
    GEO_MAP: ClassVar[dict[str, list[str]]] = {
        "stack": ["Stack"],
        "reach": ["Reach"],
        "TT": ["TT - efektywna długość górnej rury"],
        "ST": ["ST - Długość rury podsiodłowej"],
        "HT": ["HT - Długość główki ramy"],
        "CS": ["CS - Długość tylnych widełek"],
        "HA": ["HA - Kąt główki ramy"],
        "SA": ["SA - Kąt rury podsiodłowej"],
        "bb_drop": ["BBDROP"],
        "WB": ["WB - Baza kół"],
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

    def extract_file(self, html_path: Path, additional_data: Any = None) -> ExtractedBikeData | None:
        """Extracts data from a single HTML file."""
        if not html_path.exists():
            logger.error(f"❌ File {html_path} not found")
            return None

        content = html_path.read_text(encoding="utf-8")
        return self.extract_bike_data(content, additional_data)

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
        html_dir: Path | None = None,
        json_dir: Path | None = None,
        force: bool = False,
        filename: str | None = None,
    ):
        """Processes HTML files in a directory."""
        html_dir = html_dir or self.html_dir
        json_dir = json_dir or self.json_dir
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
        processed_htmls = set()
        files_processed = 0
        skipped_count = 0

        for idx, html_path in enumerate(html_files, 1):
            if html_path.name in processed_htmls:
                continue

            try:
                logger.info(f"📄 [{idx}/{total}] Processing {html_path.name}...")
                content = html_path.read_text(encoding="utf-8")

                data = self.extract_bike_data(content)

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

    def _parse_colors(self, parser: LexborHTMLParser) -> list[ColorVariant]:
        out: list[ColorVariant] = []
        related_colors_div = parser.css_first("div.product-related-colors")
        if related_colors_div:
            for color_div in related_colors_div.css("div.product-item-colors"):
                a_tag = color_div.css_first("a.variant-item")
                if a_tag:
                    v_url = a_tag.attributes.get("href", "").strip()
                    v_color = a_tag.attributes.get("title", "").strip()
                    v_url_path = v_url.split("?")[0].rstrip("/")
                    v_html_name = v_url_path.split("/")[-1] + ".html"
                    out.append(ColorVariant(html_path=v_html_name, color=v_color, url=v_url))
        return out

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

    def _parse_wheel_size(self, parser: LexborHTMLParser) -> str | None:
        spec_tables = parser.css("table.additional-attributes-table")
        for table in spec_tables:
            for row in table.css("tr"):
                title_cell = row.css_first("td.box-title")
                content_cell = row.css_first("td.box-content")
                if not (title_cell and content_cell):
                    continue
                attr_name = title_cell.text(strip=True)
                attr_content = content_cell.text(strip=True)
                if "opony" in attr_name.lower():
                    match = re.search(r"(\d{3})x|(\d{2}[.,]\d)\"|(\d{2})\"", attr_content, re.IGNORECASE)
                    if match:
                        val = match.group(1) or match.group(2) or match.group(3)
                        return self.normalize_wheel_size(val)
        return None

    def _parse_max_tire_width(self, parser: LexborHTMLParser) -> float | str | None:
        spec_tables = parser.css("table.additional-attributes-table")
        for table in spec_tables:
            for row in table.css("tr"):
                title_cell = row.css_first("td.box-title")
                content_cell = row.css_first("td.box-content")
                if not (title_cell and content_cell):
                    continue
                attr_name = title_cell.text(strip=True)
                attr_content = content_cell.text(strip=True)
                if "maksymalna szerokość opony" in attr_name.lower():
                    return self.clean_value(attr_content)
        return None

    def _extract_meta(self, parser: LexborHTMLParser) -> BikeMeta:
        return BikeMeta(
            brand=self._parse_brand(),
            model=self._parse_model(parser),
            categories=self._parse_categories(parser),
            model_year=self._parse_model_year(parser),
            wheel_size=self._parse_wheel_size(parser),
            max_tire_width=self._parse_max_tire_width(parser),
            material=self._parse_material(parser),
            source_url=self._parse_source_url(parser),
            colors=self._parse_colors(parser),
        )

    def extract_bike_data(self, html: str) -> ExtractedBikeData | None:
        """Parses Kross bike HTML."""
        parser = LexborHTMLParser(html)

        # --- Meta via dedicated field parsers ---
        bike_meta = self._extract_meta(parser)
        components = {k: [] for k in self.COMPONENT_KEYWORDS}

        # --- 1. Extract from Additional Attributes (Specyfikacja) ---
        spec_tables = parser.css("table.additional-attributes-table")
        for table in spec_tables:
            for row in table.css("tr"):
                title_cell = row.css_first("td.box-title")
                content_cell = row.css_first("td.box-content")
                if not (title_cell and content_cell):
                    continue

                attr_name = title_cell.text(strip=True)
                attr_content = content_cell.text(strip=True)

                # BuildKit components only (metadata handled by dedicated parsers)
                self._categorize_component(attr_name, attr_content, components)

        # --- 2. Geometry: handled by a single function ---
        target_table = None
        for table in parser.css("table"):
            thead = table.css_first("thead")
            if thead:
                th = thead.css_first("th")
                if th and "Rozmiar" in th.text():
                    target_table = table
                    break

        if not target_table:
            return None

        # Extract sizes and specs from geometry table
        bike_sizes: list[str] = []
        bike_specs: dict[str, list[float | int | str | None]] = {}

        thead = target_table.css_first("thead")
        header_row = thead.css_first("tr") if thead else None
        if not header_row:
            return None

        for th in header_row.css("th")[1:]:
            size_text = th.text(strip=True)
            bike_sizes.append(size_text)

            # Wheel size from header if missing
            if not bike_meta.wheel_size:
                matches = [m.group(1) or m.group(2) for m in re.finditer(r"(\d{2}[.,]\d)\"|(\d{2})\"", size_text)]
                if matches:
                    val = matches[-1] if len(matches) > 1 else (matches[0] if "(" not in size_text else None)
                    if val:
                        bike_meta.wheel_size = self.normalize_wheel_size(val)

        tbody = target_table.css_first("tbody")
        if tbody:
            for row in tbody.css("tr"):
                cells = row.css("td")
                if not cells:
                    continue
                attr_name = cells[0].text(strip=True)

                mapped_key = None
                attr_lower = attr_name.lower()
                for internal_key, labels in self.GEO_MAP.items():
                    if any(label.lower() in attr_lower for label in labels):
                        mapped_key = internal_key
                        break
                if not mapped_key:
                    mapped_key = attr_name

                values = [self.clean_value(cell.text(strip=True)) for cell in cells[1:]]
                values.extend([None] * (len(bike_sizes) - len(values)))
                bike_specs[mapped_key] = values

        # Wheel size from geometry row if still missing
        if not bike_meta.wheel_size:
            for attr, vals in bike_specs.items():
                if "rozmiar kół" in attr.lower():
                    for v in (v for v in vals if v):
                        match = re.search(r"(\d{3})|(\d{2}[.,]\d)|(\d{2})", str(v))
                        if match:
                            bike_meta.wheel_size = self.normalize_wheel_size(match.group(0))
                            break
                    if bike_meta.wheel_size:
                        break

        # Extract additional components from geometry table
        for attr_name, values in bike_specs.items():
            if not (values and any(values)):
                continue

            rep_val = None
            for v in (v for v in values if v):
                v_str = str(v)
                if len(re.sub(r"[0-9.,\s\-\*/°'\"(kg)(mm)(c)]", "", v_str, flags=re.IGNORECASE)) > 2:
                    rep_val = v_str
                    break

            if rep_val:
                self._categorize_component(attr_name, rep_val, components)

        return ExtractedBikeData(
            meta=bike_meta,
            build_kit=self._assemble_build_kit(components),
            sizes=bike_sizes,
            specs={k: v for k, v in bike_specs.items() if k in self.GEO_MAP},
        )


if __name__ == "__main__":
    extractor = KrossBikeExtractor()
    extractor.process_directory(
        artifacts_dir / "kross" / "raw_htmls",
        artifacts_dir / "kross" / "exctracted_jsons",
        force=True,
    )
