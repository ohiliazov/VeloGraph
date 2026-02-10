from pathlib import Path
from urllib.parse import urljoin, urlparse

from loguru import logger
from playwright.sync_api import sync_playwright
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.scripts.base import BaseBikeCrawler
from backend.scripts.constants import artifacts_dir

START_URL = "https://www.trekbikes.com/pl/pl_PL/rowery/c/B100/?pageSize=72&q=%3Arelevance&sort=relevance#"
BASE_URL = "https://www.trekbikes.com"


class TrekBikeCrawler(BaseBikeCrawler):
    def __init__(self, url: str = START_URL, urls_path: Path | None = None):
        brand_name = "trek"
        urls_path = urls_path or (artifacts_dir / brand_name / "bike_urls.json")
        super().__init__(brand_name=brand_name, start_url=url, urls_path=urls_path)

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
