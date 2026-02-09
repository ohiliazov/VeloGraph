import re
import sys
from typing import Any, ClassVar

from bs4 import BeautifulSoup, SoupStrainer, Tag

from backend.scripts.base import BaseBikeExtractor, BikeMeta, ColorVariant, ExtractedBikeData
from backend.scripts.constants import artifacts_dir


class KrossBikeExtractor(BaseBikeExtractor):
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

    def __init__(self):
        super().__init__(brand_name="Kross")

    def _extract_meta(self, soup: BeautifulSoup) -> BikeMeta:
        """Extracts basic metadata from BeautifulSoup object."""
        meta_data = {
            "brand": "Kross",
            "model": "",
            "categories": [],
            "model_year": None,
            "wheel_size": None,
            "max_tire_width": None,
            "material": None,
            "source_url": "",
            "colors": [],
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
                    v_url_path = v_url.split("?")[0].rstrip("/")
                    v_html_name = v_url_path.split("/")[-1] + ".html"

                    color_variants.append(ColorVariant(html_path=v_html_name, color=v_color, url=v_url))
            if color_variants:
                meta_data["colors"] = color_variants

        return BikeMeta(**meta_data)

    def extract_bike_data(self, html: str, additional_data: Any = None) -> ExtractedBikeData | None:
        """Parses Kross bike HTML."""
        strainer = SoupStrainer(["meta", "div", "table", "ul", "li", "a"])
        try:
            soup = BeautifulSoup(html, "lxml", parse_only=strainer)
        except Exception:
            soup = BeautifulSoup(html, "html.parser", parse_only=strainer)

        bike_meta = self._extract_meta(soup)
        components = {k: [] for k in self.COMPONENT_KEYWORDS}

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
                    bike_meta.max_tire_width = self.clean_value(attr_content)
                elif not bike_meta.wheel_size and "opony" in attr_lower:
                    match = re.search(r"(\d{3})x|(\d{2}[.,]\d)\"|(\d{2})\"", attr_content, re.IGNORECASE)
                    if match:
                        val = match.group(1) or match.group(2) or match.group(3)
                        bike_meta.wheel_size = self.normalize_wheel_size(val)

                # BuildKit components
                self._categorize_component(attr_name, attr_content, components)

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
                    val = matches[-1] if len(matches) > 1 else (matches[0] if "(" not in size_text else None)
                    if val:
                        bike_meta.wheel_size = self.normalize_wheel_size(val)

        # Body (Specs)
        tbody = target_table.find("tbody")
        if tbody:
            for row in tbody.find_all("tr"):
                cells = row.find_all("td")
                if not cells:
                    continue
                attr_name = cells[0].get_text(strip=True)

                # Map header to standardized key
                mapped_key = None
                attr_lower = attr_name.lower()
                for internal_key, labels in self.GEO_MAP.items():
                    if any(label.lower() in attr_lower for label in labels):
                        mapped_key = internal_key
                        break

                if not mapped_key:
                    mapped_key = attr_name

                values = [self.clean_value(cell.get_text(strip=True)) for cell in cells[1:]]
                # Pad values if shorter than sizes
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


def main():
    extractor = KrossBikeExtractor()
    parser = extractor.get_base_parser("kross", artifacts_dir)
    args = parser.parse_args()

    # Priority to archive if it exists
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
