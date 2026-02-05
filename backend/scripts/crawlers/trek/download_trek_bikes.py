import json
import time
import zipfile
from urllib.parse import urljoin, urlparse

from loguru import logger
from playwright.sync_api import sync_playwright

from backend.scripts.constants import artifacts_dir

START_URL = "https://www.trekbikes.com/pl/pl_PL/rowery/c/B100/?pageSize=72&q=%3Arelevance&sort=relevance#"
BASE_URL = "https://www.trekbikes.com"

# Artifacts paths
trek_artifacts = artifacts_dir / "trek"
trek_artifacts.mkdir(parents=True, exist_ok=True)

trek_bike_urls_path = trek_artifacts / "bike_urls.json"

trek_bike_archive_path = trek_artifacts / "raw_htmls.zip"


def normalize_url(href: str) -> str:
    href = href.strip()
    if href.startswith(("http://", "https://")):
        return href
    return urljoin(BASE_URL, href)


def slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return path.split("/")[-1]


def collect_trek_bike_urls() -> list[str]:
    urls: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Block images and fonts to speed up crawling
        page.route(
            "**/*",
            lambda r: r.abort() if r.request.resource_type in ["image", "font", "media"] else r.continue_(),
        )

        logger.info("🌐 Opening Trek catalog page: {}", START_URL)
        page.goto(START_URL, wait_until="load")

        while True:
            # Extract all product links using qaid="productCardProductName" > a
            anchors = page.query_selector_all('[qaid="productCardProductName"] a')
            for a in anchors:
                href = a.get_attribute("href")
                if not href:
                    continue
                url = normalize_url(href)
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
                    next_url = normalize_url(next_href)
                    logger.debug("➡️ Navigating to next catalog page: {}", next_url)
                    page.goto(next_url, wait_until="load")
                    time.sleep(1)
                    continue

            logger.info("🛑 No more catalog pages detected. Stopping pagination.")
            break

        browser.close()

    return sorted(urls)


def save_urls(urls: list[str]):
    with open(trek_bike_urls_path, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2)
    logger.success("💾 Saved {} bike URLs to {}", len(urls), trek_bike_urls_path)


def load_urls() -> list[str]:
    with open(trek_bike_urls_path, encoding="utf-8") as f:
        return list(dict.fromkeys(json.load(f)))


def download_bike_pages(urls: list[str]):
    # Determine which HTMLs already exist in the archive
    existing: set[str] = set()
    if trek_bike_archive_path.exists():
        with zipfile.ZipFile(trek_bike_archive_path, "r") as zread:
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
        with zipfile.ZipFile(trek_bike_archive_path, "a", zipfile.ZIP_DEFLATED) as zwrite:
            for idx, url in enumerate(urls, start=1):
                slug = slug_from_url(url)
                name = f"{slug}.html"

                if name in existing:
                    logger.debug("⏭️ [{:d}/{:d}] Skipping existing HTML for {}", idx, total, url)
                    continue

                logger.info("⬇️ [{:d}/{:d}] Fetching: {}", idx, total, url)
                page.goto(url, wait_until="load")
                time.sleep(1)  # allow extra JS rendering time

                html = page.content()
                zwrite.writestr(name, html)
                logger.debug("💾 Saved HTML to archive {} (entry: {}, slug: {})", trek_bike_archive_path, name, slug)

        browser.close()


if __name__ == "__main__":
    # Step 1: collect URLs (or load if already collected)
    if not trek_bike_urls_path.exists():
        urls = collect_trek_bike_urls()
        save_urls(urls)
    else:
        urls = load_urls()
        logger.info("📥 Loaded {} bike URLs from {}", len(urls), trek_bike_urls_path)

    # Step 2: download individual bike pages
    download_bike_pages(urls)
