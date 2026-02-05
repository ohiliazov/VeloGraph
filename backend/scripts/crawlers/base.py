import json
import time
import zipfile
from pathlib import Path

from loguru import logger
from playwright.sync_api import sync_playwright


class BaseBikeCrawler:
    def __init__(self, brand_name: str, artifacts_dir: Path, start_url: str):
        self.brand_name = brand_name
        self.artifacts_path = artifacts_dir / brand_name.lower()
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        self.urls_path = self.artifacts_path / "bike_urls.json"
        self.archive_path = self.artifacts_path / "raw_htmls.zip"
        self.start_url = start_url

    def collect_urls(self) -> list[str]:
        """
        To be implemented by subclasses. Should return a list of unique bike URLs.
        """
        raise NotImplementedError

    def save_urls(self, urls: list[str]):
        with open(self.urls_path, "w", encoding="utf-8") as f:
            json.dump(urls, f, indent=2)
        logger.success("💾 Saved {} bike URLs to {}", len(urls), self.urls_path)

    def load_urls(self) -> list[str]:
        with open(self.urls_path, encoding="utf-8") as f:
            return list(dict.fromkeys(json.load(f)))

    def get_slug_from_url(self, url: str) -> str:
        """
        Default slug extraction from URL. Can be overridden.
        """
        raise NotImplementedError("get_slug_from_url() must be implemented by subclasses")

    def download_bike_pages(self, urls: list[str]):
        # Determine which HTMLs already exist in the archive
        existing: set[str] = set()
        if self.archive_path.exists():
            with zipfile.ZipFile(self.archive_path, "r") as zread:
                existing = set(zread.namelist())

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Block heavy resources
            page.route(
                "**/*",
                lambda r: r.abort() if r.request.resource_type in ["image", "font", "media"] else r.continue_(),
            )

            total = len(urls)
            # Open the archive in append mode once and stream pages into it
            with zipfile.ZipFile(self.archive_path, "a", zipfile.ZIP_DEFLATED) as zwrite:
                for idx, url in enumerate(urls, start=1):
                    slug = self.get_slug_from_url(url)
                    name = f"{slug}.html"

                    if name in existing:
                        logger.debug("⏭️ [{:d}/{:d}] Skipping existing HTML for {}", idx, total, url)
                        continue

                    logger.info("⬇️ [{:d}/{:d}] Fetching: {}", idx, total, url)
                    try:
                        page.goto(url, wait_until="load")
                        time.sleep(1)  # allow extra JS rendering time
                        html = page.content()
                        zwrite.writestr(name, html)
                        logger.debug("💾 Saved HTML to archive {} (entry: {})", self.archive_path, name)
                    except Exception as e:
                        logger.error("❌ Failed to download {}: {}", url, e)

            browser.close()

    def run(self):
        if not self.urls_path.exists():
            logger.info("🚀 Starting URL collection for {}", self.brand_name)
            urls = self.collect_urls()
            self.save_urls(urls)
        else:
            urls = self.load_urls()
            logger.info("📥 Loaded {} bike URLs from {}", len(urls), self.urls_path)

        self.download_bike_pages(urls)
