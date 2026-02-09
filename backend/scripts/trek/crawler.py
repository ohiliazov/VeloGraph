import json
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from loguru import logger
from playwright.sync_api import sync_playwright

from backend.scripts.base import BaseBikeCrawler
from backend.scripts.constants import artifacts_dir

START_URL = "https://www.trekbikes.com/pl/pl_PL/rowery/c/B100/?pageSize=72&q=%3Arelevance&sort=relevance#"
BASE_URL = "https://www.trekbikes.com"
API_BASE = "https://api.trekbikes.com/occ/v2/pl/products/{pid}/sizing?lang=pl_PL&curr=PLN"


class TrekBikeCrawler(BaseBikeCrawler):
    def __init__(self, archive: bool = False):
        super().__init__(brand_name="trek", artifacts_dir=artifacts_dir, start_url=START_URL, archive=archive)

    def normalize_url(self, href: str) -> str:
        href = href.strip()
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(BASE_URL, href)

    def get_slug_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        return path.split("/")[-3] + "__" + path.split("/")[-1]

    def collect_urls(self) -> list[str]:
        urls: set[str] = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Block images and fonts to speed up crawling
            page.route(
                "**/*",
                lambda r: r.abort() if r.request.resource_type in ["image", "font", "media"] else r.continue_(),
            )

            logger.info("🌐 Opening Trek catalog page: {}", self.start_url)
            page.goto(self.start_url, wait_until="load")

            while True:
                # Extract all product links using qaid="productCardProductName" > a
                anchors = page.query_selector_all('[qaid="productCardProductName"] a')
                for a in anchors:
                    href = a.get_attribute("href")
                    if not href:
                        continue
                    url = self.normalize_url(href)
                    urls.add(url)

                logger.info(
                    "🔎 Found {} bikes on this page, total unique collected: {}",
                    len(anchors),
                    len(urls),
                )

                # Next page via a#search-page-next
                next_a = page.query_selector("a#search-page-next")
                if next_a:
                    next_href = next_a.get_attribute("href")
                    if next_href:
                        next_url = self.normalize_url(next_href)
                        logger.debug("➡️ Navigating to next catalog page: {}", next_url)
                        page.goto(next_url, wait_until="load")
                        time.sleep(1)
                        continue

                logger.info("🛑 No more catalog pages detected. Stopping pagination.")
                break

            browser.close()

        return sorted(urls)

    def download_bike_pages(self, urls: list[str]):
        # Override to also fetch sizing JSON per product
        existing: set[str] = set()
        if self.archive:
            if self.archive_path.exists():
                import zipfile as _zf

                with _zf.ZipFile(self.archive_path, "r") as zread:
                    existing = set(zread.namelist())
        else:
            self.html_dir.mkdir(parents=True, exist_ok=True)
            existing = {p.name for p in self.html_dir.glob("*")}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Block heavy resources
            page.route(
                "**/*",
                lambda r: r.abort() if r.request.resource_type in ["image", "font", "media"] else r.continue_(),
            )

            total = len(urls)

            if self.archive:
                with zipfile.ZipFile(self.archive_path, "a", zipfile.ZIP_DEFLATED) as zwrite:
                    for idx, url in enumerate(urls, start=1):
                        self._download_trek_bike(page, url, idx, total, existing, zwrite=zwrite)
            else:
                for idx, url in enumerate(urls, start=1):
                    self._download_trek_bike(page, url, idx, total, existing, html_dir=self.html_dir)

            browser.close()

    def _download_trek_bike(
        self,
        page: Any,
        url: str,
        idx: int,
        total: int,
        existing: set[str],
        zwrite: zipfile.ZipFile | None = None,
        html_dir: Path | None = None,
    ):
        slug = self.get_slug_from_url(url)
        html_name = f"{slug}.html"
        json_name = f"{slug}_sizing.json"

        if html_name in existing and json_name in existing:
            logger.debug("⏭️ [{:d}/{:d}] Skipping existing HTML+JSON for {}", idx, total, url)
            return

        logger.info("⬇️ [{:d}/{:d}] Fetching: {}", idx, total, url)
        try:
            page.goto(url, wait_until="load")
            # Give the page a bit more time for scripts that populate dataLayer
            time.sleep(1.5)
            html = page.content()

            if zwrite:
                zwrite.writestr(html_name, html)
                logger.debug("💾 Saved HTML to {} (entry: {})", self.archive_path, html_name)
            elif html_dir:
                (html_dir / html_name).write_text(html, encoding="utf-8")
                logger.debug("💾 Saved HTML to {}/{}", html_dir, html_name)

            # Try to extract product id and fetch sizing JSON
            pid = slug.split("__")[1]
            if not pid:
                logger.warning("⚠️ Could not determine product id for {}", url)
            else:
                api_url = API_BASE.format(pid=pid)
                try:
                    resp = page.request.get(api_url, timeout=15000)
                    if resp.ok:
                        data = resp.json()
                        json_str = json.dumps(data, ensure_ascii=False)
                        if zwrite:
                            zwrite.writestr(json_name, json_str)
                            logger.debug("💾 Saved sizing JSON (pid {}): {}", pid, json_name)
                        elif html_dir:
                            (html_dir / json_name).write_text(json_str, encoding="utf-8")
                            logger.debug("💾 Saved sizing JSON (pid {}): {}/{}", pid, html_dir, json_name)
                    else:
                        logger.warning("⚠️ Sizing API returned {} for {}", resp.status, api_url)
                except Exception as api_err:
                    logger.warning("⚠️ Failed to fetch sizing JSON for pid {}: {}", pid, api_err)
        except Exception as e:
            logger.error("❌ Failed to download {}: {}", url, e)


if __name__ == "__main__":
    parser = TrekBikeCrawler.get_base_parser("trek")
    args = parser.parse_args()
    crawler = TrekBikeCrawler(archive=args.archive)
    crawler.run(args)
