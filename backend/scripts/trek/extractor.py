import html
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from selectolax.lexbor import LexborHTMLParser

from backend.scripts.base import BaseBikeExtractor, BikeMeta, ColorVariant, ExtractedBikeData
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

    # --- Meta parsers (one function per field) ---
    def _parse_brand(self) -> str:
        return "Trek"

    def _parse_model(self, parser: LexborHTMLParser) -> str:
        # 1) Try JSON-LD Product data first (usually contains the most concrete model name)
        def _try_from_ld(obj: Any) -> str | None:
            try:
                if isinstance(obj, dict):
                    t = str(obj.get("@type") or obj.get("type") or "").lower()
                    if t in {"product", "productmodel", "bike", "bicycle"} and obj.get("name"):
                        return str(obj.get("name")).strip()
                    if "@graph" in obj and isinstance(obj["@graph"], list):
                        for it in obj["@graph"]:
                            res = _try_from_ld(it)
                            if res:
                                return res
            except Exception:
                pass
            return None

        for sc in parser.css('script[type="application/ld+json"]'):
            try:
                data = json.loads(sc.text())
                res = (
                    _try_from_ld(data)
                    if not isinstance(data, list)
                    else next((_try_from_ld(it) for it in data if _try_from_ld(it)), None)
                )
                if res:
                    return html.unescape(res)
            except Exception:
                continue

        # 2) H1 product title candidates (PDP pages)
        # Prioritize specific qaid if available
        node = parser.css_first('h1[qaid="pdp-product-title"]')
        if node:
            txt = node.text(strip=True)
            if txt:
                return html.unescape(txt)

        # 3) Check for generic frameset name in URL as a fallback or component
        # e.g. /.../madone/madone-sl/madone-sl-7-gen-8/p/57664/
        source_url = self._parse_source_url(parser)
        if source_url:
            path_parts = source_url.split("?")[0].rstrip("/").split("/")
            if len(path_parts) >= 3 and path_parts[-2] == "p":
                model_slug = path_parts[-3]
                return model_slug.replace("-", " ").title()

        # 4) Fallback to other H1s
        for sel in ["h1.product-title", "h1.product-name", "h1.pdp__title", "h1.page-title", "h1"]:
            node = parser.css_first(sel)
            if node:
                txt = node.text(strip=True)
                if txt and txt.lower() not in {"menu", "koszyk"}:
                    return html.unescape(txt)

        # 5) Breadcrumb last item
        crumbs = parser.css('nav[aria-label="Breadcrumb"] a, .breadcrumb a')
        if crumbs:
            last = crumbs[-1].text(strip=True)
            if last and last.lower() not in {"home", "rowery", "sklep"}:
                return html.unescape(last)

        return ""

    def _parse_source_url(self, parser: LexborHTMLParser) -> str:
        # Prefer canonical link
        canonical = parser.css_first('link[rel="canonical"]')
        if canonical:
            href = canonical.attributes.get("href", "").strip()
            if href:
                return href
        # Fallback to JSON-LD Product.url
        for sc in parser.css('script[type="application/ld+json"]'):
            try:
                data = json.loads(sc.text())
            except Exception:
                continue
            objs = data if isinstance(data, list) else [data]
            for obj in objs:
                if isinstance(obj, dict) and obj.get("url"):
                    return str(obj.get("url")).strip()
                if isinstance(obj, dict) and "@graph" in obj and isinstance(obj["@graph"], list):
                    for it in obj["@graph"]:
                        if isinstance(it, dict) and it.get("url"):
                            return str(it.get("url")).strip()
        # Fallback to OG url if present
        url_tag = parser.css_first('meta[property="og:url"]')
        if url_tag:
            return url_tag.attributes.get("content", "").strip()
        return ""

    def _parse_categories(self, parser: LexborHTMLParser) -> list[str]:
        out: list[str] = []
        for link in parser.css('nav[aria-label="Breadcrumb"] a, .breadcrumb a'):
            cat = link.text(strip=True)
            if cat and cat.lower() not in ["home", "rowery", "sklep"]:
                out.append(cat)
        return out

    def _parse_model_year(self, parser: LexborHTMLParser) -> int | None:
        return None

    def _parse_wheel_size(self, parser: LexborHTMLParser) -> str | None:
        return None

    def _parse_max_tire_width(self, parser: LexborHTMLParser) -> float | str | None:
        return None

    def _parse_material(self, parser: LexborHTMLParser) -> str | None:
        # Trek specs are in dt/dd pairs. Look for "Rama" (Frame)
        dts = parser.css("dt.details-list__title")
        for dt in dts:
            if "Rama" in dt.text():
                dd = dt.next
                while dd and dd.tag != "dd":
                    dd = dd.next
                if dd:
                    return dd.text(strip=True)
        return None

    def _parse_colors(self, parser: LexborHTMLParser) -> list[ColorVariant]:
        out: list[ColorVariant] = []
        # Use div with class attribute-color as requested
        attr_color_div = parser.css_first("div.attribute-color")
        if attr_color_div:
            # The selected color name is often in .variantName
            variant_name_node = attr_color_div.css_first(".variantName")
            if variant_name_node:
                color_text = variant_name_node.text(strip=True)
                # Format is usually "Kolor/Color Name"
                if "/" in color_text:
                    color_name = color_text.split("/", 1)[1].strip()
                else:
                    color_name = color_text.replace("Kolor", "").strip()
                if color_name:
                    # Record current color. We don't have URLs for other variants here,
                    # but capturing the current one is better than nothing.
                    out.append(ColorVariant(html_path="", color=color_name, url=""))
        return out

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

    def _extract_geometry(
        self, parser: LexborHTMLParser, additional_data: Any
    ) -> tuple[list[str], dict[str, list[float | int | str | None]]]:
        # Prefer JSON sizing if available
        if additional_data:
            sizes, specs = self._extract_from_sizing_json(additional_data)
            if sizes and specs:
                return sizes, specs

        # Fallback to Geometry Table in HTML
        bike_sizes: list[str] = []
        bike_specs: dict[str, list[float | int | str | None]] = {}

        target_table = parser.css_first("table#sizing-table") or parser.css_first("table.sizing-table__table")
        if not target_table:
            return [], {}

        thead = target_table.css_first("thead")
        if not thead:
            return [], {}

        header_row = thead.css_first("tr")
        headers = [th.text(strip=True) for th in header_row.css("th, td")] if header_row else []

        tbody = target_table.css_first("tbody")
        if not tbody:
            return [], {}

        rows = tbody.css("tr")
        for row in rows:
            cells = row.css("th, td")
            if not cells:
                continue
            size_label = cells[0].text(strip=True)

            # Include position if present among headers
            pos_idx = -1
            for i, h in enumerate(headers):
                if "Położenie" in h:
                    pos_idx = i
                    break

            full_size_label = size_label
            if pos_idx != -1 and pos_idx < len(cells):
                pos_val = cells[pos_idx].text(strip=True)
                if pos_val:
                    full_size_label = f"{size_label} ({pos_val})"

            bike_sizes.append(full_size_label)

            for i, cell in enumerate(cells[1:], start=1):
                if i >= len(headers):
                    continue
                header = headers[i]
                mapped_key = None
                header_lower = header.lower()
                for internal_key, labels in self.GEO_MAP.items():
                    if any(label.lower() in header_lower for label in labels):
                        mapped_key = internal_key
                        break
                if not mapped_key:
                    mapped_key = header
                bike_specs.setdefault(mapped_key, []).append(self.clean_value(cell.text(strip=True)))

        return bike_sizes, bike_specs

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
        parser = LexborHTMLParser(html)

        bike_meta = self._extract_meta(parser)
        components = {k: [] for k in self.COMPONENT_KEYWORDS}

        # --- 1. Extract Specifications (dt/dd) ---
        dts = parser.css("dt.details-list__title")
        for dt in dts:
            dd = dt.next
            while dd and dd.tag != "dd":
                dd = dd.next
            if not dd:
                continue
            attr_name = dt.text(strip=True)
            attr_content = dd.text(strip=True)
            self._categorize_component(attr_name, attr_content, components)

        # --- 2. Geometry (single dedicated function) ---
        bike_sizes, bike_specs = self._extract_geometry(parser, additional_data)
        if not bike_sizes:
            return None

        # --- 3. Wheel size fallback from specs if still missing ---
        if not bike_meta.wheel_size:
            for attr, vals in bike_specs.items():
                if "rozmiar kół" in str(attr).lower() and vals:
                    for v in vals:
                        if not v:
                            continue
                        m = re.search(r"(\d{3})|(\d{2}[.,]\d)|(\d{2})", str(v))
                        if m:
                            bike_meta.wheel_size = self.normalize_wheel_size(m.group(0))
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
        extractor.process_archive(archive_input, args.output, args.force, args.filename)
    elif args.input.exists():
        extractor.process_directory(args.input, args.output, args.force, args.filename)
    else:
        sys.exit(1)

    if not args.filename and args.archive:
        extractor.finalize_extraction(args.output)


if __name__ == "__main__":
    main()
