import json
from pathlib import Path

from loguru import logger
from playwright.sync_api import Error, Page, Route, sync_playwright
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from scripts.constants import artifacts_dir


def route_resource_type_handler(r: Route) -> None:
    if r.request.resource_type in ["image", "font", "media"]:
        r.abort()
    else:
        r.continue_()


class KrossBikeCrawler:
    def __init__(self, start_url: str, output_path: Path):
        self.start_url = start_url
        self.output_path = output_path

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Error),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )
    def goto_page(self, page: Page, url: str):
        # Playwright timeouts are in milliseconds
        page.goto(url, wait_until="load", timeout=60000)

    def collect_page_urls(self, page) -> set[str]:
        urls: set[str] = set()
        product_buttons = page.query_selector_all("div.products a.action.secondary")
        for btn in product_buttons:
            if href := btn.get_attribute("href"):
                urls.add(href)
        return urls

    def get_next_page_url(self, page) -> str | None:
        next_btn = page.query_selector("a.action.next")
        if next_btn and (next_href := next_btn.get_attribute("href")):
            return next_href
        return None

    def run(self, overwrite: bool = False) -> list[str]:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.output_path.exists() and not overwrite:
            return json.loads(self.output_path.read_text(encoding="utf-8"))

        bike_urls = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.route("**/*", handler=route_resource_type_handler)

                logger.info("🌐 Opening KROSS catalog page: {}", self.start_url)
                current_page_url = self.start_url

                while current_page_url:
                    logger.info("📄 Fetching page: {}", current_page_url)
                    self.goto_page(page, current_page_url)

                    page_urls = self.collect_page_urls(page)
                    bike_urls |= page_urls

                    logger.info(
                        "🔎 Found {} bikes on this page, total unique collected: {}",
                        len(page_urls),
                        len(bike_urls),
                    )

                    current_page_url = self.get_next_page_url(page)
                    if current_page_url:
                        logger.info("➡️ Navigating to next catalog page: {}", current_page_url)
                    else:
                        logger.info("🏁 No more pages to crawl.")
            finally:
                browser.close()

        bike_urls = sorted(bike_urls)

        self.output_path.write_text(json.dumps(bike_urls, indent=2), encoding="utf-8")

        logger.success("💾 Saved {} bike URLs to {}", len(bike_urls), self.output_path)

        return bike_urls


class KrossDownloader:
    def __init__(self, input_bike_url: str, output_dir: Path, overwrite: bool = False):
        self.input_url = input_bike_url
        self.output_html_path = output_dir / f"{self.get_slug_from_url()}.html"
        self.overwrite = overwrite
        self.output_html_path.parent.mkdir(parents=True, exist_ok=True)

    def _save_file(self, content: str, file_path: Path):
        file_path.write_text(content, encoding="utf-8")
        logger.debug("💾 File saved: {}", file_path)

    def get_slug_from_url(self) -> str:
        return self.input_url.rstrip("/").split("/")[-1]

    def _download_single_page(self):

        if self.output_html_path.exists() and not self.overwrite:
            logger.info("⏭️ Skipping existing file: {}", self.output_html_path.name)
            return

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Block heavy resources
            page.route("**/*", route_resource_type_handler)
            logger.debug("🌐 Navigating to {}", self.input_url)
            page.goto(self.input_url, wait_until="load", timeout=30000)
            self._save_file(page.content(), self.output_html_path)
            logger.success("✅ Downloaded and saved: {}", self.output_html_path.name)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )
    def run(self):
        logger.info("🚀 Downloading {}", self.input_url)
        self._download_single_page()


if __name__ == "__main__":
    crawler = KrossBikeCrawler("https://kross.pl/rowery", artifacts_dir / "kross" / "bike_urls.json")
    all_bike_urls = crawler.run()

    for url in all_bike_urls:
        downloader = KrossDownloader(url, artifacts_dir / "kross" / "raw_htmls", overwrite=False)
        downloader.run()
