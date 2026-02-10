from pathlib import Path
from typing import ClassVar

from loguru import logger
from playwright.sync_api import Route, sync_playwright
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def route_resource_type_handler(r: Route) -> None:
    if r.request.resource_type in ["image", "font", "media"]:
        r.abort()
    else:
        r.continue_()


class BaseDownloader:
    brand_name: ClassVar[str]

    def __init__(self, input_url: str, output_dir: Path, overwrite: bool = False):
        self.input_url = input_url
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _save_file(self, content: str, file_path: Path):
        file_path.write_text(content, encoding="utf-8")

    def get_slug_from_url(self) -> str:
        raise NotImplementedError("get_slug_from_url() must be implemented by subclasses")

    def _download_single_page(self):
        html_path = self.output_dir / f"{self.get_slug_from_url()}.html"

        if html_path.exists() and not self.overwrite:
            logger.info("⏭️ Skipping existing file {}", html_path)
            return

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Block heavy resources
            page.route("**/*", route_resource_type_handler)
            page.goto(self.input_url, wait_until="load", timeout=30000)
            self._save_file(page.content(), html_path)

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
