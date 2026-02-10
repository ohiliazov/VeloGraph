import json
import logging
from pathlib import Path
from typing import ClassVar

from loguru import logger
from playwright.sync_api import Error, Page, Route, sync_playwright
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def route_resource_type_handler(r: Route) -> None:
    if r.request.resource_type in ["image", "font", "media"]:
        r.abort()
    else:
        r.continue_()


class BaseBikeCrawler:
    brand_name: ClassVar[str]

    def __init__(self, start_url: str, collected_urls_path: Path):
        self.start_url = start_url
        self.collected_urls_path = collected_urls_path

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Error),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def goto_page(self, page: Page, url: str):
        # Playwright timeouts are in milliseconds
        page.goto(url, wait_until="load", timeout=60000)

    def collect_page_urls(self, page: Page) -> set[str]:
        raise NotImplementedError

    def get_next_page_url(self, page: Page) -> str | None:
        raise NotImplementedError

    def run(self) -> list[str]:
        self.collected_urls_path.parent.mkdir(parents=True, exist_ok=True)

        if self.collected_urls_path.exists():
            with open(self.collected_urls_path, encoding="utf-8") as f:
                urls = set(json.load(f))
        else:
            urls: set[str] = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.route("**/*", handler=route_resource_type_handler)

                logger.info(f"🌐 Opening {self.brand_name.upper()} catalog page: {self.start_url}")
                current_page_url = self.start_url

                while current_page_url:
                    self.goto_page(page, current_page_url)

                    page_urls = self.collect_page_urls(page)
                    urls |= page_urls

                    logger.info(
                        "🔎 Found {} bikes on this page, total unique collected: {}",
                        len(page_urls),
                        len(urls),
                    )

                    current_page_url = self.get_next_page_url(page)
            finally:
                browser.close()

        sorted_urls = sorted(urls)

        with open(self.collected_urls_path, "w", encoding="utf-8") as f:
            json.dump(sorted_urls, f, indent=2)

        logger.success("💾 Saved {} bike URLs to {}", len(sorted_urls), self.collected_urls_path)

        return sorted_urls
