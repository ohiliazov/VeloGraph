from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from backend.scripts.base import BaseBikeDataDownloader
from backend.scripts.constants import artifacts_dir

API_BASE = "https://api.trekbikes.com/occ/v2/pl/products/{pid}/sizing?lang=pl_PL&curr=PLN"


class TrekBikeDownloader(BaseBikeDataDownloader):
    def __init__(self, html_path: Path | None = None):
        brand_name = "trek"
        html_path = html_path or (artifacts_dir / brand_name / "raw_htmls")
        super().__init__(brand_name=brand_name, html_dir=html_path)

    def get_slug_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        return path.split("/")[-3] + "__" + path.split("/")[-1]

    def process_url(
        self,
        page: Any,
        url: str,
        idx: int,
        total: int,
        existing: set[str],
        html_dir: Path | None = None,
        max_retries: int = 3,
    ):
        slug = self.get_slug_from_url(url)
        html_name = f"{slug}.html"
        json_name = f"{slug}_sizing.json"

        if html_name in existing and json_name in existing:
            logger.debug("⏭️ [{:d}/{:d}] Skipping existing HTML+JSON for {}", idx, total, url)
            return

        # First: fetch and save HTML via base helper
        try:
            self._download_single_page(
                page,
                url,
                idx,
                total,
                existing,
                html_dir=html_dir or self.html_dir,
                max_retries=max_retries,
                filename=html_name,
                is_json=False,
            )
        except Exception as e:
            logger.error("❌ Failed HTML fetch for {} after {} attempts: {}", url, max_retries, e)
            return

        # Second: sizing JSON using product id
        pid = slug.split("__")[1] if "__" in slug else ""
        if not pid:
            logger.warning("⚠️ Could not determine product id for {}", url)
            return

        api_url = API_BASE.format(pid=pid)
        try:
            self._download_single_page(
                page,
                api_url,
                idx,
                total,
                existing,
                html_dir=html_dir or self.html_dir,
                max_retries=max_retries,
                filename=json_name,
                is_json=True,
            )
        except Exception:
            logger.error("❌ Failed to fetch sizing JSON for pid {} after {} attempts", pid, max_retries)
