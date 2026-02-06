import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup, SoupStrainer, Tag
from loguru import logger
from pydantic import BaseModel, Field

from backend.core.models import BuildKit
from backend.scripts.constants import artifacts_dir
from backend.utils.helpers import extract_number

# --- Models ---


class KrossColorVariant(BaseModel):
    html_path: str
    color: str
    url: str


class KrossBikeMeta(BaseModel):
    brand: str = "Kross"
    model: str
    categories: list[str] = Field(default_factory=list)
    model_year: int | None = None
    wheel_size: str | None = None
    max_tire_width: float | str | None = None
    material: str | None = None
    source_url: str = ""
    colors: list[KrossColorVariant] = Field(default_factory=list)


class ExtractedBikeData(BaseModel):
    meta: KrossBikeMeta
    build_kit: BuildKit
    sizes: list[str]
    specs: dict[str, list[float | int | str | None]]


# --- Constants ---
RELEVANT_GEO_KEYS = {
    "Stack",
    "Reach",
    "TT - efektywna długość górnej rury",
    "ST - Długość rury podsiodłowej",
    "HT - Długość główki ramy",
    "CS - Długość tylnych widełek",
    "HA - Kąt główki ramy",
    "SA - Kąt rury podsiodłowej",
    "BBDROP",
    "WB - Baza kół",
}

COMPONENT_KEYWORDS = {
    "groupset": {"przerzutka", "manetki", "korba", "kaseta", "łańcuch"},
    "wheelset": {"piasta", "obręcze", "obręcz", "szprychy", "nyple", "koła"},
    "cockpit": {"kierownica", "wspornik", "siodło", "stery", "chwyty", "owijka", "pedał"},
    "tires": {"opony"},
}


def clean_value(value: str) -> str | int | float:
    """
    Converts string values to int or float if possible.
    Handles Polish decimal formats (e.g., "74,5" -> 74.5).
    """
    if not value:
        return ""

    try:
        return extract_number(value)
    except ValueError:
        return value.strip()


def normalize_wheel_size(value: str | int | float | None) -> str | None:
    """
    Converts wheel size to mm string representation.
    e.g. 28 -> 700, 29 -> 700, 26 -> 559, etc.
    """
    if value is None:
        return None

    # Standardize to string
    val_str = str(value).strip().lower()

    # Remove quotes if any
    val_str = val_str.replace('"', "").replace("''", "")

    # Common mappings
    mapping = {
        "29": "700",  # Often used for 29er MTB (622mm)
        "28": "700",  # Standard 700c (622mm)
        "27.5": "584",
        "27,5": "584",
        "27": "584",  # Handle cases where .5 is missing but it's likely 27.5
        "26": "559",
        "24": "507",
        "20": "406",
        "16": "305",
        "14": "254",
        "12": "203",
    }

    if val_str in mapping:
        return mapping[val_str]

    # If it's already 700, return as is
    if val_str == "700":
        return "700"

    return val_str


