import time
from urllib.parse import urljoin, urlparse

from loguru import logger
from playwright.sync_api import sync_playwright

from backend.scripts.constants import artifacts_dir
from backend.scripts.crawlers.base import BaseBikeCrawler

START_URL = "https://www.trekbikes.com/pl/pl_PL/rowery/c/B100/?pageSize=72&q=%3Arelevance&sort=relevance#"
BASE_URL = "https://www.trekbikes.com"


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
        return path.split("/")[-1]

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


if __name__ == "__main__":
    crawler = TrekBikeCrawler()
    crawler.run()
