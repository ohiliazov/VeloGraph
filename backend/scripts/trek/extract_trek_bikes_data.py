import argparse
import json
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


class TrekColorVariant(BaseModel):
    html_path: str
    color: str
    url: str


class TrekBikeMeta(BaseModel):
    brand: str = "Trek"
    model: str
    categories: list[str] = Field(default_factory=list)
    model_year: int | None = None
    wheel_size: str | None = None
    max_tire_width: float | str | None = None
    material: str | None = None
    source_url: str = ""
    colors: list[TrekColorVariant] = Field(default_factory=list)


class ExtractedBikeData(BaseModel):
    meta: TrekBikeMeta
    build_kit: BuildKit
    sizes: list[str]
    specs: dict[str, list[float | int | str | None]]


# --- Constants ---
GEO_MAP = {
    "stack": ["Stack", "Wysokość ramy", "geometryFrameStack", "N —"],
    "reach": ["Reach", "Rozstaw ramy", "geometryFrameReach", "M —"],
    "TT": ["Efektywna długość górnej rury", "geometryEffToptube", "E —"],
    "ST": ["Rura podsiodłowa", "geometrySeattube", "A —"],
    "HT": ["Długość główki ramy", "geometryLengthHeadtube", "C —"],
    "CS": ["Długość widełek", "Długość tylnego trójkąta", "geometryLengthChainstay", "H —"],
    "HA": ["Kąt główki ramy", "geometryAngleHead", "D —"],
    "SA": ["Kąt nachylenia rury podsiodłowej", "geometryAngleSeattube", "B —"],
    "bb_drop": ["Obniżenie suportu", "geometryBBDrop", "G —"],
    "WB": ["Rozstaw kół", "geometryWheelbase", "K —"],
}

