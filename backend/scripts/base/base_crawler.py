import argparse
import json
from pathlib import Path

from loguru import logger


class BaseBikeCrawler:
    def __init__(self, brand_name: str, start_url: str, urls_path: Path):
        self.brand_name = brand_name
        self.start_url = start_url
        self.urls_path = urls_path
        self.urls_path.parent.mkdir(parents=True, exist_ok=True)

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

    def run(self, retries: int = 3, force: bool = False) -> list[str]:
        if not self.urls_path.exists() or force:
            logger.info("🚀 Starting URL collection for {}", self.brand_name)
            urls = self.collect_urls(max_retries=retries)
            self.save_urls(urls)
        else:
            urls = self.load_urls()
            logger.info("📥 Loaded {} bike URLs from {}", len(urls), self.urls_path)
        return urls

    @classmethod
    def get_base_parser(cls, brand: str) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=f"Crawl {brand.capitalize()} bike data.")
        parser.add_argument("--retries", type=int, default=3, help="Number of retries for each page fetch.")
        parser.add_argument("--concurrency", "-j", type=int, default=1, help="Number of concurrent download workers.")
        parser.add_argument(
            "--force", action="store_true", help="Force re-collection of URLs and re-download of pages."
        )
        return parser