def _extract_meta(soup: BeautifulSoup) -> KrossBikeMeta:
    """Extracts basic metadata from BeautifulSoup object."""
    meta_data = {
        "brand": "Kross",
        "model": "",
        "categories": [],
        "model_year": None,
        "wheel_size": None,
        "max_tire_width": None,
        "material": None,
        "color": None,
        "source_url": "",
    }

    # OG tags
    title_tag = soup.find("meta", property="og:title")
    if title_tag and isinstance(title_tag, Tag):
        title = title_tag.get("content", "").strip()
        if " | " in title:
            meta_data["model"] = title.split(" | ")[0].strip()

    url_tag = soup.find("meta", property="og:url")
    if url_tag and isinstance(url_tag, Tag):
        meta_data["source_url"] = url_tag.get("content", "").strip()

    # Breadcrumbs & Year
    breadcrumbs = soup.find("div", class_="product-breadcrumbs")
    if breadcrumbs:
        raw_text = breadcrumbs.get_text(strip=True)
        raw_cats = [c.strip() for c in re.split(r"\s*/\s*", raw_text)]
        for c in raw_cats:
            if c.isdigit() and len(c) == 4 and 2000 <= int(c) <= 2100:
                meta_data["model_year"] = int(c)
            elif c:
                meta_data["categories"].append(c)

    if not meta_data["categories"]:
        # Fallback to standard breadcrumbs: breadcrumbs > ul > li
        # Look for li with class containing "category" and a number
        breadcrumbs_fallback = soup.find("div", class_="breadcrumbs")
        if breadcrumbs_fallback:
            for li in breadcrumbs_fallback.find_all("li"):
                classes = li.get("class", [])
                if isinstance(classes, str):
                    classes = [classes]

                has_category_class = any(
                    c.startswith("category") and any(char.isdigit() for char in c) for c in classes
                )
                if has_category_class:
                    cat_text = li.get_text(strip=True)
                    if cat_text:
                        meta_data["categories"].append(cat_text)

    # Colors from product-item-colors
    related_colors_div = soup.find("div", class_="product-related-colors")
    if related_colors_div:
        color_variants = []
        for color_div in related_colors_div.find_all("div", class_="product-item-colors"):
            a_tag = color_div.find("a", class_="variant-item")
            if a_tag and isinstance(a_tag, Tag):
                v_url = a_tag.get("href", "").strip()
                v_color = a_tag.get("title", "").strip()
                # Use URL to get path
                v_url_path = v_url.split("?")[0].rstrip("/")
                v_html_name = v_url_path.split("/")[-1] + ".html"

                color_variants.append(KrossColorVariant(html_path=v_html_name, color=v_color, url=v_url))
        if color_variants:
            meta_data["colors"] = color_variants

    return KrossBikeMeta(**meta_data)


def _categorize_component(attr_name: str, attr_content: str, components: dict[str, list[str]]):
    """Categorizes a component attribute into the components dictionary."""
    attr_lower = attr_name.lower()
    for cat, keywords in COMPONENT_KEYWORDS.items():
        if any(kw in attr_lower for kw in keywords):
            if cat == "tires":
                components[cat].append(attr_content)
            elif cat == "wheelset" and "rozmiar" in attr_lower:
                continue
            else:
                components[cat].append(f"{attr_name.capitalize()}: {attr_content}")
            return True
    return False


def _assemble_build_kit(components: dict[str, list[str]]) -> BuildKit:
    """Assembles the final BuildKit model from categorized components."""
    # Deduplicate while preserving order
    bk_data = {k: " | ".join(dict.fromkeys(v)) if v else None for k, v in components.items()}

    # Heuristic for BuildKit name from groupset (rear derailleur)
    bk_data["name"] = "Standard Build"
    if components["groupset"]:
        rd = next((s for s in components["groupset"] if "Przerzutka tył" in s), None)
        if rd and ": " in rd:
            rd_val = rd.split(": ", 1)[1]
            words = rd_val.split()
            if len(words) >= 2:
                name = " ".join(words[:2])
                if len(words) >= 3 and words[2].startswith("R"):
                    name = " ".join(words[:3])
                bk_data["name"] = name
            else:
                bk_data["name"] = rd_val

    return BuildKit(**bk_data)


