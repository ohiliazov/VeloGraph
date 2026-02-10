from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from loguru import logger
from playwright.sync_api import sync_playwright
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.scripts.base import BaseBikeCrawler
from backend.scripts.constants import artifacts_dir

START_URL = "https://www.trekbikes.com/pl/pl_PL/rowery/c/B100/?pageSize=72&q=%3Arelevance&sort=relevance#"
BASE_URL = "https://www.trekbikes.com"
API_BASE = "https://api.trekbikes.com/occ/v2/pl/products/{pid}/sizing?lang=pl_PL&curr=PLN"


class TrekBikeCrawler(BaseBikeCrawler):
    def __init__(self):
        super().__init__(brand_name="trek", artifacts_dir=artifacts_dir, start_url=START_URL)

    def normalize_url(self, href: str) -> str:
        href = href.strip()
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(BASE_URL, href)

    def get_slug_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        return path.split("/")[-3] + "__" + path.split("/")[-1]

    def collect_urls(self, max_retries: int = 3) -> list[str]:
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

            @retry(
                stop=stop_after_attempt(max_retries),
                wait=wait_exponential(multiplier=1, min=2, max=10),
                retry=retry_if_exception_type(Exception),
                before_sleep=before_sleep_log(logger, "WARNING"),
                reraise=True,
            )
            def _open_catalog():
                page.goto(self.start_url, wait_until="load", timeout=60000)

            try:
                _open_catalog()
            except Exception:
                logger.error("❌ Failed to open Trek catalog after {} attempts", max_retries)
                browser.close()
                return []

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

                        @retry(
                            stop=stop_after_attempt(max_retries),
                            wait=wait_exponential(multiplier=1, min=2, max=10),
                            retry=retry_if_exception_type(Exception),
                            before_sleep=before_sleep_log(logger, "WARNING"),
                            reraise=True,
                        )
                        def _goto_next(url=next_url):
                            page.goto(url, wait_until="load", timeout=60000)

                        try:
                            _goto_next()
                            continue
                        except Exception:
                            logger.error(
                                "❌ Failed to navigate to next catalog page after {} attempts: {}",
                                max_retries,
                                next_url,
                            )
                            break  # Stop pagination on failure

                logger.info("🛑 No more catalog pages detected. Stopping pagination.")
                break

            browser.close()

        return sorted(urls)

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


if __name__ == "__main__":
    parser = TrekBikeCrawler.get_base_parser("trek")
    args = parser.parse_args()
    crawler = TrekBikeCrawler()
    crawler.run(args)
