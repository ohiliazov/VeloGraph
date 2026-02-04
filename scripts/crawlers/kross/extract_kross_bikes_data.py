import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag
from loguru import logger

from app.utils.helpers import extract_number
from scripts.constants import artifacts_dir


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


def extract_bike_data(html: str) -> dict[str, Any]:
    """
    Parses Kross bike HTML.
    Always returns a dictionary with 'meta'.
    If geometry table is found, 'has_geometry' is True and 'specs' are populated.
    """
    # Use 'lxml' for speed
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # --- 1. Extract Metadata (Always done) ---
    bike_meta = {
        "brand": "Kross",
        "model": "",
        "categories": [],
        "model_year": None,
        "wheel_size": None,
        "max_tire_width": None,
    }
    for prop in ["og:title", "og:url", "og:image"]:
        tag = soup.find("meta", property=prop)
        if tag and isinstance(tag, Tag):
            bike_meta[prop] = tag.get("content", "").strip()

    # Extract model name from og:title if it looks like "Model | Kross"
    if "og:title" in bike_meta:
        title = bike_meta["og:title"]
        if " | " in title:
            bike_meta["model"] = title.split(" | ")[0].strip()

    breadcrumbs = soup.find("div", class_="product-breadcrumbs")
    if breadcrumbs:
        # Use a more robust split for the breadcrumb separator
        raw_text = breadcrumbs.get_text(strip=True)
        # The separator is usually something like " / " with non-breaking spaces
        raw_cats = [c.strip() for c in re.split(r"\s*/\s*", raw_text)]
        cleaned_cats = []
        for c in raw_cats:
            c = c.strip()
            if not c:
                continue
            # Check if it's a year
            if c.isdigit() and len(c) == 4 and 2000 <= int(c) <= 2100:
                bike_meta["model_year"] = int(c)
                continue
            cleaned_cats.append(c)
        bike_meta["categories"] = cleaned_cats

    # --- 1b. Extract from Additional Attributes (Specyfikacja) ---
    spec_tables = soup.find_all("table", class_="additional-attributes-table")
    for table in spec_tables:
        for row in table.find_all("tr"):
            title_cell = row.find("td", class_="box-title")
            content_cell = row.find("td", class_="box-content")
            if title_cell and content_cell:
                attr_name = title_cell.get_text(strip=True).lower()
                attr_content = content_cell.get_text(strip=True)

                # Check for max tire width
                if "maksymalna szerokość opony" in attr_name or "max_tire_width" in title_cell.get("class", []):
                    bike_meta["max_tire_width"] = clean_value(attr_content)

                # Check for wheel size (from Opony if not set)
                if not bike_meta["wheel_size"] and ("opony" in attr_name or "tires" in title_cell.get("class", [])):
                    match = re.search(r"(\d{3})x|(\d{2}[.,]\d)\"|(\d{2})\"", attr_content, re.IGNORECASE)
                    if match:
                        val = match.group(1) or match.group(2) or match.group(3)
                        bike_meta["wheel_size"] = normalize_wheel_size(val)

    # --- 2. Find the Geometry Table ---
    target_table = None
    all_tables = soup.find_all("table")

    for table in all_tables:
        thead = table.find("thead")
        if thead:
            first_th = thead.find("th")
            if first_th and "Rozmiar" in first_th.get_text():
                target_table = table
                break

    # Prepare return structure
    result = {
        "meta": bike_meta,
        "sizes": [],
        "specs": {},
        "has_geometry": False,  # Flag to indicate success
    }

    if not target_table:
        return result

    # --- 3. Extract Table Data ---
    bike_sizes: list[str] = []
    bike_specs: dict[str, list[Any]] = {}

    # 3a. Headers (Sizes)
    header_row = target_table.find("thead").find("tr")
    if not header_row:
        return result

    for th in header_row.find_all("th")[1:]:
        size_text = th.get_text(strip=True)
        bike_sizes.append(size_text)

        # If wheel size still not found, try to get it from header like "M (19\") 28\""
        if not bike_meta["wheel_size"]:
            match = re.search(r"(\d{2}[.,]\d)\"|(\d{2})\"", size_text)
            if match:
                # Usually the last one is the wheel size.
                re.findall(r"(\d{2}[.,]\d)\"|(\d{2})\"", size_text)
                # Findall with groups returns tuples if there are multiple groups
                # Let's use a simpler approach
                all_matches = []
                for m in re.finditer(r"(\d{2}[.,]\d)\"|(\d{2})\"", size_text):
                    all_matches.append(m.group(1) or m.group(2))

                if len(all_matches) > 1:
                    bike_meta["wheel_size"] = normalize_wheel_size(all_matches[-1])
                elif len(all_matches) == 1 and "(" not in size_text:
                    bike_meta["wheel_size"] = normalize_wheel_size(all_matches[0])

    # 3b. Rows (Specs)
    tbody = target_table.find("tbody")
    if tbody:
        for row in tbody.find_all("tr"):
            cells = row.find_all("td")

            if not cells:
                continue

            attr_name = cells[0].get_text(strip=True)

            values = []
            for cell in cells[1:]:
                values.append(clean_value(cell.get_text(strip=True)))

            # Integrity check
            if len(values) < len(bike_sizes):
                values.extend([None] * (len(bike_sizes) - len(values)))

            bike_specs[attr_name] = values

            # Extra: if we haven't found wheel size yet, check geometry table row "Rozmiar kół"
            if not bike_meta["wheel_size"] and "rozmiar kół" in attr_name.lower():
                # Take the first non-empty value
                for v in values:
                    if v:
                        v_str = str(v)
                        match = re.search(r"(\d{3})|(\d{2}[.,]\d)|(\d{2})", v_str)
                        if match:
                            bike_meta["wheel_size"] = normalize_wheel_size(match.group(0))
                            break

    # Update result with found data
    result["sizes"] = bike_sizes
    result["specs"] = bike_specs
    result["has_geometry"] = True

    return result


