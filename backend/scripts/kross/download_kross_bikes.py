import time

from loguru import logger
from playwright.sync_api import sync_playwright

from backend.scripts.base import BaseBikeCrawler
from backend.scripts.constants import artifacts_dir

START_URL = "https://kross.pl/rowery"


class KrossBikeCrawler(BaseBikeCrawler):
    def __init__(self):
        super().__init__(brand_name="kross", artifacts_dir=artifacts_dir, start_url=START_URL)

    def get_slug_from_url(self, url: str) -> str:
        return url.rstrip("/").split("/")[-1]

    def collect_urls(self) -> list[str]:
        urls: set[str] = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Block images and fonts to speed up
            page.route(
                "**/*",
                lambda r: r.abort() if r.request.resource_type in ["image", "font"] else r.continue_(),
            )

            # Start at main catalog page
            logger.info("🌐 Opening Kross catalog page: {}", self.start_url)
            page.goto(self.start_url, wait_until="networkidle")

            while True:
                # --- Extract all bike URLs on this page ---
                product_buttons = page.query_selector_all("div.products a.action.secondary")
                for btn in product_buttons:
                    if href := btn.get_attribute("href"):
                        urls.add(href)

                logger.info(
                    "🔎 Found {} bikes on this page, total unique collected: {}",
                    len(product_buttons),
                    len(urls),
                )

                # --- Find next page button ---
                next_btn = page.query_selector("a.action.next")
                if next_btn and (next_href := next_btn.get_attribute("href")):
                    logger.debug("➡️ Navigating to next catalog page: {}", next_href)
                    page.goto(next_href, wait_until="networkidle")
                    time.sleep(1)  # wait for JS
                    continue

                logger.info("🛑 No more catalog pages detected. Stopping pagination.")
                break

            browser.close()

        return sorted(urls)


if __name__ == "__main__":
    crawler = KrossBikeCrawler()
    crawler.run()