def extract_bike_data(html: str) -> ExtractedBikeData | None:
    """
    Parses Kross bike HTML.
    Returns an ExtractedBikeData model or None if geometry is missing.
    """
    # Use SoupStrainer to only parse the parts of the document we care about
    # This significantly speeds up BeautifulSoup parsing
    strainer = SoupStrainer(["meta", "div", "table", "ul", "li", "a"])
    try:
        soup = BeautifulSoup(html, "lxml", parse_only=strainer)
    except Exception:
        soup = BeautifulSoup(html, "html.parser", parse_only=strainer)

    bike_meta = _extract_meta(soup)
    components = {k: [] for k in COMPONENT_KEYWORDS}

    # --- 1. Extract from Additional Attributes (Specyfikacja) ---
    spec_tables = soup.find_all("table", class_="additional-attributes-table")
    for table in spec_tables:
        for row in table.find_all("tr"):
            title_cell = row.find("td", class_="box-title")
            content_cell = row.find("td", class_="box-content")
            if not (title_cell and content_cell):
                continue

            attr_name = title_cell.get_text(strip=True)
            attr_content = content_cell.get_text(strip=True)
            attr_lower = attr_name.lower()

            # Metadata updates
            if "rama" in attr_lower:
                bike_meta.material = attr_content
            elif "maksymalna szerokość opony" in attr_lower:
                bike_meta.max_tire_width = clean_value(attr_content)
            elif not bike_meta.wheel_size and "opony" in attr_lower:
                match = re.search(r"(\d{3})x|(\d{2}[.,]\d)\"|(\d{2})\"", attr_content, re.IGNORECASE)
                if match:
                    val = match.group(1) or match.group(2) or match.group(3)
                    bike_meta.wheel_size = normalize_wheel_size(val)

            # BuildKit components
            _categorize_component(attr_name, attr_content, components)

    # --- 2. Find and Extract Geometry Table ---
    target_table = None
    for table in soup.find_all("table"):
        thead = table.find("thead")
        if thead and thead.find("th") and "Rozmiar" in thead.find("th").get_text():
            target_table = table
            break

    if not target_table:
        return None

    # --- 3. Extract Table Data (Sizes & Specs) ---
    bike_sizes = []
    bike_specs = {}

    # Headers (Sizes)
    header_row = target_table.find("thead").find("tr")
    if not header_row:
        return None

    for th in header_row.find_all("th")[1:]:
        size_text = th.get_text(strip=True)
        bike_sizes.append(size_text)

        # Wheel size from header if missing
        if not bike_meta.wheel_size:
            matches = [m.group(1) or m.group(2) for m in re.finditer(r"(\d{2}[.,]\d)\"|(\d{2})\"", size_text)]
            if matches:
                # Use last match if multiple (likely wheel size), otherwise use first if no parentheses
                val = matches[-1] if len(matches) > 1 else (matches[0] if "(" not in size_text else None)
                if val:
                    bike_meta.wheel_size = normalize_wheel_size(val)

    # Body (Specs)
    tbody = target_table.find("tbody")
    if tbody:
        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            attr_name = cells[0].get_text(strip=True)
            values = [clean_value(cell.get_text(strip=True)) for cell in cells[1:]]
            # Pad values if shorter than sizes
            values.extend([None] * (len(bike_sizes) - len(values)))
            bike_specs[attr_name] = values

    # Wheel size from geometry row if still missing
    if not bike_meta.wheel_size:
        for attr, vals in bike_specs.items():
            if "rozmiar kół" in attr.lower():
                for v in (v for v in vals if v):
                    match = re.search(r"(\d{3})|(\d{2}[.,]\d)|(\d{2})", str(v))
                    if match:
                        bike_meta.wheel_size = normalize_wheel_size(match.group(0))
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
            _categorize_component(attr_name, rep_val, components)

    return ExtractedBikeData(
        meta=bike_meta,
        build_kit=_assemble_build_kit(components),
        sizes=bike_sizes,
        specs={k: v for k, v in bike_specs.items() if k in RELEVANT_GEO_KEYS},
    )