if __name__ == "__main__":
    kross_artifacts = artifacts_dir / "kross"
    html_dir = kross_artifacts / "raw_htmls"
    json_dir = kross_artifacts / "extracted_jsons"
    json_dir.mkdir(parents=True, exist_ok=True)

    if not html_dir.exists():
        logger.error(f"❌ Directory '{html_dir}' not found. Please create it and add HTML files.")
        sys.exit(1)

    logger.info(f"📂 Scanning directory: {html_dir}...")

    files_processed = 0
    skipped_urls = []

    for html_path in html_dir.glob("*.html"):
        try:
            logger.info(f"🚴 Processing: {html_path.name}...")
            content = html_path.read_text(encoding="utf-8")

            data = extract_bike_data(content)

            # Check the flag we created
            if data["has_geometry"]:
                # Remove the internal flag before saving to clean JSON
                del data["has_geometry"]

                json_path = json_dir / html_path.with_suffix(".json").name
                if json_path.exists():
                    logger.warning(f"⚠️  Skipping {html_path.name}: JSON already exists")
                    continue

                json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                logger.success(f"✅ Saved JSON: {json_path.name}")
                files_processed += 1
            else:
                # Now we can safely access meta because data is not None
                url = data["meta"].get("og:url", f"UNKNOWN_URL_{html_path.name}")
                logger.warning(f"⚠️  Skipped {html_path.name}: No geometry table found")
                skipped_urls.append(url)

        except Exception:
            logger.exception(f"🚨 Critical error processing {html_path.name}")

    logger.success(f"🏁 Done. Processed: {files_processed} | Skipped: {len(skipped_urls)}")

    output_skipped = Path("skipped_urls.json")

    if skipped_urls:
        with open(output_skipped, "w", encoding="utf-8") as f:
            json.dump(skipped_urls, f, indent=2, ensure_ascii=False)
            logger.info(f"📝 Saved {len(skipped_urls)} skipped URLs to '{output_skipped}'")
    elif output_skipped.exists():
        logger.info("✅ No skipped URLs found")
        os.remove(output_skipped)
