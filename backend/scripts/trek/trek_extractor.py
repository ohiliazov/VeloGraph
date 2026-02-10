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
from backend.utils.helpers import extract_number


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

    def __init__(self, html_path: Path | None = None, json_path: Path | None = None):
        brand_name = "trek"
        html_path = html_path or (artifacts_dir / brand_name / "raw_htmls")
        json_path = json_path or (artifacts_dir / brand_name / "extracted_jsons")
        super().__init__(brand_name="Trek", html_dir=html_path, json_dir=json_path)

    # --- Meta parsers (one function per field) ---
    def _parse_brand(self) -> str:
        return "Trek"

    def _parse_model(self, parser: LexborHTMLParser) -> str:
        # 0) Try user instruction: selected element in "Wybierz swój model"
        for fs in parser.css("fieldset"):
            fs_text = fs.text()
            if "Wybierz swój model" in fs_text or "Wybierz model" in fs_text:
                checked_model = fs.css_first("input[checked]")
                if checked_model:
                    id_val = checked_model.attributes.get("id")
                    label_node = fs.css_first(f'label[for="{id_val}"]')
                    if label_node:
                        txt = label_node.text(strip=True)
                        if txt:
                            model_name = html.unescape(txt).strip()
                            # Clean up common frame variations from model name
                            model_name = re.sub(
                                r"\s*\((Stepover|Midstep|Lowstep|Highstep|Stagger|Damski|Męski)\)$",
                                "",
                                model_name,
                                flags=re.I,
                            )
                            return model_name

        # 1) Try tech header as a fallback
        tech_header = parser.css_first('[qaid="tech__product-name-header"]')
        if tech_header:
            txt = tech_header.text(strip=True)
            if txt:
                model_name = html.unescape(txt).strip()
                model_name = re.sub(
                    r"\s*\((Stepover|Midstep|Lowstep|Highstep|Stagger|Damski|Męski)\)$", "", model_name, flags=re.I
                )
                return model_name

        # 2) Fallback to general model-option radio
        model_input = parser.css_first('input[name="model-option"][checked]')
        if model_input:
            id_val = model_input.attributes.get("id")
            if id_val:
                label_node = parser.css_first(f'label[for="{id_val}"]')
                if label_node:
                    txt = label_node.text(strip=True)
                    if txt:
                        model_name = html.unescape(txt).strip()
                        model_name = re.sub(
                            r"\s*\((Stepover|Midstep|Lowstep|Highstep|Stagger|Damski|Męski)\)$",
                            "",
                            model_name,
                            flags=re.I,
                        )
                        return model_name

        # 3) Try JSON-LD Product data first (usually contains the most concrete model name)
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
                    model_name = html.unescape(res).strip()
                    model_name = re.sub(
                        r"\s*\((Stepover|Midstep|Lowstep|Highstep|Stagger|Damski|Męski)\)$", "", model_name, flags=re.I
                    )
                    return model_name
            except Exception:
                continue

        # 4) H1 product title candidates (PDP pages)
        node = parser.css_first('h1[qaid="pdp-product-title"]')
        if node:
            txt = node.text(strip=True)
            if txt:
                model_name = html.unescape(txt).strip()
                model_name = re.sub(
                    r"\s*\((Stepover|Midstep|Lowstep|Highstep|Stagger|Damski|Męski)\)$", "", model_name, flags=re.I
                )
                return model_name

        # 5) Fallback to other H1s
        for sel in ["h1.product-title", "h1.product-name", "h1.pdp__title", "h1.page-title", "h1"]:
            node = parser.css_first(sel)
            if node:
                txt = node.text(strip=True)
                if txt and txt.lower() not in {"menu", "koszyk"}:
                    return html.unescape(txt)

        # 6) Breadcrumb last item
        crumbs = parser.css('nav[aria-label="Breadcrumb"] a, .breadcrumb a')
        if crumbs:
            last = crumbs[-1].text(strip=True)
            if last and last.lower() not in {"home", "rowery", "sklep"}:
                return html.unescape(last)

        return ""

    def _parse_frame_name(self, parser: LexborHTMLParser) -> str | None:
        # 1) Try general sub-family-option radio (User suggestion)
        # Note: we search ONLY in #app or main content area to avoid nav cards
        content_area = parser.css_first("#app, main") or parser
        frame_input = content_area.css_first('input[name^="sub-family-option-"][checked]')
        if frame_input:
            id_val = frame_input.attributes.get("id")
            if id_val:
                label_node = content_area.css_first(f'label[for="{id_val}"]')
                if label_node:
                    return html.unescape(label_node.text(strip=True)).strip()

        # 2) User instruction fallback: div next to "Wybierz rodzaj ramy"
        for fs in content_area.css("fieldset"):
            fs_text = fs.text()
            if "Wybierz rodzaj ramy" in fs_text:
                checked_frame = fs.css_first("input[checked]")
                if checked_frame:
                    id_val = checked_frame.attributes.get("id")
                    label_node = fs.css_first(f'label[for="{id_val}"]')
                    if label_node:
                        txt = label_node.text(strip=True)
                        if txt:
                            return html.unescape(txt).strip()

        # 3) Extract from technical header if it has parenthesis
        tech_header = content_area.css_first('[qaid="tech__product-name-header"]')
        if tech_header:
            txt = tech_header.text(strip=True)
            m = re.search(r"\((Stepover|Midstep|Lowstep|Highstep|Stagger|Damski|Męski)\)", txt, flags=re.I)
            if m:
                return m.group(1).capitalize()

        # 4) Extract from title/h1 if it contains frame variation in parentheses
        node = content_area.css_first('h1[qaid="pdp-product-title"]')
        if node:
            txt = node.text(strip=True)
            m = re.search(r"\((Stepover|Midstep|Lowstep|Highstep|Stagger|Damski|Męski)\)", txt, flags=re.I)
            if m:
                return m.group(1).capitalize()

        return None

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
            if cat and cat.lower() not in ["home", "rowery", "sklep", "diamant"]:
                out.append(cat)
        # If no categories from breadcrumbs, try product title keywords
        if not out:
            title = parser.css_first("h1")
            if title:
                title_txt = title.text(strip=True).lower()
                if "dziecięcy" in title_txt or "kids" in title_txt:
                    out.append("Dziecięce")
        return out

    def _parse_model_year(self, parser: LexborHTMLParser) -> int | None:
        # Try to find year in name or tech header
        full_text = ""
        tech_header = parser.css_first('[qaid="tech__product-name-header"]')
        if tech_header:
            full_text += tech_header.text()
        h1 = parser.css_first("h1")
        if h1:
            full_text += h1.text()

        years = re.findall(r"\b(20\d{2})\b", full_text)
        if years:
            return int(years[0])
        return None

    def _parse_wheel_size(self, parser: LexborHTMLParser) -> str | None:
        # Check specs for wheel size
        dts = parser.css("dt.details-list__title")
        for dt in dts:
            dt_text = dt.text(strip=True).lower()
            if "koło" in dt_text or "opona" in dt_text or "wheel" in dt_text or "tire" in dt_text:
                dd = dt.next
                while dd and dd.tag != "dd":
                    dd = dd.next
                if dd:
                    txt = dd.text(strip=True)
                    m = re.search(r'(\d{2,3})["”c]?', txt)
                    if m:
                        return self.normalize_wheel_size(m.group(1))
        return None

    def _parse_max_tire_width(self, parser: LexborHTMLParser) -> float | str | None:
        # We MUST avoid navigation menu items
        content_area = parser.css_first("#app, main") or parser

        # 1) Try specialized qaid for feature specs (usually PDP row)
        # Search multiple icons as the order varies by bike type
        for i in range(6):
            qaid = f"product-family-feature-spec-icon-{i}"
            icon = content_area.css_first(f'[qaid="{qaid}"]')
            if icon:
                curr = icon.parent
                while curr and curr.tag != "li" and curr.tag != "div":
                    curr = curr.parent
                if curr:
                    txt = curr.text(strip=True).lower()
                    # Look for tire clearance markers
                    if any(k in txt for k in ["opon", "tire", "clearance", "prześwit"]):
                        m = re.search(r"(\d+(?:\.\d+)?)\s*mm", txt, flags=re.I)
                        if m:
                            return extract_number(m.group(1))

        # 2) Fallback to spec table or description
        dts = content_area.css("dt.details-list__title")
        for dt in dts:
            dt_text = dt.text(strip=True).lower()
            if "max" in dt_text and "opon" in dt_text:
                dd = dt.next
                while dd and dd.tag != "dd":
                    dd = dd.next
                if dd:
                    txt = dd.text(strip=True)
                    m = re.search(r"(\d+(?:\.\d+)?)\s*mm", txt, flags=re.I)
                    if m:
                        return extract_number(m.group(1))
        return None

    def _parse_material(self, parser: LexborHTMLParser) -> str | None:
        # IMPORTANT: Exclude navigation/header to avoid false positives from mega-menu
        content_area = parser.css_first("main, #app") or parser

        # 0) Try specialized qaid for feature specs (Icons 0-5)
        # Order varies, so we check text content for material keywords
        for i in range(6):
            qaid = f"product-family-feature-spec-icon-{i}"
            icon = content_area.css_first(f'[qaid="{qaid}"]')
            if icon:
                curr = icon.parent
                while curr and curr.tag != "li" and curr.tag != "div":
                    curr = curr.parent
                if curr:
                    txt = curr.text(strip=True)
                    if any(
                        k in txt.lower()
                        for k in ["carbon", "węglow", "aluminium", "aluminum", "stal", "steel", "oclv", "alpha"]
                    ):
                        mat = self._clean_material(html.unescape(txt))
                        if mat:
                            return mat

        # 1) Try short spec from configurator
        for node in content_area.css('dd[qaid*="-shortSpecFrame-value"], [qaid="shortSpecFrame-value"]'):
            mat = self._clean_material(html.unescape(node.text(strip=True)))
            if mat:
                return mat

        # 2) Fallback to spec table: Look for "Rama" or "Materiał ramy"
        dts = content_area.css("dt.details-list__title")
        for dt in dts:
            dt_text = dt.text(strip=True)
            if dt_text in ["Rama", "Materiał ramy", "Frame"]:
                dd = dt.next
                while dd and dd.tag != "dd":
                    dd = dd.next
                if dd:
                    mat = self._clean_material(dd.text(strip=True))
                    if mat:
                        return mat

        # 3) Heuristic: look for material keywords in li/span, EXCLUDING nav
        for node in content_area.css("li span, .spec-attribute"):
            # Exclude elements inside nav/header
            is_in_nav = False
            curr = node.parent
            while curr:
                if curr.tag in {"nav", "header"} or "nav" in curr.attributes.get("class", "").lower():
                    is_in_nav = True
                    break
                curr = curr.parent
            if is_in_nav:
                continue

            txt = node.text(strip=True)
            # Look for OCLV or Alpha specifically
            if "OCLV" in txt or "Alpha" in txt:
                return self._clean_material(txt)

            if txt in ["Aluminium", "Karbon", "Carbon", "Stal", "Steel"]:
                return txt

        return None

    def _clean_material(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"^(Rama|Materiał ramy|Frame):\s*", "", text, flags=re.I)

        # Handle Trek OCLV Carbon
        if "OCLV" in text:
            m = re.search(r"OCLV\s*(\d+)", text, flags=re.I)
            if m:
                return f"Carbon OCLV {m.group(1)}"
            return "Carbon OCLV"

        # Handle Alpha Aluminum
        if "Alpha" in text and ("Aluminum" in text or "Aluminium" in text):
            m = re.search(r"Alpha\s*(\d+)", text, flags=re.I)
            if m:
                return f"Aluminum Alpha {m.group(1)}"
            return "Aluminum Alpha"

        # Prefer short versions if long
        if ("Aluminum" in text or "Aluminium" in text) and len(text) > 30:
            return "Aluminum"
        if ("Carbon" in text or "Karbon" in text or "włókno węglowe" in text) and len(text) > 30:
            return "Carbon"

        return text.strip()

    def _parse_colors(self, parser: LexborHTMLParser) -> list[ColorVariant]:
        out: list[ColorVariant] = []

        # 1) Check tech info dropdown for clean color names
        tech_color_select = parser.css_first("select#tech-info-bike_colorSwatch")
        if tech_color_select:
            for opt in tech_color_select.css("option"):
                color_name = opt.text(strip=True)
                if color_name:
                    out.append(ColorVariant(html_path="", color=color_name, url=""))
            if out:
                return out

        # 2) Fallback to attribute-color div
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
                    out.append(ColorVariant(html_path="", color=color_name, url=""))
        return out

    def _extract_meta(self, parser: LexborHTMLParser) -> BikeMeta:
        return BikeMeta(
            brand=self._parse_brand(),
            model=self._parse_model(parser),
            frame_name=self._parse_frame_name(parser),
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
    parser = BaseBikeExtractor.get_base_parser("trek", artifacts_dir)
    args = parser.parse_args()
    extractor = TrekBikeExtractor(html_path=args.input, json_path=args.output)

    if args.input.exists():
        extractor.process_directory(args.input, args.output, args.force, args.filename)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