def process_archive(html_zip: Path, json_dir: Path, force: bool = False):
    """
    Processes all HTML files in a zip archive.
    Groups color variants.
    """
    json_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📦 Scanning archive: {html_zip}...")

    processed_htmls = set()
    files_processed = 0
    skipped_count = 0

    with zipfile.ZipFile(html_zip, "r") as z:
        html_files = [n for n in z.namelist() if n.endswith(".html")]

        # Sort files to be deterministic
        for html_name in sorted(html_files):
            if html_name in processed_htmls:
                continue

            try:
                content = z.read(html_name).decode("utf-8")
                data = extract_bike_data(content)

                if data:
                    # Mark variants as processed
                    for v in data.meta.colors:
                        processed_htmls.add(v.html_path)

                    # Mark current file as processed
                    processed_htmls.add(html_name)

                    json_name = Path(html_name).with_suffix(".json").name
                    json_path = json_dir / json_name
                    if json_path.exists() and not force:
                        logger.debug(f"⚠️  Skipping {html_name}: JSON already exists")
                        skipped_count += 1
                        continue

                    json_path.write_text(
                        data.model_dump_json(indent=2),
                        encoding="utf-8",
                    )
                    logger.debug(f"✅ Saved JSON: {json_path.name}")
                    files_processed += 1
                else:
                    logger.warning(f"⚠️  Skipped {html_name}: No geometry table found")
                    skipped_count += 1
                    processed_htmls.add(html_name)
            except Exception:
                logger.exception(f"🚨 Critical error processing {html_name}")
                skipped_count += 1
                processed_htmls.add(html_name)

    logger.success(f"🏁 Done. Processed: {files_processed} | Skipped: {skipped_count}")

    # Finalizer: Archive extracted_jsons
    archive_path = json_dir.parent / "extracted_jsons.zip"
    logger.info("📦 Archiving extracted_jsons to {}...", archive_path)
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for json_file in json_dir.glob("*.json"):
            zipf.write(json_file, arcname=json_file.name)
    logger.success("✅ JSON archive created: {}", archive_path)

    # Remove the folder after archiving
    if json_dir.exists():
        shutil.rmtree(json_dir)
        logger.info("🗑️ Removed original folder: {}", json_dir)


def process_directory(html_dir: Path, json_dir: Path, force: bool = False):
    """
    Processes all HTML files in a directory.
    Groups color variants.
    """
    json_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📂 Scanning directory: {html_dir}...")

    html_files = list(html_dir.glob("*.html"))
    processed_htmls = set()
    files_processed = 0
    skipped_count = 0

    # Sort files to be deterministic
    for html_path in sorted(html_files):
        if html_path.name in processed_htmls:
            continue

        try:
            content = html_path.read_text(encoding="utf-8")
            data = extract_bike_data(content)

            if data:
                # The extract_bike_data now populates meta.colors from product-related-colors
                # We should ensure all those variants are marked as processed
                for v in data.meta.colors:
                    processed_htmls.add(v.html_path)

                # Also mark current file as processed
                processed_htmls.add(html_path.name)

                json_path = json_dir / html_path.with_suffix(".json").name
                if json_path.exists() and not force:
                    logger.debug(f"⚠️  Skipping {html_path.name}: JSON already exists")
                    skipped_count += 1
                    continue

                json_path.write_text(
                    data.model_dump_json(indent=2),
                    encoding="utf-8",
                )
                logger.debug(f"✅ Saved JSON: {json_path.name}")
                files_processed += 1
            else:
                logger.warning(f"⚠️  Skipped {html_path.name}: No geometry table found")
                skipped_count += 1
                processed_htmls.add(html_path.name)
        except Exception:
            logger.exception(f"🚨 Critical error processing {html_path.name}")
            skipped_count += 1
            processed_htmls.add(html_path.name)

    logger.success(f"🏁 Done. Processed: {files_processed} | Skipped: {skipped_count}")


def main():
    parser = argparse.ArgumentParser(description="Extract Kross bike data from HTML files.")
    parser.add_argument(
        "--input",
        type=Path,
        default=artifacts_dir / "kross" / "raw_htmls",
        help="Directory containing raw HTML files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=artifacts_dir / "kross" / "extracted_jsons",
        help="Directory to save extracted JSON files.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing JSON files.")

    args = parser.parse_args()

    # Priority to archive if it exists
    archive_input = args.input.with_suffix(".zip")
    if archive_input.exists():
        process_archive(archive_input, args.output, args.force)
    elif args.input.exists():
        process_directory(args.input, args.output, args.force)
    else:
        logger.error(f"❌ Input '{args.input}' (directory or zip) not found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
