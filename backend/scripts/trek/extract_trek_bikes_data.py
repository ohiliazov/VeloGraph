import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, ClassVar

from bs4 import BeautifulSoup, SoupStrainer, Tag
from loguru import logger

from backend.scripts.base_extractor import BaseBikeExtractor, BikeMeta, ExtractedBikeData
from backend.scripts.constants import artifacts_dir


class TrekBikeExtractor(BaseBikeExtractor):
    GEO_MAP: ClassVar[dict[str, list[str]]] = {
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

    def __init__(self):
        super().__init__(brand_name="Trek")

    def _extract_meta(self, soup: BeautifulSoup) -> BikeMeta:
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

        # Categories from breadcrumbs
        breadcrumb_links = soup.select('nav[aria-label="Breadcrumb"] a, .breadcrumb a')
        for link in breadcrumb_links:
            cat = link.get_text(strip=True)
            if cat and cat.lower() not in ["home", "rowery", "sklep"]:
                meta_data["categories"].append(cat)

        return BikeMeta(**meta_data)

    def _extract_from_sizing_json(
        self, sizing_data
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
                    for internal_key, labels in self.GEO_MAP.items():
                        if any(label.lower() in header_lower for label in labels):
                            mapped_key = internal_key
                            break

                    if mapped_key:
                        out_specs.setdefault(mapped_key, []).append(self.clean_value(str(cell)))

            if sizes and out_specs:
                return sizes, out_specs

        # Case 2: Heuristic recursive search for other table-like structures
        candidates: list[tuple[list, list]] = []

        def walk(obj):
            if isinstance(obj, dict):
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
                    out.append(
                        str(h.get("label") or h.get("title") or h.get("name") or next(iter(h.values()), "")).strip()
                    )
                else:
                    out.append(str(h).strip())
            return out

        for headers, rows in candidates:
            headers = normalize_headers(headers)
            out_specs: dict[str, list[float | int | str | None]] = {}
            sizes: list[str] = []
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
                        for internal_key, labels in self.GEO_MAP.items():
                            if any(label.lower() in header_lower for label in labels):
                                mapped = internal_key
                                break
                        if not mapped:
                            mapped = header
                        out_specs.setdefault(mapped, []).append(self.clean_value(str(cell)))
                if sizes and out_specs:
                    return sizes, {k: v for k, v in out_specs.items() if k in self.GEO_MAP}
            elif rows and isinstance(rows[0], dict):
                if all(isinstance(r, dict) and ("values" in r or "geometry" in r) for r in rows):
                    for r in rows:
                        label = str(
                            r.get("label") or r.get("size") or r.get("name") or r.get("dimension") or ""
                        ).strip()
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
                            for internal_key, labels in self.GEO_MAP.items():
                                if any(label.lower() in header_lower for label in labels):
                                    mapped = internal_key
                                    break
                            if not mapped:
                                mapped = header
                            out_specs.setdefault(mapped, []).append(self.clean_value(str(cell)))
                    if sizes and out_specs:
                        return sizes, {k: v for k, v in out_specs.items() if k in self.GEO_MAP}
        return None, None

    def extract_bike_data(self, html: str, additional_data: Any = None) -> ExtractedBikeData | None:
        strainer = SoupStrainer(["meta", "div", "table", "ul", "li", "a", "nav", "dt", "dd", "h1", "script"])
        try:
            soup = BeautifulSoup(html, "lxml", parse_only=strainer)
        except Exception:
            soup = BeautifulSoup(html, "html.parser", parse_only=strainer)

        bike_meta = self._extract_meta(soup)
        components = {k: [] for k in self.COMPONENT_KEYWORDS}

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
                    bike_meta.wheel_size = self.normalize_wheel_size(val)

            self._categorize_component(attr_name, attr_content, components)

        bike_sizes: list[str] = []
        bike_specs: dict[str, list[float | int | str | None]] = {}

        # --- Prefer JSON sizing if available ---
        if additional_data:
            sizes, specs = self._extract_from_sizing_json(additional_data)
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
                    for internal_key, labels in self.GEO_MAP.items():
                        if any(label.lower() in header_lower for label in labels):
                            mapped_key = internal_key
                            break

                    if not mapped_key:
                        mapped_key = header

                    if mapped_key not in bike_specs:
                        bike_specs[mapped_key] = []

                    bike_specs[mapped_key].append(self.clean_value(cell.get_text(strip=True)))

            # Wheel size from table if still missing
            if not bike_meta.wheel_size and rows:
                for i, h in enumerate(headers):
                    if "Rozmiar kół" in h:
                        for row in rows:
                            cells = row.find_all(["th", "td"])
                            if len(cells) > i:
                                val = cells[i].get_text(strip=True)
                                bike_meta.wheel_size = self.normalize_wheel_size(val)
                                if bike_meta.wheel_size:
                                    break
                        if bike_meta.wheel_size:
                            break

        return ExtractedBikeData(
            meta=bike_meta,
            build_kit=self._assemble_build_kit(components),
            sizes=bike_sizes,
            specs=self._normalize_specs(bike_specs),
        )

    def _normalize_specs(self, specs: dict[str, list[Any]]) -> dict[str, list[float | int | str | None]]:
        """Trek specific: convert cm to mm for length dimensions."""
        out = {}
        for key, vals in specs.items():
            if key not in self.GEO_MAP:
                continue

            # Keys that are lengths (not angles)
            if key in ["stack", "reach", "TT", "ST", "HT", "CS", "bb_drop", "WB"]:
                new_vals = []
                for v in vals:
                    if isinstance(v, (int, float)):
                        # If value < 150, it's almost certainly cm (e.g., 50.7 stack or 10.0 headtube)
                        if v < 150:
                            new_vals.append(round(v * 10))
                        else:
                            new_vals.append(round(v))
                    else:
                        new_vals.append(v)
                out[key] = new_vals
            else:
                out[key] = vals
        return out

    def _get_additional_data(self, html_name: str, all_names: set[str], archive: zipfile.ZipFile) -> Any:
        slug = Path(html_name).stem
        sizing_json_name = f"{slug}_sizing.json"
        if sizing_json_name in all_names:
            try:
                return json.loads(archive.read(sizing_json_name).decode("utf-8"))
            except Exception:
                logger.warning("⚠️ Failed to load sizing JSON for {}", html_name)
        return None

    def _get_additional_data_dir(self, html_path: Path) -> Any:
        sizing_json_path = html_path.with_name(html_path.stem + "_sizing.json")
        if sizing_json_path.exists():
            try:
                return json.loads(sizing_json_path.read_text(encoding="utf-8"))
            except Exception:
                logger.warning("⚠️ Failed to load sizing JSON for {}", html_path.name)
        return None


def main():
    extractor = TrekBikeExtractor()
    parser = extractor.get_base_parser("trek", artifacts_dir)
    args = parser.parse_args()

    archive_input = args.input.with_suffix(".zip")
    if archive_input.exists():
        extractor.process_archive(archive_input, args.output, args.force)
    elif args.input.exists():
        extractor.process_directory(args.input, args.output, args.force)
    else:
        sys.exit(1)

    extractor.finalize_extraction(args.output)


if __name__ == "__main__":
    main()