COMPONENT_KEYWORDS = {
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
    "wheelset": {"piasta", "obręcze", "obręcz", "szprychy", "koła", "koło"},
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


def clean_value(value: str) -> str | int | float:
    if not value:
        return ""
    # Remove degree symbol
    value = value.replace("°", "")
    try:
        return extract_number(value)
    except ValueError:
        return value.strip()


def normalize_wheel_size(value: str | int | float | None) -> str | None:
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


def _extract_meta(soup: BeautifulSoup) -> TrekBikeMeta:
    meta_data = {
        "brand": "Trek",
        "model": "",
        "categories": [],
        "model_year": None,
        "wheel_size": None,
        "max_tire_width": None,
        "material": None,
        "source_url": "",
    }

    # OG tags
    title_tag = soup.find("meta", property="og:title")
    if title_tag and isinstance(title_tag, Tag):
        title = title_tag.get("content", "").strip()
        # Remove " - Trek Bikes (PL)"
        title = re.sub(r"\s*-\s*Trek Bikes.*", "", title, flags=re.IGNORECASE)
        meta_data["model"] = title

    url_tag = soup.find("meta", property="og:url")
    if url_tag and isinstance(url_tag, Tag):
        meta_data["source_url"] = url_tag.get("content", "").strip()
        # Try to extract year from URL if present (Trek sometimes has it)
        # But usually they don't have year in the slug.

    # Categories from breadcrumbs
    # Trek usually has breadcrumbs in a <nav> or a specific list
    # Based on the grep, I saw some nav-related classes
    breadcrumb_links = soup.select('nav[aria-label="Breadcrumb"] a, .breadcrumb a')
    for link in breadcrumb_links:
        cat = link.get_text(strip=True)
        if cat and cat.lower() not in ["home", "rowery", "sklep"]:
            meta_data["categories"].append(cat)

    return TrekBikeMeta(**meta_data)


def _categorize_component(attr_name: str, attr_content: str, components: dict[str, list[str]]):
    attr_lower = attr_name.lower()
    for cat, keywords in COMPONENT_KEYWORDS.items():
        if any(kw in attr_lower for kw in keywords):
            if cat == "tires":
                components[cat].append(attr_content)
            else:
                components[cat].append(f"{attr_name.capitalize()}: {attr_content}")
            return True
    return False


def _assemble_build_kit(components: dict[str, list[str]]) -> BuildKit:
    bk_data = {k: " | ".join(dict.fromkeys(v)) if v else None for k, v in components.items()}
    bk_data["name"] = "Standard Build"
    if components["groupset"]:
        rd = next((s for s in components["groupset"] if "Przerzutka tylna" in s or "Przerzutka tył" in s), None)
        if rd and ": " in rd:
            rd_val = rd.split(": ", 1)[1]
            words = rd_val.split()
            if len(words) >= 2:
                bk_data["name"] = " ".join(words[:2])
            else:
                bk_data["name"] = rd_val
    return BuildKit(**bk_data)


def _extract_from_sizing_json(
    sizing_data,
) -> tuple[list[str], dict[str, list[float | int | str | None]]] | tuple[None, None]:
    """Attempt to extract sizes and specs from Trek sizing JSON structure."""
    if not sizing_data or not isinstance(sizing_data, dict):
        return None, None

    # Case 1: Trek specific structure (geometryDataHeaders + geometryData)
    headers = sizing_data.get("geometryDataHeaders")
    data = sizing_data.get("geometryData")
    if headers and data and isinstance(headers, list) and isinstance(data, list):
        out_specs = {}
        sizes = []

        # Determine size index
        size_idx = -1
        for i, h in enumerate(headers):
            if h in ["geometryFrameSizeLetter", "geometryFrameSizeNumber"]:
                size_idx = i
                break
        if size_idx == -1:
            size_idx = 0

        for item in data:
            row = item.get("geometry")
            if not row or not isinstance(row, list):
                continue

            label = str(row[size_idx]).strip() if size_idx < len(row) else f"Size {len(sizes)}"
            sizes.append(label)

            for i, cell in enumerate(row):
                if i >= len(headers):
                    continue
                header = headers[i]

                mapped_key = None
                header_lower = header.lower()
                for internal_key, labels in GEO_MAP.items():
                    if any(label.lower() in header_lower for label in labels):
                        mapped_key = internal_key
                        break

                if mapped_key:
                    out_specs.setdefault(mapped_key, []).append(clean_value(str(cell)))

        if sizes and out_specs:
            return sizes, out_specs

    # Case 2: Heuristic recursive search for other table-like structures
    candidates: list[tuple[list, list]] = []

    def walk(obj):
        if isinstance(obj, dict):
            # Common patterns: headers+rows or columns+rows/body
            if ("headers" in obj or "columns" in obj) and ("rows" in obj or "body" in obj):
                headers = obj.get("headers") or obj.get("columns") or []
                rows = obj.get("rows") or obj.get("body") or []
                if isinstance(headers, list) and isinstance(rows, list) and rows:
                    candidates.append((headers, rows))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(sizing_data)

    def normalize_headers(hs):
        out = []
        for h in hs:
            if isinstance(h, dict):
                out.append(str(h.get("label") or h.get("title") or h.get("name") or next(iter(h.values()), "")).strip())
            else:
                out.append(str(h).strip())
        return out

    for headers, rows in candidates:
        headers = normalize_headers(headers)
        out_specs: dict[str, list[float | int | str | None]] = {}
        sizes: list[str] = []
        # Expect first column to be size label
        if rows and isinstance(rows[0], list):
            for r in rows:
                if not isinstance(r, list):
                    break
                label = str(r[0]).strip() if r else ""
                if label:
                    sizes.append(label)
                for i, cell in enumerate(r[1:], start=1):
                    if i >= len(headers):
                        continue
                    header = headers[i]
                    mapped = None
                    header_lower = header.lower()
                    for internal_key, labels in GEO_MAP.items():
                        if any(label.lower() in header_lower for label in labels):
                            mapped = internal_key
                            break
                    if not mapped:
                        mapped = header
                    out_specs.setdefault(mapped, []).append(clean_value(str(cell)))
            if sizes and out_specs:
                return sizes, {k: v for k, v in out_specs.items() if k in GEO_MAP}
        elif rows and isinstance(rows[0], dict):
            # Try rows with 'values' list
            if all(isinstance(r, dict) and ("values" in r or "geometry" in r) for r in rows):
                for r in rows:
                    label = str(r.get("label") or r.get("size") or r.get("name") or r.get("dimension") or "").strip()
                    values = r.get("values") or r.get("geometry") or []
                    if not label and values:
                        label = str(values[0]).strip()
                    if label:
                        sizes.append(label)

                    for i, cell in enumerate(values):
                        if i >= len(headers):
                            continue
                        header = headers[i]
                        mapped = None
                        header_lower = header.lower()
                        for internal_key, labels in GEO_MAP.items():
                            if any(label.lower() in header_lower for label in labels):
                                mapped = internal_key
                                break
                        if not mapped:
                            mapped = header
                        out_specs.setdefault(mapped, []).append(clean_value(str(cell)))
                if sizes and out_specs:
                    return sizes, {k: v for k, v in out_specs.items() if k in GEO_MAP}
    return None, None


def extract_bike_data(html: str, sizing_json: dict | None = None) -> ExtractedBikeData | None:
    strainer = SoupStrainer(["meta", "div", "table", "ul", "li", "a", "nav", "dt", "dd", "h1", "script"])
    try:
        soup = BeautifulSoup(html, "lxml", parse_only=strainer)
    except Exception:
        soup = BeautifulSoup(html, "html.parser", parse_only=strainer)

    bike_meta = _extract_meta(soup)
    components = {k: [] for k in COMPONENT_KEYWORDS}

    # --- 1. Extract Specifications (dt/dd) ---
    dts = soup.find_all("dt", class_="details-list__title")
    for dt in dts:
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue

        attr_name = dt.get_text(strip=True)
        attr_content = dd.get_text(strip=True)
        attr_lower = attr_name.lower()

        if "rama" in attr_lower and not bike_meta.material:
            bike_meta.material = attr_content
        elif "opony" in attr_lower and not bike_meta.wheel_size:
            match = re.search(r"(\d{3})x|(\d{2}[.,]\d)\"|(\d{2})\"", attr_content)
            if match:
                val = match.group(1) or match.group(2) or match.group(3)
                bike_meta.wheel_size = normalize_wheel_size(val)

        _categorize_component(attr_name, attr_content, components)

    bike_sizes: list[str] = []
    bike_specs: dict[str, list[float | int | str | None]] = {}

    # --- Prefer JSON sizing if available ---
    if sizing_json:
        sizes, specs = _extract_from_sizing_json(sizing_json)
        if sizes and specs:
            bike_sizes = sizes
            bike_specs = specs

    # --- Fallback to Geometry Table in HTML ---
    if not bike_sizes:
        target_table = soup.find("table", id="sizing-table") or soup.find("table", class_="sizing-table__table")
        if not target_table:
            return None

        # Headers
        thead = target_table.find("thead")
        if not thead:
            return None

        header_row = thead.find("tr")
        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

        # Body
        tbody = target_table.find("tbody")
        if not tbody:
            return None

        rows = tbody.find_all("tr")
        for row in rows:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue

            # In Trek's table, sizes are in the first column
            size_label = cells[0].get_text(strip=True)

            # Include position if present among headers
            pos_idx = -1
            for i, h in enumerate(headers):
                if "Położenie" in h:
                    pos_idx = i
                    break

            full_size_label = size_label
            if pos_idx != -1 and pos_idx < len(cells):
                pos_val = cells[pos_idx].get_text(strip=True)
                if pos_val:
                    full_size_label = f"{size_label} ({pos_val})"

            bike_sizes.append(full_size_label)

            for i, cell in enumerate(cells[1:], start=1):
                if i >= len(headers):
                    continue
                header = headers[i]
                # Map header to standardized key
                mapped_key = None
                header_lower = header.lower()
                for internal_key, labels in GEO_MAP.items():
                    if any(label.lower() in header_lower for label in labels):
                        mapped_key = internal_key
                        break

                if not mapped_key:
                    mapped_key = header

                if mapped_key not in bike_specs:
                    bike_specs[mapped_key] = []

                bike_specs[mapped_key].append(clean_value(cell.get_text(strip=True)))

        # Wheel size from table if still missing
        if not bike_meta.wheel_size and rows:
            for i, h in enumerate(headers):
                if "Rozmiar kół" in h:
                    for row in rows:
                        cells = row.find_all(["th", "td"])
                        if len(cells) > i:
                            val = cells[i].get_text(strip=True)
                            bike_meta.wheel_size = normalize_wheel_size(val)
                            if bike_meta.wheel_size:
                                break
                    if bike_meta.wheel_size:
                        break

    return ExtractedBikeData(
        meta=bike_meta,
        build_kit=_assemble_build_kit(components),
        sizes=bike_sizes,
        specs={k: v for k, v in bike_specs.items() if k in GEO_MAP},
    )


def finalize_extraction(json_dir: Path):
    """
    Archives extracted_jsons to a zip file and removes the original folder.
    """
    if not json_dir.exists():
        logger.warning(f"⚠️ Cannot finalize: {json_dir} does not exist")
        return

    archive_path = json_dir.parent / "extracted_jsons.zip"
    logger.info("📦 Archiving extracted_jsons to {}...", archive_path)

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Sort files to be deterministic in zip
        for json_file in sorted(json_dir.glob("*.json")):
            zipf.write(json_file, arcname=json_file.name)

    logger.success("✅ JSON archive created: {}", archive_path)

    # Remove the folder after archiving
    shutil.rmtree(json_dir)
    logger.info("🗑️ Removed original folder: {}", json_dir)


def process_archive(html_zip: Path, json_dir: Path, force: bool = False):
    json_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📦 Scanning archive: {html_zip}...")

    files_processed = 0
    skipped_count = 0

    with zipfile.ZipFile(html_zip, "r") as z:
        names = set(z.namelist())
        html_files = sorted([n for n in names if n.endswith(".html")])
        total = len(html_files)
        for idx, html_name in enumerate(html_files, 1):
            try:
                logger.info(f"📄 [{idx}/{total}] Processing {html_name}...")
                content = z.read(html_name).decode("utf-8")
                slug = Path(html_name).stem
                sizing_json_name = f"{slug}_sizing.json"
                sizing_json = None
                if sizing_json_name in names:
                    try:
                        sizing_json = json.loads(z.read(sizing_json_name).decode("utf-8"))
                    except Exception:
                        logger.warning("⚠️ Failed to load sizing JSON for {}", html_name)
                data = extract_bike_data(content, sizing_json)
                if data:
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
            except Exception:
                logger.exception(f"🚨 Error processing {html_name}")
                skipped_count += 1

    logger.success(f"🏁 Done. Processed: {files_processed} | Skipped: {skipped_count}")


def process_directory(html_dir: Path, json_dir: Path, force: bool = False):
    json_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📂 Scanning directory: {html_dir}...")
    html_files = sorted(list(html_dir.glob("*.html")))
    total = len(html_files)
    files_processed = 0
    skipped_count = 0
    for idx, html_path in enumerate(html_files, 1):
        try:
            logger.info(f"📄 [{idx}/{total}] Processing {html_path.name}...")
            content = html_path.read_text(encoding="utf-8")
            sizing_json_path = html_path.with_name(html_path.stem + "_sizing.json")
            sizing_json = None
            if sizing_json_path.exists():
                try:
                    sizing_json = json.loads(sizing_json_path.read_text(encoding="utf-8"))
                except Exception:
                    logger.warning("⚠️ Failed to load sizing JSON for {}", html_path.name)
            data = extract_bike_data(content, sizing_json)
            if data:
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
        except Exception:
            logger.exception(f"🚨 Error processing {html_path.name}")
            skipped_count += 1
    logger.success(f"🏁 Done. Processed: {files_processed} | Skipped: {skipped_count}")


def main():
    parser = argparse.ArgumentParser(description="Extract Trek bike data from HTML files.")
    parser.add_argument(
        "--input", type=Path, default=artifacts_dir / "trek" / "raw_htmls", help="Directory containing raw HTML files."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=artifacts_dir / "trek" / "extracted_jsons",
        help="Directory to save extracted JSON files.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing JSON files.")
    args = parser.parse_args()
    archive_input = args.input.with_suffix(".zip")
    if archive_input.exists():
        process_archive(archive_input, args.output, args.force)
    elif args.input.exists():
        process_directory(args.input, args.output, args.force)
    else:
        logger.error(f"❌ Input '{args.input}' not found.")
        sys.exit(1)

    # Always finalize (archive and cleanup)
    finalize_extraction(args.output)


if __name__ == "__main__":
    main()
