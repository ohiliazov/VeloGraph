import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger
from playwright.sync_api import sync_playwright
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class BaseBikeCrawler:
    def __init__(self, brand_name: str, artifacts_dir: Path, start_url: str):
        self.brand_name = brand_name
        self.artifacts_path = artifacts_dir / brand_name.lower()
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        self.urls_path = self.artifacts_path / "bike_urls.json"
        self.html_dir = self.artifacts_path / "raw_htmls"
        self.start_url = start_url

    def collect_urls(self, max_retries: int = 3) -> list[str]:
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

    def download_bike_pages(self, urls: list[str], max_retries: int = 3, concurrency: int = 1):
        # Determine which HTMLs already exist
        self.html_dir.mkdir(parents=True, exist_ok=True)
        existing = {p.name for p in self.html_dir.glob("*")}

        total = len(urls)

        def _worker(batch: list[tuple[int, str]]):
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                # Block heavy resources
                page.route(
                    "**/*",
                    lambda r: r.abort() if r.request.resource_type in ["image", "font", "media"] else r.continue_(),
                )

                for idx, url in batch:
                    self.process_url(
                        page=page,
                        url=url,
                        idx=idx,
                        total=total,
                        existing=existing,
                        html_dir=self.html_dir,
                        max_retries=max_retries,
                    )
                browser.close()

        # Split URLs into batches for workers
        url_with_idx = list(enumerate(urls, start=1))

        if concurrency <= 1:
            _worker(url_with_idx)
        else:
            batches = [url_with_idx[i::concurrency] for i in range(concurrency)]
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                executor.map(_worker, batches)

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
        """
        Hook for subclasses to process a single product URL.
        Default implementation downloads one HTML page via `_download_single_page`.
        Trek overrides this to also fetch the sizing JSON per product.
        """
        self._download_single_page(
            page=page,
            url=url,
            idx=idx,
            total=total,
            existing=existing,
            html_dir=html_dir or self.html_dir,
            max_retries=max_retries,
            filename=None,
            is_json=False,
        )

    def _download_single_page(
        self,
        page: Any,
        url: str,
        idx: int,
        total: int,
        existing: set[str],
        html_dir: Path | None = None,
        max_retries: int = 3,
        filename: str | None = None,
        is_json: bool = False,
    ):
        slug = self.get_slug_from_url(url)
        name = filename or (f"{slug}.json" if is_json else f"{slug}.html")

        if name in existing:
            logger.debug("⏭️ [{:d}/{:d}] Skipping existing {} for {}", idx, total, "JSON" if is_json else "HTML", url)
            return

        logger.info("⬇️ [{:d}/{:d}] Fetching {}: {}", idx, total, "JSON" if is_json else "HTML", url)

        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(Exception),
            before_sleep=before_sleep_log(logger, "WARNING"),
            reraise=True,
        )
        def _fetch(target_url=url, target_is_json=is_json):
            if target_is_json:
                resp = page.request.get(target_url, timeout=15000)
                if not resp.ok:
                    raise RuntimeError(f"Bad status {resp.status} for {target_url}")
                return json.dumps(resp.json(), ensure_ascii=False)
            else:
                page.goto(target_url, wait_until="load", timeout=30000)
                return page.content()

        try:
            content = _fetch()
            if html_dir:
                (html_dir / name).write_text(content, encoding="utf-8")
                logger.debug("💾 Saved {} to {}/{}", "JSON" if is_json else "HTML", html_dir, name)
        except Exception as e:
            logger.error("❌ Failed to download {} after {} attempts: {}", url, max_retries, e)

    def run(self, args: argparse.Namespace | None = None):
        retries = getattr(args, "retries", 3) if args else 3
        concurrency = getattr(args, "concurrency", 1) if args else 1
        if not self.urls_path.exists():
            logger.info("🚀 Starting URL collection for {}", self.brand_name)
            urls = self.collect_urls(max_retries=retries)
            self.save_urls(urls)
        else:
            urls = self.load_urls()
            logger.info("📥 Loaded {} bike URLs from {}", len(urls), self.urls_path)

        self.download_bike_pages(urls, max_retries=retries, concurrency=concurrency)

    @classmethod
    def get_base_parser(cls, brand: str) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=f"Crawl {brand.capitalize()} bike data.")
        parser.add_argument("--retries", type=int, default=3, help="Number of retries for each page fetch.")
        parser.add_argument("--concurrency", "-j", type=int, default=1, help="Number of concurrent download workers.")
        return parser
